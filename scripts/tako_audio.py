#!/usr/bin/env python3
"""Tako audio helper (TTS, voice instruct, zero-shot voice clone, and ASR). Uses only the Python standard library."""
import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request
import uuid

MAX_VOICE_SAMPLE_BYTES = 10485760  # 10 MiB

AUDIO_MIME_TYPES = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.wave': 'audio/wav',
    '.opus': 'audio/opus',
    '.ogg': 'audio/ogg',
    '.oga': 'audio/ogg',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.mp4': 'audio/mp4',
    '.aac': 'audio/aac',
    '.webm': 'audio/webm',
}


class NoAPIRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('API redirect refused; check TAKO_BASE_URL')


def detect_audio_mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in AUDIO_MIME_TYPES:
        return AUDIO_MIME_TYPES[ext]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or 'application/octet-stream'


def write_atomic_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise ValueError(f'output already exists: {path}; choose a new path')
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
            raise ValueError(f'output already exists: {path}; choose a new path')
        except OSError:
            if path.exists():
                raise ValueError(f'output already exists: {path}; choose a new path')
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


def resolve_tts_model(explicit_model, voice_sample, instructions) -> str:
    if explicit_model is not None:
        return explicit_model
    if voice_sample:
        return 'mimo-v2.5-tts-voiceclone'
    if instructions and instructions.strip():
        return 'mimo-v2.5-tts-instruct'
    return 'mimo-v2.5-tts'


def run_tts(args, base: str, key: str) -> int:
    if not args.text or not args.text.strip():
        raise ValueError('text must be non-empty')
    if args.speed is not None and args.speed <= 0:
        raise ValueError('--speed must be positive')

    save_path = Path(args.save_audio)
    if save_path.exists():
        raise ValueError(f'output already exists: {save_path}; choose a new --save-audio path')

    out_path = Path(args.out) if args.out else None
    if out_path is not None and out_path.exists():
        raise ValueError(f'output already exists: {out_path}; choose a new --out path')

    instructions = args.instructions.strip() if args.instructions and args.instructions.strip() else None
    model = resolve_tts_model(args.model, args.voice_sample, instructions)

    payload = {
        'model': model,
        'input': args.text,
        'response_format': args.format,
    }

    if args.voice_sample:
        sample_path = Path(args.voice_sample)
        if not sample_path.is_file():
            raise ValueError(f'voice sample file not found: {sample_path}')
        sample_bytes = sample_path.read_bytes()
        if not sample_bytes:
            raise ValueError(f'voice sample file is empty: {sample_path}')
        if len(sample_bytes) > MAX_VOICE_SAMPLE_BYTES:
            raise ValueError(
                f'voice sample exceeds {MAX_VOICE_SAMPLE_BYTES} bytes limit (got {len(sample_bytes)} bytes)'
            )
        sample_mime = detect_audio_mime(sample_path)
        payload['voice'] = f'data:{sample_mime};base64,' + base64.b64encode(sample_bytes).decode('ascii')
        meta_voice = '<voice_sample>'
    else:
        payload['voice'] = args.voice
        meta_voice = args.voice

    if instructions:
        payload['instructions'] = instructions
    if args.speed is not None:
        payload['speed'] = args.speed

    req = urllib.request.Request(
        base + '/v1/audio/speech',
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
        audio_bytes = resp.read()
        preview = resp.headers.get('x-speech-final-text-preview')

    if not audio_bytes:
        raise ValueError('API returned empty audio response; nothing saved')
    stripped = audio_bytes.lstrip()
    if stripped.startswith(b'{'):
        detail = 'API returned JSON error payload instead of audio'
        try:
            err_json = json.loads(stripped.decode('utf-8', errors='replace'))
            if isinstance(err_json, dict):
                err = err_json.get('error', err_json)
                if isinstance(err, dict) and err.get('message'):
                    detail = str(err['message'])
                elif err:
                    detail = str(err)
        except ValueError:
            pass
        raise ValueError(f'{detail}; nothing saved')

    write_atomic_new(save_path, audio_bytes)

    metadata = {
        'saved_path': str(save_path),
        'model': model,
        'voice': meta_voice,
        'response_format': args.format,
        'bytes': len(audio_bytes),
        'x-speech-final-text-preview': preview,
    }
    if out_path is not None:
        write_atomic_new(out_path, (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    else:
        print(json.dumps(metadata, ensure_ascii=False))
    print('Saved audio: ' + str(save_path), file=sys.stderr)
    return 0


def run_asr(args, base: str, key: str) -> int:
    audio_path = Path(args.audio_file)
    if not audio_path.is_file():
        raise ValueError(f'audio file not found: {audio_path}')
    audio_bytes = audio_path.read_bytes()
    if not audio_bytes:
        raise ValueError(f'audio file is empty: {audio_path}')

    out_path = Path(args.out) if args.out else None
    if out_path is not None and out_path.exists():
        raise ValueError(f'output already exists: {out_path}; choose a new --out path')

    boundary = 'tako-audio-' + uuid.uuid4().hex
    chunks = []
    fields = [('model', args.model)]
    if args.language:
        fields.append(('language', args.language))
    if args.prompt:
        fields.append(('prompt', args.prompt))
    for name, value in fields:
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode('utf-8')
        )

    mime = detect_audio_mime(audio_path)
    safe_filename = audio_path.name.replace('"', '_')
    chunks.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{safe_filename}"\r\n'
        f'Content-Type: {mime}\r\n\r\n'.encode('utf-8')
    )
    chunks.append(audio_bytes)
    chunks.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
    body = b''.join(chunks)

    req = urllib.request.Request(
        base + '/v1/audio/transcriptions',
        data=body,
        headers={
            'Authorization': 'Bearer ' + key,
            'Content-Type': f'multipart/form-data; boundary={boundary}',
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
        raise ValueError('API returned invalid JSON response for ASR') from exc

    if not isinstance(response, dict):
        raise ValueError('API returned unexpected non-object JSON response for ASR')
    if response.get('error'):
        err = response['error']
        msg = err.get('message', err) if isinstance(err, dict) else err
        raise ValueError(f'API returned error: {msg}')
    if 'text' not in response or not isinstance(response['text'], str):
        raise ValueError('API response contains no text field')

    if out_path is not None:
        write_atomic_new(out_path, (json.dumps(response, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

    print(response['text'])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='command', required=True)

    tts = modes.add_parser('tts', help='synthesize speech via POST /v1/audio/speech')
    tts.add_argument('text', help='text to synthesize into speech')
    tts.add_argument(
        '--model',
        default=None,
        help='TTS model (default: mimo-v2.5-tts; auto-switches to mimo-v2.5-tts-voiceclone with --voice-sample or mimo-v2.5-tts-instruct with --instructions)',
    )
    tts.add_argument('--voice', default='冰糖', help='preset voice name (default: 冰糖)')
    tts.add_argument('--instructions', help='emotion, pacing, or tone instructions')
    tts.add_argument('--voice-sample', help='local audio sample file (<= 10485760 bytes) for voice cloning')
    tts.add_argument('--format', choices=('mp3', 'wav', 'opus'), default='mp3', help='output format (default: mp3)')
    tts.add_argument('--speed', type=float, help='optional speech speed multiplier')
    tts.add_argument('--save-audio', required=True, help='output audio file path; never overwrites')
    tts.add_argument('--out', help='optional metadata JSON output path; never overwrites')
    tts.add_argument('--timeout', type=float, default=120, help='HTTP timeout in seconds (default: 120)')

    asr = modes.add_parser('asr', help='transcribe audio via POST /v1/audio/transcriptions')
    asr.add_argument('audio_file', help='local audio file path to transcribe')
    asr.add_argument('--model', default='speech_asr', help='ASR model (default: speech_asr)')
    asr.add_argument('--language', help='optional ISO language code, e.g. zh or en')
    asr.add_argument('--prompt', help='optional context or vocabulary hint')
    asr.add_argument('--out', help='optional full JSON response output path; never overwrites')
    asr.add_argument('--timeout', type=float, default=120, help='HTTP timeout in seconds (default: 120)')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    key = os.environ.get('TAKO_API_KEY', '')
    if not key:
        parser.error('TAKO_API_KEY is required; create a user token in the Tako console')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')

    base = os.environ.get('TAKO_BASE_URL', 'https://tako.shiroha.tech').rstrip('/')
    try:
        if args.command == 'tts':
            return run_tts(args, base, key)
        return run_asr(args, base, key)
    except urllib.error.HTTPError as error:
        msg = http_error_message(error)
        print(f'Tako HTTP {error.code}: {msg}'.replace(key, '[redacted]'), file=sys.stderr)
        return 1
    except (ValueError, OSError, urllib.error.URLError) as error:
        print(str(error).replace(key, '[redacted]'), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
