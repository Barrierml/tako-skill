#!/usr/bin/env python3
"""Tako image helper. Uses only the Python standard library; no automatic retries."""
import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
import uuid


class NoAPIRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('API redirect refused; check TAKO_BASE_URL')


def build_request(args):
    image = None
    if args.command == 'edit':
        image = Path(args.image).read_bytes()
        mime = mimetypes.guess_type(args.image)[0] or 'application/octet-stream'
        if mime not in ('image/png', 'image/jpeg', 'image/webp'):
            raise ValueError('reference must be PNG, JPEG or WebP')
    if args.model.startswith('gemini-') and '-image' in args.model:
        if args.n != 1:
            raise ValueError('Gemini image requests require --n 1')
        parts = [{'text': args.prompt}]
        if image is not None:
            parts.append({'inlineData': {'mimeType': mime, 'data': base64.b64encode(image).decode()}})
        config = {'responseModalities': ['TEXT', 'IMAGE']}
        if args.size:
            ratios = {'1024x1024':'1:1', '1536x1024':'3:2', '1024x1536':'2:3', '1792x1024':'16:9', '1024x1792':'9:16'}
            ratio = ratios.get(args.size, args.size if ':' in args.size else None)
            if ratio is None:
                raise ValueError('use a supported aspect ratio for Gemini --size, e.g. 16:9')
            config['imageConfig'] = {'aspectRatio': ratio}
        body = {'contents': [{'role':'user', 'parts':parts}], 'generationConfig':config}
        return f'/v1beta/models/{args.model}:generateContent', json.dumps(body).encode(), 'application/json'
    fields = {'model':args.model, 'prompt':args.prompt, 'n':args.n, 'response_format':'b64_json'}
    if args.size:
        fields['size'] = args.size
    if image is None:
        return '/v1/images/generations', json.dumps(fields).encode(), 'application/json'
    if args.model.startswith('grok-imagine-image'):
        # The current upstream drops response_format when translating multipart edits.
        fields['images'] = [{'image_url': f'data:{mime};base64,' + base64.b64encode(image).decode()}]
        return '/v1/images/edits', json.dumps(fields).encode(), 'application/json'
    boundary = 'tako-image-' + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="reference{Path(args.image).suffix}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
    chunks += [image, f'\r\n--{boundary}--\r\n'.encode()]
    return '/v1/images/edits', b''.join(chunks), 'multipart/form-data; boundary=' + boundary


def image_outputs(response):
    if 'candidates' in response:
        return [{'b64_json':part['inlineData']['data']} for candidate in response['candidates']
                for part in candidate.get('content', {}).get('parts', [])
                if part.get('inlineData', {}).get('mimeType', '').startswith('image/')]
    return response.get('data', [])


def save_images(outputs, target, timeout):
    paths = []
    for i, item in enumerate(outputs):
        if item.get('b64_json'):
            data = base64.b64decode(item['b64_json'], validate=True)
        elif item.get('url'):
            # Deliberately unauthenticated: never send the Tako key to an image CDN.
            with urllib.request.urlopen(item['url'], timeout=timeout) as resp:
                data = resp.read()
        else:
            raise ValueError('response contains no image bytes or URL')
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            suffix = '.png'
        elif data.startswith(b'\xff\xd8\xff'):
            suffix = '.jpg'
        elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
            suffix = '.webp'
        else:
            raise ValueError('downloaded output is not a recognized PNG, JPEG or WebP image')
        path = Path(target)
        if len(outputs) > 1:
            path = path.with_name(f'{path.stem}-{i+1}{suffix}')
        else:
            path = path.with_suffix(suffix)
        if path.exists():
            raise ValueError(f'output already exists: {path}; choose a new --save-image path')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as file:
            file.write(data)
        paths.append(str(path))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='command', required=True)
    for name in ('generate', 'edit'):
        mode = modes.add_parser(name)
        if name == 'edit':
            mode.add_argument('image')
        mode.add_argument('prompt')
        mode.add_argument('--model', default='gpt-image-2')
        mode.add_argument('--n', type=int, default=1)
        mode.add_argument('--size')
        mode.add_argument('--out', help='save response JSON')
        mode.add_argument('--save-image', help='save image file(s); extension follows actual bytes')
        mode.add_argument('--timeout', type=float, default=240)
    args = parser.parse_args()
    key = os.environ.get('TAKO_API_KEY', '')
    if not key:
        parser.error('TAKO_API_KEY is required; create a user token in the Tako console')
    if not 1 <= args.n <= 128:
        parser.error('--n must be between 1 and 128')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    if args.save_image and Path(args.save_image).exists():
        parser.error('output already exists; choose a new --save-image path')
    try:
        path, body, content_type = build_request(args)
        base = os.environ.get('TAKO_BASE_URL', 'https://tako.shiroha.tech').rstrip('/')
        req = urllib.request.Request(base + path, data=body, headers={
            'Authorization':'Bearer ' + key, 'Content-Type':content_type}, method='POST')
        opener = urllib.request.build_opener(NoAPIRedirect())
        with opener.open(req, timeout=args.timeout) as resp:
            response = json.load(resp)
        outputs = image_outputs(response)
        if response.get('error') or not outputs:
            raise ValueError('API returned an error or no image; inspect the response and do not retry blindly')
        # Retain a successful response before a CDN download failure, so no regeneration is needed.
        if args.out:
            Path(args.out).write_text(json.dumps(response, ensure_ascii=False) + '\n', encoding='utf-8')
        if args.save_image:
            for saved in save_images(outputs, args.save_image, args.timeout):
                print('Saved image: ' + saved, file=sys.stderr)
        if not args.out:
            print(json.dumps(response, ensure_ascii=False))
    except urllib.error.HTTPError as error:
        try:
            message = json.loads(error.read()).get('error', {})
            if isinstance(message, dict):
                message = message.get('message', 'request rejected')
        except (ValueError, AttributeError):
            message = 'request rejected'
        print(f'Tako HTTP {error.code}: {str(message).replace(key, "[redacted]")}', file=sys.stderr)
        return 1
    except (ValueError, OSError, urllib.error.URLError) as error:
        print(str(error).replace(key, '[redacted]'), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
