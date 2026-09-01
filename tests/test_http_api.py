import hashlib

import pytest

from polygon_api import (
    CautionCategory,
    CautionSeverity,
    FileType,
    Polygon,
    ProblemAccessType,
    RenderStatus,
)


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


def test_view_statement_resource_returns_utf8_text(local_api_endpoint, polygon):
    response_text = '\\begin{problem}{Сложите два числа}\n'
    local_api_endpoint.enqueue_response(
        response_text.encode('utf-8'),
        headers={'Content-Type': 'text/plain; charset=utf-8'},
    )

    result = polygon.problem_view_statement_resource(PROBLEM_ID, 'olymp.sty')

    assert result == response_text
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.viewStatementResource', {
        'problemId': b'42',
        'name': b'olymp.sty',
    })


def test_view_statement_resource_returns_exact_bytes_in_binary_mode(local_api_endpoint, polygon):
    """
    Statement resources are pictures as often as they are .sty files, and a PNG header cannot be
    decoded as UTF-8, so binary mode has to hand the body back untouched.
    """
    response_body = b'\x89PNG\r\n\x1a\n\x00\xff'
    local_api_endpoint.enqueue_response(
        response_body,
        headers={'Content-Type': 'image/png'},
    )

    result = polygon.problem_view_statement_resource(PROBLEM_ID, 'scheme.png', binary=True)

    assert result == response_body
    assert isinstance(result, bytes)
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.viewStatementResource', {
        'problemId': b'42',
        'name': b'scheme.png',
    })


def test_rendered_statements_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """
    With includeContent the whole render tree arrives base64-encoded inside JSON, so the round
    trip has to survive a PDF that is not valid UTF-8 and a failed render standing next to a
    successful one.
    """
    response_body = (
        '{"status":"OK","result":{'
        '"revision":7,"renderingTimeSeconds":1756600000,'
        '"statements":['
        '{"language":"russian",'
        '"html":{"status":"OK","sha256":"' + 'a' * 64 + '","sizeBytes":41,'
        '"contentBase64":"PHA+0KHQu9C+0LbQuNGC0LUg0LTQstCwINGH0LjRgdC70LAuPC9wPg=="},'
        '"pdf":{"status":"OK","sha256":"' + 'b' * 64 + '","sizeBytes":19,'
        '"contentBase64":"JVBERi0xLjQKAP8lRU9GCg=="}},'
        '{"language":"english",'
        '"html":{"status":"OK","sha256":"' + 'c' * 64 + '","sizeBytes":23,'
        '"contentBase64":"PHA+QWRkIHR3byBudW1iZXJzLjwvcD4="},'
        '"pdf":{"status":"FAILED","message":"Rendering did not finish in 1 minute"}}],'
        '"tutorials":['
        '{"language":"russian",'
        '"html":{"status":"OK","sha256":"' + 'd' * 64 + '","sizeBytes":42},'
        '"pdf":{"status":"OK","sha256":"' + 'e' * 64 + '","sizeBytes":50}}]}}'
    ).encode('utf-8')
    local_api_endpoint.enqueue_response(
        response_body,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    rendered = polygon.problem_render_statements(PROBLEM_ID, include_content=True)

    assert rendered.revision == 7
    assert rendered.rendering_time_seconds == 1756600000

    russian, english = rendered.statements
    assert russian.language == 'russian'
    assert russian.html.status == RenderStatus.OK
    assert russian.html.sha256 == 'a' * 64
    assert russian.html.size_bytes == 41
    assert russian.html.content_bytes == '<p>Сложите два числа.</p>'.encode('utf-8')
    assert russian.pdf.content_bytes == b'%PDF-1.4\n\x00\xff%EOF\n'
    assert russian.pdf.message is None

    assert english.html.content_bytes == b'<p>Add two numbers.</p>'
    assert english.pdf.status == RenderStatus.FAILED
    assert english.pdf.message == 'Rendering did not finish in 1 minute'
    assert english.pdf.sha256 is None
    assert english.pdf.content_bytes is None

    tutorial, = rendered.tutorials
    assert tutorial.language == 'russian'
    assert tutorial.html.size_bytes == 42
    assert tutorial.html.content_bytes is None

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.renderStatements', {
        'problemId': b'42',
        'includeContent': b'true',
    })


def test_accesses_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """
    problem.accesses answers with a JSON array rather than an object, and the entries keep the
    order the API sent them in - the docs sort by login, case-sensitively, so a user group comes
    before the logins.
    """
    response_body = (
        '{"status":"OK","result":['
        '{"login":"@editors","accessType":"WRITE"},'
        '{"login":"alice","accessType":"READ"},'
        '{"login":"owner","accessType":"OWNER"}]}'
    ).encode('utf-8')
    local_api_endpoint.enqueue_response(
        response_body,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    accesses = polygon.problem_accesses(PROBLEM_ID)

    assert [access.login for access in accesses] == ['@editors', 'alice', 'owner']
    assert [access.access_type for access in accesses] == [
        ProblemAccessType.WRITE,
        ProblemAccessType.READ,
        ProblemAccessType.OWNER,
    ]

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.accesses', {'problemId': b'42'})


def test_set_access_accepts_a_success_response_without_a_result(local_api_endpoint, polygon):
    """
    The docs: a successful problem.setAccess response is {"status":"OK"} with no result field at
    all, so the wrapper has to answer None instead of tripping over the missing key.
    """
    local_api_endpoint.enqueue_response(
        b'{"status":"OK"}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    assert polygon.problem_set_access(PROBLEM_ID, 'alice', ProblemAccessType.NONE) is None

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.setAccess', {
        'problemId': b'42',
        'login': b'alice',
        'accessType': b'NONE',
    })
