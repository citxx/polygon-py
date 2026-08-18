import hashlib

import pytest

from polygon_api import FileType, Polygon


API_KEY = 'test-key'
API_SECRET = 'test-secret'
PROBLEM_ID = 42


@pytest.fixture
def polygon(local_api_endpoint):
    return Polygon(local_api_endpoint.api_url, API_KEY, API_SECRET)


def _assert_signed_request(request, method_name, expected_fields):
    assert request.path == '/api/' + method_name
    assert set(request.fields) == set(expected_fields) | {'apiKey', 'time', 'apiSig'}
    for name, expected_value in expected_fields.items():
        assert request.fields[name] == expected_value

    assert request.fields['apiKey'] == API_KEY.encode('utf-8')
    assert request.fields['time'].isdigit()

    signature = request.fields['apiSig']
    assert len(signature) == 6 + 128
    random_prefix = signature[:6]
    signed_fields = {
        name: value for name, value in request.fields.items()
        if name != 'apiSig'
    }
    args_bit = b'&'.join(
        name.encode('utf-8') + b'=' + value
        for name, value in sorted(signed_fields.items())
    )
    signature_input = (
        random_prefix + b'/' + method_name.encode('utf-8') + b'?' + args_bit
        + b'#' + API_SECRET.encode('utf-8')
    )
    expected_signature = random_prefix + hashlib.sha512(signature_input).hexdigest().encode('ascii')
    assert signature == expected_signature


def test_view_file_returns_utf8_text(local_api_endpoint, polygon):
    response_text = 'Привет, Polygon!\n'
    local_api_endpoint.enqueue_response(
        response_text.encode('utf-8'),
        headers={'Content-Type': 'text/plain; charset=utf-8'},
    )

    result = polygon.problem_view_file(PROBLEM_ID, FileType.RESOURCE, 'statement.txt')

    assert result == response_text
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.viewFile', {
        'problemId': b'42',
        'type': b'resource',
        'name': b'statement.txt',
    })


def test_view_file_returns_exact_bytes_in_binary_mode(local_api_endpoint, polygon):
    response_body = b'\x00\xffPNG\r\n'
    local_api_endpoint.enqueue_response(
        response_body,
        headers={'Content-Type': 'application/octet-stream'},
    )

    result = polygon.problem_view_file(
        PROBLEM_ID, FileType.RESOURCE, 'image.bin', binary=True,
    )

    assert result == response_body
    assert isinstance(result, bytes)
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.viewFile', {
        'problemId': b'42',
        'type': b'resource',
        'name': b'image.bin',
    })
