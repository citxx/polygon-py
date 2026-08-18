import threading
from collections import namedtuple
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


RecordedRequest = namedtuple('RecordedRequest', ['path', 'fields'])
QueuedResponse = namedtuple('QueuedResponse', ['status', 'headers', 'body'])


class LocalApiEndpoint:
    def __init__(self):
        self.requests = []
        self.responses = []
        self.errors = []
        endpoint = self

        class RequestHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                try:
                    length = int(self.headers['Content-Length'])
                    body = self.rfile.read(length)
                    fields = endpoint._parse_multipart(self.headers['Content-Type'], body)
                    endpoint.requests.append(RecordedRequest(self.path, fields))
                    if not endpoint.responses:
                        raise AssertionError('Received a request without a queued response')
                    response = endpoint.responses.pop(0)
                except Exception as exc:
                    endpoint.errors.append(exc)
                    response = QueuedResponse(500, {'Content-Type': 'text/plain'}, str(exc).encode('utf-8'))

                self.send_response(response.status)
                for name, value in response.headers.items():
                    self.send_header(name, value)
                self.send_header('Content-Length', str(len(response.body)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(response.body)
                self.close_connection = True

            def log_message(self, format, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), RequestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def api_url(self):
        host, port = self.server.server_address
        return 'http://{}:{}/api'.format(host, port)

    def enqueue_response(self, body, status=200, headers=None):
        self.responses.append(QueuedResponse(status, headers or {}, body))

    @staticmethod
    def _parse_multipart(content_type, body):
        message = BytesParser(policy=default).parsebytes(
            b'Content-Type: ' + content_type.encode('ascii')
            + b'\r\nMIME-Version: 1.0\r\n\r\n' + body
        )
        if not message.is_multipart():
            raise AssertionError('Expected a multipart request')

        fields = {}
        for part in message.iter_parts():
            name = part.get_param('name', header='content-disposition')
            if name in fields:
                raise AssertionError('Duplicate multipart field: {}'.format(name))
            fields[name] = part.get_payload(decode=True)
        return fields

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise AssertionError('Local API server thread did not stop')


@pytest.fixture
def local_api_endpoint():
    endpoint = LocalApiEndpoint()
    try:
        yield endpoint
    finally:
        endpoint.close()
        assert not endpoint.errors
        assert not endpoint.responses, 'Not all queued responses were consumed'
