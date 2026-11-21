#!/usr/bin/env python3
"""Tako external-brain consultation helper via POST /v1/chat/completions. Uses only the Python standard library."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Optional
import urllib.error
import urllib.request

SYSTEM_PROMPT = (
    'You are an independent senior architecture and code consultation advisor. '
    'Challenge implicit assumptions and blind spots, uncover concurrency, state-machine, '
    'and edge-case hazards, and provide concrete, actionable fixes.'
)


class NoAPIRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('API redirect refused; check TAKO_BASE_URL')


def write_atomic_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise ValueError(f'output already exists: {path}; choose a new --out path')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(tmp_path, path)
        except FileExistsError:
            raise ValueError(f'output already exists: {path}; choose a new --out path')
        except OSError:
            if path.exists():
                raise ValueError(f'output already exists: {path}; choose a new --out path')
            os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def http_error_message(error: urllib.error.HTTPError) -> str:
    try:
        raw = error.read()
        parsed = json.loads(raw)
        err = parsed.get('error', parsed)
        if isinstance(err, dict):
            return str(err.get('message') or err)
        return str(err)
    except (ValueError, AttributeError):
        return 'request rejected'


def extract_message_content(response: dict) -> str:
    choices = response.get('choices')
    if not isinstance(choices, list) or not choices:
        raise ValueError('API response contains no choices')
    message = choices[0].get('message') if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError('API response choices[0] contains no message')
    content = message.get('content')
    if isinstance(content, str):
        if not content.strip():
            raise ValueError('API response choices[0].message.content is empty')
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get('text'), str):
                parts.append(item['text'])
        joined = ''.join(parts)
        if joined.strip():
            return joined
    raise ValueError('API response contains no valid choices[0].message.content')


def assemble_user_message(
    question: str,
    context: Optional[str],
    context_file: Optional[str],
    focus: Optional[str],
) -> str:
    sections = [question.strip()]
    context_blocks = []
    if context and context.strip():
        context_blocks.append(context.strip())
    if context_file:
        ctx_path = Path(context_file)
        if not ctx_path.is_file():
            raise ValueError(f'context file not found: {ctx_path}')
        file_text = ctx_path.read_text(encoding='utf-8').strip()
        if file_text:
            context_blocks.append(f'[file: {ctx_path}]\n{file_text}')
    if context_blocks:
        sections.append('<context>\n' + '\n\n'.join(context_blocks) + '\n</context>')
    if focus and focus.strip():
        sections.append('<focus>\n' + focus.strip() + '\n</focus>')
    return '\n\n'.join(sections)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question', help='question, architecture dilemma, or review prompt')
    parser.add_argument('--model', default='gpt-6.2-sol', help='consultation model (default: gpt-6.2-sol)')
    parser.add_argument('--context', help='inline context (code, logs, constraints)')
    parser.add_argument('--context-file', help='path to a UTF-8 file to include as context')
    parser.add_argument('--focus', help='specific review angle or risk area to focus on')
    parser.add_argument('--out', help='optional path to save full JSON response; never overwrites')
    parser.add_argument('--timeout', type=float, default=120, help='HTTP timeout in seconds (default: 120)')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    key = os.environ.get('TAKO_API_KEY', '')
    if not key:
        parser.error('TAKO_API_KEY is required; create a user token in the Tako console')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    if not args.question or not args.question.strip():
        parser.error('question must be non-empty')

    out_path = Path(args.out) if args.out else None
    if out_path is not None and out_path.exists():
        parser.error(f'output already exists: {out_path}; choose a new --out path')

    base = os.environ.get('TAKO_BASE_URL', 'https://tako.shiroha.tech').rstrip('/')
    try:
        user_content = assemble_user_message(args.question, args.context, args.context_file, args.focus)
        payload = {
            'model': args.model,
            'stream': False,
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_content},
            ],
        }
        req = urllib.request.Request(
            base + '/v1/chat/completions',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={
                'Authorization': 'Bearer ' + key,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        opener = urllib.request.build_opener(NoAPIRedirect())
        with opener.open(req, timeout=args.timeout) as resp:
            if not 200 <= resp.status < 300:
                raise ValueError(f'Tako HTTP {resp.status}: unexpected response status')
            raw = resp.read()

        try:
            response = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError('API returned invalid JSON response') from exc

        if not isinstance(response, dict):
            raise ValueError('API returned unexpected non-object JSON response')
        if response.get('error'):
            err = response['error']
            msg = err.get('message', err) if isinstance(err, dict) else err
            raise ValueError(f'API returned error: {msg}')

        reply = extract_message_content(response)
        if out_path is not None:
            write_atomic_new(out_path, (json.dumps(response, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

        print(reply)
        return 0
    except urllib.error.HTTPError as error:
        msg = http_error_message(error)
        print(f'Tako HTTP {error.code}: {msg}'.replace(key, '[redacted]'), file=sys.stderr)
        return 1
    except (ValueError, OSError, urllib.error.URLError) as error:
        print(str(error).replace(key, '[redacted]'), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
