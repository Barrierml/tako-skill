import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SH_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/tako-consult.sh'
PY_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/tako_consult.py'


class ConsultHelperContract(unittest.TestCase):
    def test_consult_default_model_context_and_out(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                received.append((self.path, dict(self.headers), json.loads(body)))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            'id': 'chatcmpl-test',
                            'model': 'gpt-6.2-sol',
                            'choices': [
                                {
                                    'index': 0,
                                    'message': {
                                        'role': 'assistant',
                                        'content': '1. 必须加幂等键\n2. 使用状态单调更新条件',
                                    },
                                }
                            ],
                        }
                    ).encode('utf-8')
                )

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                ctx_file = root / 'state.rs'
                ctx_file.write_text('fn transition(status: &str) {}', encoding='utf-8')
                out_json = root / 'consult.json'
                env = dict(
                    os.environ,
                    TAKO_API_KEY='consult-secret-key',
                    TAKO_BASE_URL=f'http://127.0.0.1:{server.server_port}',
                )
                run = subprocess.run(
                    [
                        str(SH_SCRIPT),
                        '并发回调到来时状态机有哪些盲点？',
                        '--context',
                        '90 秒超时后会重试一次',
                        '--context-file',
                        str(ctx_file),
                        '--focus',
                        '幂等性与状态回退',
                        '--out',
                        str(out_json),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn('必须加幂等键', run.stdout)
                saved = json.loads(out_json.read_text(encoding='utf-8'))
                self.assertEqual(saved['id'], 'chatcmpl-test')

                path, headers, payload = received[-1]
                self.assertEqual(path, '/v1/chat/completions')
                self.assertEqual(headers['Authorization'], 'Bearer consult-secret-key')
                self.assertEqual(payload['model'], 'gpt-6.2-sol')
                self.assertFalse(payload['stream'])
                self.assertEqual(payload['messages'][0]['role'], 'system')
                user_msg = payload['messages'][1]['content']
                self.assertIn('并发回调到来时状态机有哪些盲点？', user_msg)
                self.assertIn('90 秒超时后会重试一次', user_msg)
                self.assertIn('fn transition', user_msg)
                self.assertIn('幂等性与状态回退', user_msg)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_consult_errors_no_overwrite_and_missing_key(self):
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                calls.append(self.path)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"upstream failure"}}')

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                existing = root / 'existing.json'
                existing.write_text('{}', encoding='utf-8')
                env = dict(
                    os.environ,
                    TAKO_API_KEY='consult-secret-key',
                    TAKO_BASE_URL=f'http://127.0.0.1:{server.server_port}',
                )

                # Existing --out refuses overwrite before HTTP call
                r_exists = subprocess.run(
                    ['python3', str(PY_SCRIPT), 'test question', '--out', str(existing)],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_exists.returncode, 0)
                self.assertEqual(len(calls), 0)

                # Missing TAKO_API_KEY exits non-zero
                no_key_env = dict(os.environ)
                no_key_env.pop('TAKO_API_KEY', None)
                r_nokey = subprocess.run(
                    [str(SH_SCRIPT), 'test question'],
                    env=no_key_env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_nokey.returncode, 0)
                self.assertEqual(len(calls), 0)

                # HTTP 500 exits non-zero without writing --out and redacts key
                err_out = root / 'err.json'
                r_http = subprocess.run(
                    [str(SH_SCRIPT), 'test question', '--out', str(err_out)],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(r_http.returncode, 0)
                self.assertIn('HTTP 500', r_http.stderr)
                self.assertFalse(err_out.exists())
                self.assertNotIn('consult-secret-key', r_http.stderr + r_http.stdout)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
