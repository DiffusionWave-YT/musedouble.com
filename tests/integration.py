"""Isolated HTTP/security integration test; the GPU server is simulated here."""
import base64
import http.cookiejar
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aY5sAAAAASUVORK5CYII=')
prompts = {}

class Comfy(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, data, mime='application/json'):
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.end_headers()
        self.wfile.write(data if isinstance(data, bytes) else json.dumps(data).encode())

    def do_GET(self):
        if self.path == '/system_stats':
            self.reply({'system': {'os': 'test'}})
        elif self.path.startswith('/history/'):
            pid = self.path.split('/')[-1]
            workflow = prompts[pid]
            output = next(k for k, n in workflow.items() if n['_meta']['title'] == 'FINAL_IMAGE')
            self.reply({pid: {'status': {'completed': True, 'status_str': 'success'}, 'outputs': {output: {'images': [{'filename': 'result.png', 'type': 'output', 'subfolder': ''}]}}}})
        elif self.path.startswith('/view?'):
            self.reply(PNG, 'image/png')
        else:
            self.send_error(404)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers['Content-Length']))
        if self.path == '/prompt':
            pid = str(uuid.uuid4())
            prompts[pid] = json.loads(raw)['prompt']
            self.reply({'prompt_id': pid})
        elif self.path == '/upload/image':
            assert b'musedouble-' in raw
            self.reply({'name': 'reference-test.png', 'subfolder': '', 'type': 'input'})
        else:
            self.send_error(404)

class Client:
    def __init__(self, base):
        self.base = base
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        self.csrf = ''

    def call(self, action, data=None, files=None, expected=200, token=True):
        headers = {}
        body = None
        if data is not None:
            headers['X-CSRF-Token'] = self.csrf if token else 'wrong'
            if files:
                boundary = '----muse' + uuid.uuid4().hex
                parts = []
                for key, value in data.items():
                    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
                for key, (name, content, mime) in files.items():
                    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + content + b'\r\n')
                parts.append(f'--{boundary}--\r\n'.encode())
                body = b''.join(parts)
                headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
            else:
                headers['Content-Type'] = 'application/json'
                body = json.dumps(data).encode()
        req = urllib.request.Request(self.base + '/api.php?action=' + action, body, headers)
        try:
            response = self.opener.open(req, timeout=20)
        except urllib.error.HTTPError as err:
            response = err
        raw = response.read()
        assert response.code == expected, (action, response.code, expected, raw[:500])
        if response.headers.get_content_type() != 'application/json':
            return raw
        result = json.loads(raw)
        if 'csrf' in result:
            self.csrf = result['csrf']
        return result

def run():
    workflow_dir = Path(sys.argv[1]).resolve()
    password = os.environ['MUSEDOUBLE_ADMIN_PASSWORD']
    storage = Path(tempfile.mkdtemp(prefix='musedouble-tests-')).resolve()
    assert storage.parent == Path(tempfile.gettempdir()).resolve()
    env = dict(os.environ, MUSEDOUBLE_DATA_DIR=str(storage))
    subprocess.run(['php', 'scripts/install.php', str(workflow_dir)], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    comfy = ThreadingHTTPServer(('127.0.0.1', 0), Comfy)
    threading.Thread(target=comfy.serve_forever, daemon=True).start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    log = open(storage / 'php.log', 'wb')
    process = subprocess.Popen(['php', '-S', f'127.0.0.1:{port}', 'router.php'], cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        admin = Client(base)
        for _ in range(30):
            try:
                admin.call('session')
                break
            except urllib.error.URLError:
                time.sleep(.1)
        admin.call('admin_state', expected=401)
        admin.call('login', {'identity': 'jhon', 'password': password}, token=False, expected=419)
        admin.call('login', {'identity': 'jhon', 'password': password})
        admin.call('admin_server', {'url': f'http://127.0.0.1:{comfy.server_port}'})
        admin.call('admin_test_server', {})
        model = {'id': 'test-model', 'name': 'Studio Model', 'character_prompt': 'An adult studio model.', 'eye_prompt': 'Brown eyes.', 'active': True, 'loras': [{'name': 'zib/test.safetensors', 'strength': .65}]}
        admin.call('admin_model', model)
        admin.call('admin_workflow', {'mode': 'generate'}, {'workflow': ('bad.json', b'{"nodes":[]}', 'application/json')}, expected=400)
        assert len(admin.call('admin_state')['workflows']) == 2
        for mode, name in [('generate', 'IMG_GEN_API.json'), ('reference', 'IMG_REFERENCE_GEN_API.json')]:
            admin.call('admin_workflow', {'mode': mode}, {'workflow': (name, (workflow_dir / name).read_bytes(), 'application/json')})
        member = Client(base)
        member.call('session')
        result = member.call('register', {'name': 'Member', 'email': 'member@example.test', 'password': password})
        uid = result['user']['id']
        member.call('admin_state', expected=403)
        params = {'mode': 'generate', 'model_id': model['id'], 'prompt': 'A fully clothed editorial portrait.', 'ratio': '4:5', 'batch': 1, 'seed': 23, 'request_key': uuid.uuid4().hex}
        member.call('generate', params, expected=403)
        admin.call('admin_user', {'id': uid, 'active': True, 'can_generate': True})
        member.call('generate', dict(params, batch=3), expected=400)
        member.call('generate', dict(params, model_id='unknown'), expected=400)
        job = member.call('generate', params, expected=202)['job']
        member.call('generate', params)
        assert len(prompts) == 1, 'Duplicate GPU submission'
        result = member.call('job&id=' + job['id'])['job']
        assert result['status'] == 'completed'
        media = result['images'][0]['id']
        assert member.call('media&id=' + media) == PNG
        admin.call('job&id=' + job['id'], expected=404)
        admin.call('media&id=' + media, expected=404)
        anon = Client(base)
        anon.call('media&id=' + media, expected=401)
        refparams = dict(params, mode='reference', request_key=uuid.uuid4().hex, strength=.6)
        member.call('generate', refparams, {'reference': ('bad.png', b'<?php echo 1;', 'image/png')}, expected=400)
        refparams['request_key'] = uuid.uuid4().hex
        refjob = member.call('generate', refparams, {'reference': ('valid.png', PNG, 'image/png')}, expected=202)['job']
        assert member.call('job&id=' + refjob['id'])['job']['status'] == 'completed'
        assert len(prompts) == 2
        for workflow in prompts.values():
            char = next(n for n in workflow.values() if n['_meta']['title'] == 'SELECT_CHARACTER')
            assert char['inputs']['lora_1_name'] == 'zib/test.safetensors'
            assert char['inputs']['lora_2_name'] == 'None'
        for path in ['/backend/bootstrap.php', '/scripts/install.php', '/entrega/publicacion-verificada.json', '/PUBLICACION.md']:
            try:
                urllib.request.urlopen(base + path)
                raise AssertionError('Private path was served: ' + path)
            except urllib.error.HTTPError as err:
                assert err.code == 404
        member.call('logout', {})
        member.call('jobs', expected=401)
        print('PASS: sessions, CSRF, roles, member approval, workflow upload, title mapping, batching, image validation, idempotency, both generations, original downloads, private media isolation, protected source paths and logout.')
    finally:
        process.terminate()
        process.wait(timeout=10)
        comfy.shutdown()
        log.close()
        print('Isolated test data:', storage)

if __name__ == '__main__':
    run()
