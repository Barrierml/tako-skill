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

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/tako_image.py'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aip8AAAAASUVORK5CYII=')


class ImageHelperContract(unittest.TestCase):
    def test_routes_reference_images_and_saves_outputs(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                received.append((self.path, dict(self.headers), body))
                self.send_response(200)
                self.end_headers()
                if ':generateContent' in self.path:
                    result = {'candidates':[{'content':{'parts':[{'inlineData':{'mimeType':'image/png','data':base64.b64encode(PNG).decode()}}]}}]}
                else:
                    result = {'data':[{'b64_json':base64.b64encode(PNG).decode()}]}
                self.wfile.write(json.dumps(result).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); (root/'reference.png').write_bytes(PNG)
                env = dict(os.environ, TAKO_API_KEY='test-user-key', TAKO_BASE_URL=f'http://127.0.0.1:{server.server_port}')
                for model in ('gpt-image-2', 'gemini-3.1-flash-image', 'grok-imagine-image-quality'):
                    output = root/(model+'.png')
                    run = subprocess.run(['python3',str(SCRIPT),'edit',str(root/'reference.png'),'keep the blue circle','--model',model,'--out',str(root/(model+'.json')),'--save-image',str(output)],env=env,capture_output=True,text=True)
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertEqual(output.read_bytes(),PNG)
                    self.assertEqual(received[-1][1]['Authorization'],'Bearer test-user-key')
                    path, headers, body = received[-1]
                    if model.startswith('gemini-'):
                        self.assertEqual(path,f'/v1beta/models/{model}:generateContent')
                        request=json.loads(body)
                        self.assertEqual(base64.b64decode(request['contents'][0]['parts'][1]['inlineData']['data']),PNG)
                        self.assertEqual(request['generationConfig']['responseModalities'],['TEXT','IMAGE'])
                    elif model.startswith('grok-'):
                        request=json.loads(body)
                        self.assertEqual(request['response_format'],'b64_json')
                        self.assertEqual(base64.b64decode(request['images'][0]['image_url'].split(',',1)[1]),PNG)
                    else:
                        self.assertIn('multipart/form-data',headers['Content-Type'])
                        self.assertIn(PNG,body)
                        self.assertIn(b'name="response_format"',body)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_http_error_exits_nonzero_without_saving_success(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_POST(self):
                self.send_response(400);self.end_headers()
                self.wfile.write(b'{"error":{"message":"invalid image"}}')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                out=Path(temporary)/'response.json'
                env=dict(os.environ,TAKO_API_KEY='test-user-key',TAKO_BASE_URL=f'http://127.0.0.1:{server.server_port}')
                run=subprocess.run(['python3',str(SCRIPT),'generate','draw','--out',str(out)],env=env,capture_output=True,text=True)
                self.assertNotEqual(run.returncode,0)
                self.assertIn('HTTP 400',run.stderr)
                self.assertFalse(out.exists())
                self.assertNotIn('test-user-key',run.stderr+run.stdout)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_image_download_does_not_send_tako_auth(self):
        spec=importlib.util.spec_from_file_location('tako_image',SCRIPT)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        auth=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_GET(self):
                auth.append(self.headers.get('Authorization'))
                self.send_response(200);self.end_headers();self.wfile.write(PNG)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                output=Path(temporary)/'image.png'
                module.save_images([{'url':f'http://127.0.0.1:{server.server_port}/image'}],output,10)
                self.assertEqual(output.read_bytes(),PNG)
                self.assertEqual(auth,[None])
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__ == '__main__':
    unittest.main()
