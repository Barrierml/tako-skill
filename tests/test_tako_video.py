import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/tako_video.py'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aip8AAAAASUVORK5CYII=')
MP4 = b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41' + b'\x00' * 32


def silent(cls):
    cls.log_message = lambda self, *args: None
    return cls


class VideoHelperContract(unittest.TestCase):
    def make_env(self, port):
        return dict(os.environ, TAKO_API_KEY='test-user-key',
                    TAKO_BASE_URL=f'http://127.0.0.1:{port}')

    def run_helper(self, argv, env):
        return subprocess.run(['python3', str(SCRIPT)] + argv, env=env,
                              capture_output=True, text=True)

    def test_generate_polls_and_saves_mp4(self):
        received = []
        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                received.append(('POST', self.path, json.loads(body)))
                assert self.path == '/v1/videos/generations'
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'id': 'task-42'}).encode())
            def do_GET(self):
                received.append(('GET', self.path, self.headers.get('Authorization')))
                if self.path == '/v1/videos/task-42':
                    self.send_response(200); self.end_headers()
                    self.wfile.write(json.dumps({'id': 'task-42', 'status': 'SUCCESS'}).encode())
                elif self.path == '/v1/videos/task-42/content':
                    self.send_response(200); self.end_headers()
                    self.wfile.write(MP4)
                else:
                    self.send_response(404); self.end_headers()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                env = self.make_env(server.server_port)
                run = self.run_helper(['generate', 'a red apple spins slowly',
                                       '--duration', '5', '--resolution', '480p',
                                       '--aspect-ratio', '16:9',
                                       '--out', str(root/'task.json'),
                                       '--save-video', str(root/'clip.mp4')], env)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual((root/'clip.mp4').read_bytes(), MP4)
                self.assertIn('Submitted video task: task-42', run.stderr)
                request = received[0][2]
                self.assertEqual(request['model'], 'grok-imagine-video')
                self.assertEqual(request['duration'], 5)
                self.assertEqual(request['resolution'], '480p')
                self.assertEqual(request['aspect_ratio'], '16:9')
                self.assertNotIn('image', request)
                self.assertEqual(received[1][2], 'Bearer test-user-key')
                self.assertEqual(received[2][2], 'Bearer test-user-key')
                self.assertNotIn('test-user-key', run.stderr + run.stdout)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_generate_encodes_reference_image(self):
        bodies = []
        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                bodies.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'task_id': 'task-9'}).encode())
            def do_GET(self):
                self.send_response(200); self.end_headers()
                if self.path.endswith('/content'):
                    self.wfile.write(MP4)
                else:
                    self.wfile.write(json.dumps({'status': 'SUCCESS'}).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); (root/'ref.png').write_bytes(PNG)
                env = self.make_env(server.server_port)
                run = self.run_helper(['generate', 'make it move',
                                       '--model', 'grok-imagine-video-1.5',
                                       '--resolution', '1080p',
                                       '--image', str(root/'ref.png'),
                                       '--save-video', str(root/'out.mp4')], env)
                self.assertEqual(run.returncode, 0, run.stderr)
                request = bodies[0]
                self.assertEqual(request['model'], 'grok-imagine-video-1.5')
                self.assertEqual(base64.b64decode(request['image'].split(',', 1)[1]), PNG)
                self.assertTrue(request['image'].startswith('data:image/png;base64,'))
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_failed_task_exits_nonzero_without_download(self):
        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'id': 'task-bad'}).encode())
            def do_GET(self):
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'id': 'task-bad', 'status': 'FAILURE',
                                             'error': 'moderation'}).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                env = self.make_env(server.server_port)
                run = self.run_helper(['generate', 'spin', '--poll-interval', '0.01',
                                       '--max-wait', '30',
                                       '--save-video', str(Path(temporary)/'clip.mp4')], env)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn('task-bad', run.stderr)
                self.assertFalse((Path(temporary)/'clip.mp4').exists())
                self.assertNotIn('test-user-key', run.stderr + run.stdout)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_status_downloads_finished_video(self):
        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers()
                if self.path.endswith('/content'):
                    self.wfile.write(MP4)
                else:
                    self.wfile.write(json.dumps({'id': 'task-42', 'status': 'done'}).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                env = self.make_env(server.server_port)
                run = self.run_helper(['status', 'task-42',
                                       '--save-video', str(Path(temporary)/'clip.mp4')], env)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual((Path(temporary)/'clip.mp4').read_bytes(), MP4)
                run = self.run_helper(['status', 'task-42',
                                       '--save-video', str(Path(temporary)/'clip.mp4')], env)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn('already exists', run.stderr)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_status_rejects_unfinished_download(self):
        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'id': 'task-7', 'status': 'RUNNING'}).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                env = self.make_env(server.server_port)
                run = self.run_helper(['status', 'task-7',
                                       '--save-video', str(Path(temporary)/'clip.mp4')], env)
                self.assertNotEqual(run.returncode, 0)
                self.assertFalse((Path(temporary)/'clip.mp4').exists())
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_http_error_exits_nonzero_without_saving_success(self):
        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(400); self.end_headers()
                self.wfile.write(b'{"error":{"message":"invalid prompt"}}')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                env = self.make_env(server.server_port)
                run = self.run_helper(['generate', 'draw',
                                       '--out', str(Path(temporary)/'task.json')], env)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn('HTTP 400', run.stderr)
                self.assertFalse((Path(temporary)/'task.json').exists())
                self.assertNotIn('test-user-key', run.stderr + run.stdout)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_generate_arguments_validation(self):
        env = dict(os.environ, TAKO_API_KEY='test-user-key')
        run = self.run_helper(['generate', 'spin', '--duration', '0'], env)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('--duration', run.stderr)
        run = self.run_helper(['status'], env)
        self.assertNotEqual(run.returncode, 0)

    def test_content_json_url_download_has_no_tako_auth(self):
        spec = importlib.util.spec_from_file_location('tako_video', SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        auth = []
        @silent
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                auth.append((self.path, self.headers.get('Authorization')))
                if self.path == '/v1/videos/task-1/content':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    url = f'http://127.0.0.1:{self.server.server_port}/cdn/video.mp4'
                    self.wfile.write(json.dumps({'url': url}).encode())
                elif self.path == '/cdn/video.mp4':
                    self.send_response(200); self.end_headers()
                    self.wfile.write(MP4)
                else:
                    self.send_response(404); self.end_headers()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            data = module.get_content(base, 'task-1', 'test-user-key', 10)
            self.assertEqual(data, MP4)
            self.assertEqual(auth[0][1], 'Bearer test-user-key')
            self.assertIsNone(auth[1][1])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_save_video_rejects_non_mp4_and_overwrites(self):
        spec = importlib.util.spec_from_file_location('tako_video', SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                module.save_video(b'not a video', root/'clip.mp4')
            saved = module.save_video(MP4, root/'clip')
            self.assertTrue(saved.endswith('.mp4'))
            with self.assertRaises(ValueError):
                module.save_video(MP4, root/'clip')


if __name__ == '__main__':
    unittest.main()
