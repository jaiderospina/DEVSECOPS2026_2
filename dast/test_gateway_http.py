"""Exercise the real gateway over loopback HTTP with a disposable upstream."""
import http.client
import http.server
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import gateway


class Upstream(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.received.append(dict(self.headers))
        body = json.dumps({'path': self.path}).encode()
        self.send_response(503 if self.path == '/unavailable' else 200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Connection', 'close')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class GatewayHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.request_count = 0
        self.upstream = self.server(Upstream)
        self.upstream.received = []
        self.proxy = self.server(gateway.Handler)
        self.cfg = {'run': 'fixture', 'token': 'fixture-session-only', 'hosts': {
            'identity:8003': {'upstream': '127.0.0.1', 'port': self.upstream.server_port,
                              'patterns': ['/usuarios', '/unavailable']}}}
        self.config_path = self.directory / 'config.json'
        self.log_path = self.directory / 'gateway.jsonl'
        self.config_path.write_text(json.dumps(self.cfg))
        for name, value in [('CONFIG', self.config_path), ('LOG', self.log_path)]:
            patcher = patch.object(gateway, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def server(self, handler):
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def stop():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.addCleanup(stop)
        return server

    def request(self, method, path, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.proxy.server_port, timeout=5)
        try:
            connection.request(method, path, headers={'Host': 'identity:8003', **(headers or {})})
            response = connection.getresponse()
            result = response.status, dict(response.getheaders()), response.read()
            self.request_count += 1
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if self.log_path.exists() and len(self.log_path.read_text().splitlines()) >= self.request_count:
                    return result
                time.sleep(0.005)
            self.fail('Gateway did not record the request')
        finally:
            connection.close()

    def logs(self):
        return [json.loads(line) for line in self.log_path.read_text().splitlines()]

    def test_forwards_get_and_replaces_caller_authentication(self):
        status, headers, body = self.request('GET', '/usuarios?filter=fixture', {
            'Authorization': 'Bearer caller-credential', 'X-HTTP-Method-Override': 'DELETE',
            'X-Method-Override': 'POST', 'X-HTTP-Method': 'PUT', 'X-Test': 'retained'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {'path': '/usuarios?filter=fixture'})
        self.assertEqual(int(headers['Content-Length']), len(body))
        upstream = {k.lower(): v for k, v in self.upstream.received[-1].items()}
        self.assertEqual(upstream['authorization'], 'Bearer fixture-session-only')
        self.assertEqual(upstream['x-test'], 'retained')
        self.assertFalse(any(k.startswith('x-') and 'method' in k for k in upstream))
        entry = self.logs()[-1]
        self.assertTrue(entry['allowed'])
        self.assertEqual(entry['path'], '/usuarios')
        self.assertNotIn('credential', self.log_path.read_text())

    def test_write_methods_and_scope_escapes_never_reach_upstream(self):
        for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD', 'TRACE', 'CONNECT'):
            with self.subTest(method=method):
                self.assertEqual(self.request(method, '/usuarios')[0], 403)
        for path in ('/auth/login', '/usuarios/cargas', '/usuarios/%2e%2e', '/usuarios%00'):
            self.assertEqual(self.request('GET', path)[0], 403)
        self.assertEqual(self.request('GET', '/usuarios', {'Host': 'unrelated:8003'})[0], 403)
        self.assertEqual(self.upstream.received, [])
        self.assertTrue(all(not entry['allowed'] for entry in self.logs()))

    def test_public_scan_does_not_forward_caller_credential(self):
        self.cfg.pop('token')
        self.config_path.write_text(json.dumps(self.cfg))
        self.assertEqual(self.request('GET', '/usuarios', {'Authorization': 'Bearer caller-credential'})[0], 200)
        self.assertNotIn('authorization', {k.lower() for k in self.upstream.received[-1]})

    def test_upstream_errors_are_preserved_and_connection_failures_are_recorded(self):
        self.assertEqual(self.request('GET', '/unavailable')[0], 503)
        self.assertEqual(self.logs()[-1]['status'], 503)
        original = gateway.http.client.HTTPConnection
        failing = Mock()
        failing.request.side_effect = ConnectionError('fixture upstream failure')
        with patch.object(gateway.http.client, 'HTTPConnection', side_effect=lambda host, port, **kw:
                          failing if port == self.upstream.server_port else original(host, port, **kw)):
            self.assertEqual(self.request('GET', '/usuarios')[0], 502)
        failing.close.assert_called_once()
        self.assertEqual(self.logs()[-1]['error'], 'ConnectionError')
        self.assertNotIn('fixture upstream failure', self.log_path.read_text())

    def test_keepalive_closes_connections_on_success_and_failure(self):
        success, failure = Mock(), Mock()
        success.getresponse.return_value.status = 200
        failure.request.side_effect = ConnectionError('fixture')
        cfg = {'keepalive_tokens': ['fixture-one', 'fixture-two'], 'hosts': {
            'identity:8003': {'upstream': '127.0.0.1'}}}
        with patch.object(gateway, 'config', return_value=cfg), \
                patch.object(gateway.http.client, 'HTTPConnection', side_effect=[success, failure]), \
                patch.object(gateway, 'record') as record, \
                patch.object(gateway.time, 'sleep', side_effect=RuntimeError('stop fixture loop')):
            with self.assertRaisesRegex(RuntimeError, 'stop fixture loop'):
                gateway.keepalive()
        success.close.assert_called_once()
        failure.close.assert_called_once()
        record.assert_called_once()
        self.assertEqual(record.call_args.args[0]['status'], 200)
