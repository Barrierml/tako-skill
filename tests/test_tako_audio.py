import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SH_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/tako-audio.sh'
PY_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/tako_audio.py'
FAKE_MP3 = b'ID3\x03\x00\x00\x00\x00\x00\x10FAKE-MP3-AUDIO-BYTES'
FAKE_WAV = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00'


class AudioHelperContract(unittest.TestCase):
    def test_tts_default_and_metadata_out(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get('Content-Length', '0'))
                body = self.rfile.read(length)
                received.append((self.path, dict(self.headers), body))
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('x-speech-final-text-preview', 'ni hao, welcome to bingtang tts')
                self.end_headers()
                self.wfile.write(FAKE_MP3)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                audio_out = root / 'hello.mp3'
                meta_out = root / 'meta.json'
                env = dict(
                    os.environ,
                    TAKO_API_KEY='test-user-key',
                    TAKO_BASE_URL=f'http://127.0.0.1:{server.server_port}',
                )
                run = subprocess.run(
                    [
                        str(SH_SCRIPT),
                        'tts',
                        '你好，欢迎使用冰糖配音',
                        '--save-audio',
                        str(audio_out),
                        '--out',
                        str(meta_out),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(audio_out.read_bytes(), FAKE_MP3)
                meta = json.loads(meta_out.read_text(encoding='utf-8'))
                self.assertEqual(meta['saved_path'], str(audio_out))
                self.assertEqual(meta['model'], 'mimo-v2.5-tts')
                self.assertEqual(meta['voice'], '冰糖')
                self.assertEqual(meta['response_format'], 'mp3')
                self.assertEqual(meta['bytes'], len(FAKE_MP3))
                self.assertEqual(meta['x-speech-final-text-preview'], 'ni hao, welcome to bingtang tts')
                path, headers, body = received[-1]
                self.assertEqual(path, '/v1/audio/speech')
                self.assertEqual(headers['Authorization'], 'Bearer test-user-key')
                payload = json.loads(body)
                self.assertEqual(payload['model'], 'mimo-v2.5-tts')
                self.assertEqual(payload['voice'], '冰糖')
                self.assertEqual(payload['input'], '你好，欢迎使用冰糖配音')
                self.assertEqual(payload['response_format'], 'mp3')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_tts_instruct_and_voiceclone_model_autoswitch_and_explicit_override(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                received.append((self.path, json.loads(body)))
                self.send_response(200)
                self.send_header('Content-Type', 'audio/wav')
                self.end_headers()
                self.wfile.write(FAKE_WAV)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                sample = root / 'sample.mp3'
                sample.write_bytes(FAKE_MP3)
                env = dict(
                    os.environ,
                    TAKO_API_KEY='test-user-key',
                    TAKO_BASE_URL=f'http://127.0.0.1:{server.server_port}',
                )

                # --instructions auto-switches to mimo-v2.5-tts-instruct
                run1 = subprocess.run(
                    [
                        'python3',
                        str(PY_SCRIPT),
                        'tts',
                        '窗外正下着细雨。',
                        '--instructions',
                        '语速舒缓，温柔电台口吻',
                        '--format',
                        'wav',
                        '--speed',
                        '0.95',
                        '--save-audio',
                        str(root / 'instruct.wav'),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run1.returncode, 0, run1.stderr)
                _, req1 = received[-1]
                self.assertEqual(req1['model'], 'mimo-v2.5-tts-instruct')
                self.assertEqual(req1['instructions'], '语速舒缓，温柔电台口吻')
                self.assertEqual(req1['response_format'], 'wav')
                self.assertEqual(req1['speed'], 0.95)

                # --voice-sample auto-switches to mimo-v2.5-tts-voiceclone
                run2 = subprocess.run(
                    [
                        'python3',
                        str(PY_SCRIPT),
                        'tts',
                        '用参考音色朗读这段话。',
                        '--voice-sample',
                        str(sample),
                        '--save-audio',
                        str(root / 'clone.mp3'),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run2.returncode, 0, run2.stderr)
                _, req2 = received[-1]
                self.assertEqual(req2['model'], 'mimo-v2.5-tts-voiceclone')
                self.assertTrue(req2['voice'].startswith('data:audio/mpeg;base64,'))
                self.assertEqual(base64.b64decode(req2['voice'].split(',', 1)[1]), FAKE_MP3)

                # explicit --model is preserved even when --instructions is set
                run3 = subprocess.run(
                    [
                        'python3',
                        str(PY_SCRIPT),
                        'tts',
                        '测试显式模型保留',
                        '--model',
                        'mimo-v2.5-tts',
                        '--instructions',
                        '轻快',
                        '--save-audio',
                        str(root / 'explicit.mp3'),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run3.returncode, 0, run3.stderr)
                _, req3 = received[-1]
                self.assertEqual(req3['model'], 'mimo-v2.5-tts')
                self.assertEqual(req3['instructions'], '轻快')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_tts_rejects_oversized_sample_and_overwrites_and_bad_responses(self):
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                calls.append(self.path)
                if self.path == '/v1/audio/speech' and len(calls) == 1:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"error":{"message":"upstream returned json"}}')
                elif len(calls) == 2:
                    self.send_response(502)
                    self.end_headers()
                    self.wfile.write(b'{"error":{"message":"bad gateway"}}')
                else:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'')

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                env = dict(
                    os.environ,
                    TAKO_API_KEY='secret-audio-key',
                    TAKO_BASE_URL=f'http://127.0.0.1:{server.server_port}',
                )

                # Oversized voice sample (> 10485760 bytes) fails before any HTTP call
                big_sample = root / 'big.wav'
                with big_sample.open('wb') as f:
                    f.truncate(10485761)
                r_big = subprocess.run(
                    [
                        'python3',
                        str(PY_SCRIPT),
                        'tts',
                        'hello',
                        '--voice-sample',
                        str(big_sample),
                        '--save-audio',
                        str(root / 'out1.mp3'),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_big.returncode, 0)
                self.assertEqual(len(calls), 0)

                # Existing --save-audio refuses overwrite before HTTP call
                existing = root / 'exists.mp3'
                existing.write_bytes(b'old')
                r_exists = subprocess.run(
                    ['python3', str(PY_SCRIPT), 'tts', 'hello', '--save-audio', str(existing)],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_exists.returncode, 0)
                self.assertEqual(existing.read_bytes(), b'old')
                self.assertEqual(len(calls), 0)

                # Existing --out refuses overwrite before HTTP call
                existing_meta = root / 'exists.json'
                existing_meta.write_text('{}', encoding='utf-8')
                r_out_exists = subprocess.run(
                    [
                        'python3',
                        str(PY_SCRIPT),
                        'tts',
                        'hello',
                        '--save-audio',
                        str(root / 'fresh.mp3'),
                        '--out',
                        str(existing_meta),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_out_exists.returncode, 0)
                self.assertEqual(len(calls), 0)

                # 200 with JSON error payload must NOT write file
                bad_json_target = root / 'bad-json.mp3'
                bad_json_meta = root / 'bad-json.json'
                r_json = subprocess.run(
                    [
                        'python3',
                        str(PY_SCRIPT),
                        'tts',
                        'hello',
                        '--save-audio',
                        str(bad_json_target),
                        '--out',
                        str(bad_json_meta),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_json.returncode, 0)
                self.assertFalse(bad_json_target.exists())
                self.assertFalse(bad_json_meta.exists())

                # 502 HTTP error must NOT write file and must redact key
                http_err_target = root / 'http-err.mp3'
                r_http = subprocess.run(
                    ['python3', str(PY_SCRIPT), 'tts', 'hello', '--save-audio', str(http_err_target)],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_http.returncode, 0)
                self.assertIn('HTTP 502', r_http.stderr)
                self.assertFalse(http_err_target.exists())
                self.assertNotIn('secret-audio-key', r_http.stderr + r_http.stdout)

                # Empty 200 body must NOT write file
                empty_target = root / 'empty.mp3'
                r_empty = subprocess.run(
                    ['python3', str(PY_SCRIPT), 'tts', 'hello', '--save-audio', str(empty_target)],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_empty.returncode, 0)
                self.assertFalse(empty_target.exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_asr_multipart_and_error_handling(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                received.append((self.path, dict(self.headers), body))
                if len(received) == 1:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'text': '你好，Tako 语音转写成功。'}).encode('utf-8'))
                else:
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b'{"error":{"message":"invalid token"}}')

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                sample = root / 'clip.mp3'
                sample.write_bytes(FAKE_MP3)
                asr_json = root / 'asr.json'
                env = dict(
                    os.environ,
                    TAKO_API_KEY='test-asr-key',
                    TAKO_BASE_URL=f'http://127.0.0.1:{server.server_port}',
                )
                run = subprocess.run(
                    [
                        str(SH_SCRIPT),
                        'asr',
                        str(sample),
                        '--language',
                        'zh',
                        '--prompt',
                        'Tako Switch',
                        '--out',
                        str(asr_json),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout.strip(), '你好，Tako 语音转写成功。')
                self.assertEqual(json.loads(asr_json.read_text(encoding='utf-8'))['text'], '你好，Tako 语音转写成功。')
                path, headers, body = received[0]
                self.assertEqual(path, '/v1/audio/transcriptions')
                self.assertIn('multipart/form-data', headers['Content-Type'])
                self.assertIn(b'name="model"\r\n\r\nspeech_asr', body)
                self.assertIn(b'name="language"\r\n\r\nzh', body)
                self.assertIn(b'name="prompt"\r\n\r\nTako Switch', body)
                self.assertIn(FAKE_MP3, body)

                # Missing TAKO_API_KEY fails non-zero
                no_key_env = dict(os.environ)
                no_key_env.pop('TAKO_API_KEY', None)
                r_nokey = subprocess.run(
                    [str(SH_SCRIPT), 'asr', str(sample)],
                    env=no_key_env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_nokey.returncode, 0)

                # HTTP 401 fails non-zero and refuses to overwrite existing --out
                r_err = subprocess.run(
                    [str(SH_SCRIPT), 'asr', str(sample), '--out', str(root / 'err.json')],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_err.returncode, 0)
                self.assertFalse((root / 'err.json').exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
