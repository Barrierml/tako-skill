import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
AUDIO_SCRIPT = ROOT / 'scripts/tako-audio.sh'
CONSULT_SCRIPT = ROOT / 'scripts/tako-consult.sh'

# Minimal valid ID3v2 header + MPEG-1 Layer III frame sync bytes
MP3_BYTES = b'ID3\x04\x00\x00\x00\x00\x00\x00\xff\xfb\x90\x64' + b'\x00' * 128


def silent(cls):
    cls.log_message = lambda self, *args: None
    return cls


class AudioAndConsultContract(unittest.TestCase):
    def make_env(self, port, api_key='cr_test'):
        env = dict(os.environ, TAKO_BASE_URL=f'http://127.0.0.1:{port}')
        if api_key is None:
            env.pop('TAKO_API_KEY', None)
        else:
            env['TAKO_API_KEY'] = api_key
        return env

    def run_script(self, script, argv, env):
        return subprocess.run(
            [str(script)] + argv,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_tts_default_bingtang_saves_mp3_and_meta(self):
        received = []

        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                raw = self.rfile.read(length)
                received.append((
                    self.path,
                    self.headers.get('Authorization'),
                    json.loads(raw),
                ))
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Content-Length', str(len(MP3_BYTES)))
                self.send_header('X-Speech-Final-Text-Preview', 'hello')
                self.end_headers()
                self.wfile.write(MP3_BYTES)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                tmp = Path(temporary)
                out_mp3 = tmp / 'out.mp3'
                meta_json = tmp / 'meta.json'
                env = self.make_env(server.server_port)
                run = self.run_script(
                    AUDIO_SCRIPT,
                    [
                        'tts',
                        '你好，我是冰糖',
                        '--save-audio',
                        str(out_mp3),
                        '--out',
                        str(meta_json),
                    ],
                    env,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(len(received), 1)
                path, auth, payload = received[0]
                self.assertEqual(path, '/v1/audio/speech')
                self.assertEqual(auth, 'Bearer cr_test')
                self.assertEqual(payload.get('model'), 'mimo-v2.5-tts')
                self.assertEqual(payload.get('voice'), '冰糖')
                self.assertEqual(payload.get('response_format'), 'mp3')
                self.assertEqual(payload.get('input'), '你好，我是冰糖')

                self.assertTrue(out_mp3.exists())
                self.assertEqual(out_mp3.read_bytes(), MP3_BYTES)

                self.assertTrue(meta_json.exists())
                meta = json.loads(meta_json.read_text(encoding='utf-8'))
                self.assertIn('saved_path', meta)
                self.assertIn('bytes', meta)
                self.assertEqual(
                    Path(meta['saved_path']).resolve(),
                    out_mp3.resolve(),
                )
                self.assertEqual(meta['bytes'], len(MP3_BYTES))
                self.assertNotIn('cr_test', run.stdout + run.stderr)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_tts_instructions_and_voice_clone_routing(self):
        received = []

        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                raw = self.rfile.read(length)
                received.append((self.path, json.loads(raw)))
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Content-Length', str(len(MP3_BYTES)))
                self.end_headers()
                self.wfile.write(MP3_BYTES)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                tmp = Path(temporary)
                env = self.make_env(server.server_port)

                instruct_mp3 = tmp / 'instruct.mp3'
                run_instruct = self.run_script(
                    AUDIO_SCRIPT,
                    [
                        'tts',
                        '你好，我是冰糖',
                        '--instructions',
                        '温柔电台主播口吻',
                        '--save-audio',
                        str(instruct_mp3),
                    ],
                    env,
                )
                self.assertEqual(run_instruct.returncode, 0, run_instruct.stderr)
                self.assertEqual(instruct_mp3.read_bytes(), MP3_BYTES)
                self.assertEqual(received[-1][0], '/v1/audio/speech')
                self.assertEqual(
                    received[-1][1].get('model'),
                    'mimo-v2.5-tts-instruct',
                )
                self.assertEqual(
                    received[-1][1].get('instructions'),
                    '温柔电台主播口吻',
                )

                sample_mp3 = tmp / 'sample.mp3'
                sample_mp3.write_bytes(MP3_BYTES)
                clone_mp3 = tmp / 'clone.mp3'
                run_clone = self.run_script(
                    AUDIO_SCRIPT,
                    [
                        'tts',
                        '你好，我是复刻声音',
                        '--voice-sample',
                        str(sample_mp3),
                        '--save-audio',
                        str(clone_mp3),
                    ],
                    env,
                )
                self.assertEqual(run_clone.returncode, 0, run_clone.stderr)
                self.assertEqual(clone_mp3.read_bytes(), MP3_BYTES)
                self.assertEqual(received[-1][0], '/v1/audio/speech')
                self.assertEqual(
                    received[-1][1].get('model'),
                    'mimo-v2.5-tts-voiceclone',
                )
                voice_val = received[-1][1].get('voice', '')
                self.assertTrue(voice_val.startswith('data:audio/'), voice_val[:40])
                self.assertIn(';base64,', voice_val)
                encoded_sample = voice_val.split(';base64,', 1)[1]
                self.assertEqual(base64.b64decode(encoded_sample), MP3_BYTES)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_tts_refuses_overwrite_and_never_writes_error_json_as_audio(self):
        mode = {'kind': '401'}

        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                self.rfile.read(length)
                if mode['kind'] == '401':
                    payload = b'{"error":{"message":"unauthorized"}}'
                    self.send_response(401)
                else:
                    payload = b'{"error":{"message":"quota"}}'
                    self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                tmp = Path(temporary)
                env = self.make_env(server.server_port)

                existing = tmp / 'existing.mp3'
                existing.write_bytes(b'ORIGINAL_AUDIO_BYTES')
                run_overwrite = self.run_script(
                    AUDIO_SCRIPT,
                    ['tts', '你好', '--save-audio', str(existing)],
                    env,
                )
                self.assertNotEqual(run_overwrite.returncode, 0)
                self.assertEqual(existing.read_bytes(), b'ORIGINAL_AUDIO_BYTES')

                mode['kind'] = '401'
                err_401 = tmp / 'err401.mp3'
                run_401 = self.run_script(
                    AUDIO_SCRIPT,
                    ['tts', '你好', '--save-audio', str(err_401)],
                    env,
                )
                self.assertNotEqual(run_401.returncode, 0)
                self.assertFalse(err_401.exists())

                mode['kind'] = '200_error'
                err_200 = tmp / 'err200.mp3'
                run_200 = self.run_script(
                    AUDIO_SCRIPT,
                    ['tts', '你好', '--save-audio', str(err_200)],
                    env,
                )
                self.assertNotEqual(run_200.returncode, 0)
                self.assertFalse(err_200.exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_asr_multipart_transcription(self):
        received = []

        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                raw = self.rfile.read(length)
                received.append((
                    self.path,
                    self.headers.get('Authorization'),
                    self.headers.get('Content-Type', ''),
                    raw,
                ))
                resp = json.dumps({'text': '测试转写成功'}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                tmp = Path(temporary)
                sample_mp3 = tmp / 'sample.mp3'
                sample_mp3.write_bytes(MP3_BYTES)
                asr_json = tmp / 'asr.json'
                env = self.make_env(server.server_port)

                run = self.run_script(
                    AUDIO_SCRIPT,
                    [
                        'asr',
                        str(sample_mp3),
                        '--language',
                        'zh',
                        '--out',
                        str(asr_json),
                    ],
                    env,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(len(received), 1)
                path, auth, content_type, raw = received[0]
                self.assertEqual(path, '/v1/audio/transcriptions')
                self.assertEqual(auth, 'Bearer cr_test')
                self.assertIn('multipart/form-data', content_type)
                self.assertIn(b'speech_asr', raw)
                self.assertIn(b'zh', raw)
                self.assertIn(MP3_BYTES, raw)

                self.assertIn('测试转写成功', run.stdout)
                self.assertTrue(asr_json.exists())
                saved = json.loads(asr_json.read_text(encoding='utf-8'))
                self.assertEqual(saved.get('text'), '测试转写成功')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_consult_second_opinion_and_error_handling(self):
        received = []
        reply_text = '建议为每台机器持久化独立 device_id，避免同名覆盖。'
        mode = {'status': 200}

        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                raw = self.rfile.read(length)
                received.append((
                    self.path,
                    self.headers.get('Authorization'),
                    json.loads(raw),
                ))
                if mode['status'] != 200:
                    err = b'{"error":{"message":"upstream failure"}}'
                    self.send_response(mode['status'])
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(err)))
                    self.end_headers()
                    self.wfile.write(err)
                    return
                resp = json.dumps({
                    'id': 'chatcmpl-test',
                    'object': 'chat.completion',
                    'model': 'gpt-6.2-sol',
                    'choices': [
                        {
                            'index': 0,
                            'message': {'role': 'assistant', 'content': reply_text},
                            'finish_reason': 'stop',
                        }
                    ],
                }, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                tmp = Path(temporary)
                consult_json = tmp / 'consult.json'
                env = self.make_env(server.server_port)

                run = self.run_script(
                    CONSULT_SCRIPT,
                    [
                        '评估双机 OAuth 并发隐患',
                        '--context',
                        '同名删旧 token',
                        '--focus',
                        '并发安全',
                        '--out',
                        str(consult_json),
                    ],
                    env,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(len(received), 1)
                path, auth, payload = received[0]
                self.assertEqual(path, '/v1/chat/completions')
                self.assertEqual(auth, 'Bearer cr_test')
                self.assertEqual(payload.get('model'), 'gpt-6.2-sol')
                self.assertIs(payload.get('stream'), False)
                serialized_messages = json.dumps(payload.get('messages', []), ensure_ascii=False)
                self.assertIn('评估双机 OAuth 并发隐患', serialized_messages)
                self.assertIn('同名删旧 token', serialized_messages)
                self.assertIn('并发安全', serialized_messages)

                self.assertIn(reply_text, run.stdout)
                self.assertTrue(consult_json.exists())
                saved_text = consult_json.read_text(encoding='utf-8')
                saved_json = json.loads(saved_text)
                self.assertIn(reply_text, json.dumps(saved_json, ensure_ascii=False))
                self.assertNotIn('cr_test', run.stdout + run.stderr)

                env_no_key = self.make_env(server.server_port, api_key=None)
                run_no_key = self.run_script(
                    CONSULT_SCRIPT,
                    ['评估双机 OAuth 并发隐患'],
                    env_no_key,
                )
                self.assertNotEqual(run_no_key.returncode, 0)

                mode['status'] = 500
                fail_json = tmp / 'fail.json'
                run_500 = self.run_script(
                    CONSULT_SCRIPT,
                    ['评估双机 OAuth 并发隐患', '--out', str(fail_json)],
                    env,
                )
                self.assertNotEqual(run_500.returncode, 0)
                self.assertFalse(fail_json.exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
