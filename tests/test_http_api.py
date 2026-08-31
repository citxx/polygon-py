import hashlib

import pytest

from polygon_api import CautionCategory, CautionSeverity, FileType, Polygon


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


def test_save_file_uploads_exact_bytes_and_parses_result(local_api_endpoint, polygon):
    file_content = b'\x00\xffPolygon file\r\n'
    local_api_endpoint.enqueue_response(
        b'{"status":"OK","result":true}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    result = polygon.problem_save_file(
        PROBLEM_ID, FileType.RESOURCE, 'checker.bin', file_content,
    )

    assert result is True
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.saveFile', {
        'problemId': b'42',
        'type': b'resource',
        'name': b'checker.bin',
        'file': file_content,
    })


def test_pin_is_sent_as_a_signed_field(local_api_endpoint, polygon):
    """
    The pin is an ordinary request argument, so it has to be part of apiSig as well: a pin
    appended after signing would be rejected by Polygon.
    """
    local_api_endpoint.enqueue_response(
        b'{"status":"OK","result":true}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    result = polygon.problem_enable_points(PROBLEM_ID, True, pin='1234')

    assert result is True
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.enablePoints', {
        'problemId': b'42',
        'enable': b'true',
        'pin': b'1234',
    })


def test_cautions_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """
    problem.cautions returns the whole caution tree in one response, so the round trip has to
    survive the nested AI tips and non-ASCII statement text as well.
    """
    response_body = (
        '{"status":"OK","result":{'
        '"common":[{"type":"NO_TAGS","severity":"SOFT","category":"COMMON",'
        '"message":"Problem has no tags","parameters":[]}],'
        '"statement":[],'
        '"structure":[{"type":"NO_CHECKER","severity":"HARD","category":"STRUCTURE",'
        '"message":"Checker is not set","parameters":[]}],'
        '"issues":[],'
        '"packageReadinessIssues":[{"type":"INVALID_TEST_SCRIPT","reason":"tests",'
        '"message":"Invalid test script for testset tests"}],'
        '"latestPackageWarnings":["Solution a.cpp is not tested on all tests"],'
        '"ai":{"disabled":false,'
        '"statements":[{"language":"russian","source":"Сложите два числа.",'
        '"suggestion":"Сложите два целых числа.","processing":false}],'
        '"validator":{"name":"validator.cpp","comment":"Не проверена сумма n."}}}}'
    ).encode('utf-8')
    local_api_endpoint.enqueue_response(
        response_body,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    cautions = polygon.problem_cautions(PROBLEM_ID)

    common, = cautions.common
    assert common.type == 'NO_TAGS'
    assert common.severity == CautionSeverity.SOFT
    assert common.category == CautionCategory.COMMON
    structure, = cautions.structure
    assert structure.severity == CautionSeverity.HARD
    issue, = cautions.package_readiness_issues
    assert issue.type == 'INVALID_TEST_SCRIPT'
    assert issue.reason == 'tests'
    assert cautions.latest_package_warnings == ['Solution a.cpp is not tested on all tests']
    assert cautions.ai.disabled is False
    statement_tip, = cautions.ai.statements
    assert statement_tip.language == 'russian'
    assert statement_tip.source == 'Сложите два числа.'
    assert statement_tip.suggestion == 'Сложите два целых числа.'
    assert cautions.ai.validator.comment == 'Не проверена сумма n.'
    assert cautions.ai.checker is None

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.cautions', {'problemId': b'42'})
