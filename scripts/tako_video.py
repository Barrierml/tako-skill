#!/usr/bin/env python3
"""Tako video helper. Uses only the Python standard library; no automatic retries."""
import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

SUBMIT_PATH = '/v1/videos/generations'
STATUSES_PATH = '/v1/videos/{task_id}'
CONTENT_PATH = '/v1/videos/{task_id}/content'
SUCCESS_STATES = {'success', 'succeeded', 'done', 'completed', 'finished', 'ok'}
FAILURE_STATES = {'failure', 'failed', 'error', 'cancelled', 'canceled', 'rejected', 'expired'}


class NoAPIRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('API redirect refused; check TAKO_BASE_URL')


def task_id_of(payload):
    if isinstance(payload, list):
        for entry in payload:
            found = task_id_of(entry)
            if found:
                return found
        return None
    if not isinstance(payload, dict):
        return None
    for key in ('id', 'task_id'):
        if payload.get(key):
            return str(payload[key])
    for key in ('task', 'data'):
        found = task_id_of(payload.get(key))
        if found:
            return found
    return None


def status_of(payload):
    if isinstance(payload, list):
        for entry in payload:
            found = status_of(entry)
            if found:
                return found
        return None
    if not isinstance(payload, dict):
        return None
    for key in ('status', 'state', 'task_status'):
        if payload.get(key):
            return str(payload[key])
    for key in ('task', 'data'):
        found = status_of(payload.get(key))
        if found:
            return found
    return None


def fetch(request, timeout):
    opener = urllib.request.build_opener(NoAPIRedirect())
    try:
        with opener.open(request, timeout=timeout) as resp:
            return resp.read(), resp.headers.get('Content-Type', '')
    except urllib.error.HTTPError as error:
        raise ValueError(f'Tako HTTP {error.code}: {http_message(error)}')


def http_message(error):
    try:
        message = json.loads(error.read()).get('error', {})
        if isinstance(message, dict):
            return message.get('message', 'request rejected')
        return str(message)
    except (ValueError, AttributeError):
        return 'request rejected'


def post_json(base, path, key, body, timeout):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    payload, _ = fetch(request, timeout)
    return json.loads(payload)


def get_json(base, path, key, timeout):
    request = urllib.request.Request(base + path, headers={'Authorization': 'Bearer ' + key})
    payload, _ = fetch(request, timeout)
    return json.loads(payload)


def find_video_item(node):
    if isinstance(node, list):
        for entry in node:
            found = find_video_item(entry)
            if found:
                return found
        return None
    if not isinstance(node, dict):
        return None
    if node.get('b64_json') or node.get('url') or node.get('video_url'):
        return node
    for field in ('data', 'video', 'task', 'output'):
        found = find_video_item(node.get(field))
        if found:
            return found
    return None


def get_content(base, task_id, key, timeout):
    request = urllib.request.Request(base + CONTENT_PATH.format(task_id=task_id),
                                   headers={'Authorization': 'Bearer ' + key})
    payload, content_type = fetch(request, timeout)
    if content_type.split(';')[0].strip() != 'application/json':
        return payload
    item = find_video_item(json.loads(payload))
    if not item:
        raise ValueError('content response contains no video bytes or URL')
    if item.get('b64_json'):
        return base64.b64decode(item['b64_json'], validate=True)
    # Deliberately unauthenticated: never send the Tako key to a video CDN.
    with urllib.request.urlopen(item.get('url') or item.get('video_url'), timeout=timeout) as resp:
        return resp.read()


def save_video(data, target):
    if not data:
        raise ValueError('downloaded video is empty')
    if len(data) < 12 or data[4:8] != b'ftyp':
        raise ValueError('downloaded output is not a recognized MP4/MOV video')
    path = Path(target).with_suffix('.mp4')
    if path.exists():
        raise ValueError(f'output already exists: {path}; choose a new --save-video path')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as file:
        file.write(data)
    return str(path)


def reference_image_value(source):
    if source.startswith('http://') or source.startswith('https://'):
        return source
    image = Path(source).read_bytes()
    mime = mimetypes.guess_type(source)[0] or 'application/octet-stream'
    if mime not in ('image/png', 'image/jpeg', 'image/webp'):
        raise ValueError('reference must be PNG, JPEG or WebP')
    return f'data:{mime};base64,' + base64.b64encode(image).decode()


def generate(args, base, key):
    body = {'model': args.model, 'prompt': args.prompt,
            'duration': args.duration, 'resolution': args.resolution}
    if args.aspect_ratio:
        body['aspect_ratio'] = args.aspect_ratio
    if args.image:
        body['image'] = reference_image_value(args.image)
    submitted = post_json(base, SUBMIT_PATH, key, body, args.timeout)
    if submitted.get('error'):
        raise ValueError('API returned an error; inspect the response and do not retry blindly')
    task_id = task_id_of(submitted)
    if not task_id:
        raise ValueError('submit response contains no task id; inspect the saved response')
    # Persist the submitted response first so the task can be recovered without regenerating.
    if args.out:
        Path(args.out).write_text(json.dumps(submitted, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Submitted video task: ' + task_id, file=sys.stderr)
    deadline = time.monotonic() + args.max_wait
    last_status = None
    while True:
        status_payload = get_json(base, STATUSES_PATH.format(task_id=task_id), key, args.timeout)
        status = (status_of(status_payload) or '').lower()
        if status and status != last_status:
            print(f'Task {task_id} status: {status}', file=sys.stderr)
            last_status = status
        if status in SUCCESS_STATES:
            break
        if status in FAILURE_STATES:
            raise ValueError(f'video task {task_id} failed with status {status!r}; '
                             'inspect the saved task JSON before paying for another run')
        if time.monotonic() + args.poll_interval > deadline:
            raise ValueError(f'video task {task_id} still {status or "pending"} after --max-wait '
                             f'{args.max_wait:g}s; finish it later with `tako-video.sh status {task_id}`')
        time.sleep(args.poll_interval)
    return task_id


def status_command(args, base, key):
    task_id = args.task_id
    if task_id is None:
        task_id = task_id_of(json.loads(Path(args.task_json).read_text(encoding='utf-8')))
        if not task_id:
            raise ValueError(f'no task id in {args.task_json}')
    payload = get_json(base, STATUSES_PATH.format(task_id=task_id), key, args.timeout)
    status = status_of(payload)
    if args.out:
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False) + '\n', encoding='utf-8')
    elif not args.save_video:
        print(json.dumps(payload, ensure_ascii=False))
    if args.save_video and (status or '').lower() not in SUCCESS_STATES:
        raise ValueError(f'task {task_id} status is {status or "unknown"}, not finished; '
                         'no video downloaded')
    return task_id if args.save_video else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='command', required=True)
    gen = modes.add_parser('generate', help='submit a video task, poll it and save the MP4')
    gen.add_argument('prompt')
    gen.add_argument('--model', default='grok-imagine-video')
    gen.add_argument('--duration', type=int, default=5)
    gen.add_argument('--resolution', default='480p')
    gen.add_argument('--aspect-ratio')
    gen.add_argument('--image', help='optional reference image path or URL for image-to-video')
    gen.add_argument('--poll-interval', type=float, default=5)
    gen.add_argument('--max-wait', type=float, default=1200)
    gen.add_argument('--out', help='save submitted task JSON')
    gen.add_argument('--save-video', help='save the finished MP4; never overwrites')
    gen.add_argument('--timeout', type=float, default=240)
    stat = modes.add_parser('status', help='read a task status or download a finished video')
    stat.add_argument('task_id', nargs='?', help='task id; or use --task-json')
    stat.add_argument('--task-json', help='JSON file saved by generate --out')
    stat.add_argument('--out', help='save status JSON')
    stat.add_argument('--save-video', help='download the MP4 when the task succeeded')
    stat.add_argument('--timeout', type=float, default=240)
    args = parser.parse_args()
    key = os.environ.get('TAKO_API_KEY', '')
    if not key:
        parser.error('TAKO_API_KEY is required; create a user token in the Tako console')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    if args.command == 'generate':
        if not 1 <= args.duration <= 15:
            parser.error('--duration must be between 1 and 15 seconds')
        if args.poll_interval <= 0 or args.max_wait <= 0:
            parser.error('--poll-interval and --max-wait must be positive')
        if args.save_video and Path(args.save_video).with_suffix('.mp4').exists():
            parser.error('output already exists; choose a new --save-video path')
    else:
        if not args.task_id and not args.task_json:
            parser.error('status needs a task_id argument or --task-json')
        if args.save_video and Path(args.save_video).with_suffix('.mp4').exists():
            parser.error('output already exists; choose a new --save-video path')
    try:
        base = os.environ.get('TAKO_BASE_URL', 'https://tako.shiroha.tech').rstrip('/')
        if args.command == 'generate':
            task_id = generate(args, base, key)
        else:
            task_id = status_command(args, base, key)
        if task_id and args.save_video:
            data = get_content(base, task_id, key, args.timeout)
            print('Saved video: ' + save_video(data, args.save_video), file=sys.stderr)
    except urllib.error.HTTPError as error:
        print(f'Tako HTTP {error.code}: {http_message(error)}'.replace(key, '[redacted]'), file=sys.stderr)
        return 1
    except (ValueError, OSError, urllib.error.URLError, KeyError) as error:
        print(str(error).replace(key, '[redacted]'), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
