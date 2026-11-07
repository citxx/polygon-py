import hashlib
import json

import pytest

from polygon_api import (
    CautionCategory,
    CautionSeverity,
    DeleteTestsFailedException,
    FileType,
    InvocationRunVerdict,
    InvocationStatus,
    IssueStatus,
    IssueType,
    MaterialItem,
    MaterialItemType,
    MaterialPublishStrategy,
    MaterialTest,
    Polygon,
    PolygonRequestFailedException,
    ProblemAccessType,
    RenderStatus,
    SolutionTag,
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


def test_clear_script_sends_the_testset_and_parses_the_result(local_api_endpoint, polygon):
    local_api_endpoint.enqueue_response(
        b'{"status":"OK","result":true}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    result = polygon.problem_clear_script(PROBLEM_ID, 'tests')

    assert result is True
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.clearScript', {
        'problemId': b'42',
        'testset': b'tests',
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


def test_an_empty_note_survives_the_multipart_encoding(local_api_endpoint, polygon):
    """
    An empty note is how problem.saveNote clears the note. The unit tests only see the arguments
    before they are encoded, so an empty field dropped by the multipart encoder, or left out of
    apiSig, would go unnoticed there and clear nothing.
    """
    local_api_endpoint.enqueue_response(
        b'{"status":"OK","result":null}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    polygon.problem_save_note(PROBLEM_ID, '')

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.saveNote', {
        'problemId': b'42',
        'note': b'',
    })


def test_a_note_round_trips_as_utf8_text(local_api_endpoint, polygon):
    """The note is free-form user text, so it has to survive non-ASCII in both directions."""
    local_api_endpoint.enqueue_response(
        '{"status":"OK","result":"не публиковать"}'.encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    assert polygon.problem_view_note(PROBLEM_ID) == 'не публиковать'

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.note', {'problemId': b'42'})


def test_commit_result_is_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """
    The docs: with no changes problem.commitChanges still answers OK, and the result is the
    only place that says nothing was committed.
    """
    local_api_endpoint.enqueue_response(
        b'{"status":"OK","result":{"committed":false,"conflictOccurred":false,"message":"No changes"}}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    result = polygon.problem_commit_changes(PROBLEM_ID, minor_changes=True, message='Fix the checker')

    assert result.committed is False
    assert result.conflict_occurred is False
    assert result.message == 'No changes'

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.commitChanges', {
        'problemId': b'42',
        'minorChanges': b'true',
        'message': b'Fix the checker',
    })


def test_delete_file_sends_the_type_in_lower_case(local_api_endpoint, polygon):
    local_api_endpoint.enqueue_response(
        b'{"status":"OK"}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    polygon.problem_delete_file(PROBLEM_ID, FileType.SOURCE, 'gen.cpp')

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.deleteFile', {
        'problemId': b'42',
        'type': b'source',
        'name': b'gen.cpp',
    })


def test_delete_solution_raises_on_the_http_400_for_a_missing_solution(local_api_endpoint, polygon):
    """
    The docs: problem.deleteSolution returns FAILED if there is no such solution. Polygon sends
    that with HTTP 400, which the wrapper has to read as a FAILED status rather than an HTTP error.
    """
    local_api_endpoint.enqueue_response(
        b'{"status":"FAILED","comment":"Solution not found"}',
        status=400,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    with pytest.raises(PolygonRequestFailedException) as excinfo:
        polygon.problem_delete_solution(PROBLEM_ID, 'wa.cpp')
    assert excinfo.value.comment == 'Solution not found'

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.deleteSolution', {
        'problemId': b'42',
        'name': b'wa.cpp',
    })


def test_delete_statement_sends_the_language(local_api_endpoint, polygon):
    local_api_endpoint.enqueue_response(
        b'{"status":"OK"}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    polygon.problem_delete_statement(PROBLEM_ID, 'russian')

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.deleteStatement', {
        'problemId': b'42',
        'lang': b'russian',
    })


def test_delete_statement_resource_sends_the_name(local_api_endpoint, polygon):
    local_api_endpoint.enqueue_response(
        b'{"status":"OK"}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    polygon.problem_delete_statement_resource(PROBLEM_ID, 'picture.png')

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.deleteStatementResource', {
        'problemId': b'42',
        'name': b'picture.png',
    })


def test_delete_validator_test_sends_the_index(local_api_endpoint, polygon):
    local_api_endpoint.enqueue_response(
        b'{"status":"OK"}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    polygon.problem_delete_validator_test(PROBLEM_ID, 3)

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.deleteValidatorTest', {
        'problemId': b'42',
        'testIndex': b'3',
    })


def test_delete_checker_test_sends_the_index(local_api_endpoint, polygon):
    local_api_endpoint.enqueue_response(
        b'{"status":"OK"}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    polygon.problem_delete_checker_test(PROBLEM_ID, 3)

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.deleteCheckerTest', {
        'problemId': b'42',
        'testIndex': b'3',
    })


def test_delete_test_failures_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """
    The docs: when a requested test can not be deleted, problem.deleteTest answers FAILED and still
    sends a result, a DeleteTestsResult with one failure per such test, and deletes nothing.
    """
    local_api_endpoint.enqueue_response(
        b'{"status":"FAILED","comment":"Some tests can not be deleted.","result":{"failures":['
        b'{"index":2,"reason":"DUPLICATE","message":"Test 2 is requested twice"},'
        b'{"index":9,"reason":"NOT_FOUND","message":"Test 9 not found"}]}}',
        status=400,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    with pytest.raises(DeleteTestsFailedException) as excinfo:
        polygon.problem_delete_test(PROBLEM_ID, 'tests', test_indices=[2, 2, 9])

    assert excinfo.value.comment == 'Some tests can not be deleted.'
    assert [(failure.index, str(failure.reason)) for failure in excinfo.value.result.failures] == [
        (2, 'DUPLICATE'),
        (9, 'NOT_FOUND'),
    ]

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.deleteTest', {
        'problemId': b'42',
        'testset': b'tests',
        'testIndices': b'2,2,9',
    })


def test_issues_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """The example response of problem.issues in the docs."""
    response_body = (
        '{"status":"OK","result":[{"id":1234,"type":"BUG","status":"CLOSED","author":"alice",'
        '"assignee":"bob","html":"<div class=\'markup\'><p>Test 5 is invalid</p>\\n</div>",'
        '"creationTimeSeconds":1790000000,"modificationTimeSeconds":1790003600,"comments":['
        '{"author":"bob","html":"<div class=\'markup\'><p>Fixed in revision 12</p>\\n</div>",'
        '"creationTimeSeconds":1790003600,"status":"CLOSED"}]}]}'
    ).encode('utf-8')
    local_api_endpoint.enqueue_response(
        response_body,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    issue, = polygon.problem_issues(PROBLEM_ID)

    assert issue.id == 1234
    assert issue.type == IssueType.BUG
    assert issue.status == IssueStatus.CLOSED
    assert issue.assignee == 'bob'
    assert issue.html == "<div class='markup'><p>Test 5 is invalid</p>\n</div>"
    comment, = issue.comments
    assert comment.author == 'bob'
    assert comment.status == IssueStatus.CLOSED
    assert comment.type is None
    assert comment.assignee is None

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.issues', {'problemId': b'42'})


def test_add_issue_sends_markdown_content_as_utf8(local_api_endpoint, polygon):
    """The issue content is free-form Markdown, so it has to survive non-ASCII on the wire."""
    local_api_endpoint.enqueue_response(
        ('{"status":"OK","result":{"id":1235,"type":"DISCUSSION","status":"OPENED","author":"alice",'
         '"html":"<p>Ограничение на <em>n</em>?</p>","creationTimeSeconds":1790000000,'
         '"modificationTimeSeconds":1790000000,"comments":[]}}').encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    issue = polygon.problem_add_issue(PROBLEM_ID, IssueType.DISCUSSION, 'Ограничение на *n*?')

    assert issue.html == '<p>Ограничение на <em>n</em>?</p>'
    assert issue.status == IssueStatus.OPENED
    assert issue.assignee is None
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.addIssue', {
        'problemId': b'42',
        'type': b'DISCUSSION',
        'content': 'Ограничение на *n*?'.encode('utf-8'),
    })


def test_an_empty_assignee_survives_the_multipart_encoding(local_api_endpoint, polygon):
    """
    An empty assignee is how problem.updateIssue unassigns an issue. The unit tests only see the
    arguments before they are encoded, so an empty field dropped by the multipart encoder, or left
    out of apiSig, would go unnoticed there and leave the assignee in place.
    """
    local_api_endpoint.enqueue_response(
        b'{"status":"OK","result":{"id":1234,"type":"BUG","status":"OPENED","author":"alice",'
        b'"html":"<p>Test 5 is invalid</p>","creationTimeSeconds":1790000000,'
        b'"modificationTimeSeconds":1790003600,"comments":[{"author":"bob","html":"",'
        b'"creationTimeSeconds":1790003600}]}}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    issue = polygon.problem_update_issue(PROBLEM_ID, 1234, assignee='')

    assert issue.assignee is None
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.updateIssue', {
        'problemId': b'42',
        'issueId': b'1234',
        'assignee': b'',
    })


def test_enable_treat_points_from_checker_as_percent_sends_the_flag(local_api_endpoint, polygon):
    local_api_endpoint.enqueue_response(
        b'{"status":"OK","result":null}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    result = polygon.problem_enable_treat_points_from_checker_as_percent(PROBLEM_ID, False)

    assert result is None
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.enableTreatPointsFromCheckerAsPercent', {
        'problemId': b'42',
        'enable': b'false',
    })


def test_enable_treat_points_from_checker_as_percent_raises_on_the_http_400(local_api_endpoint, polygon):
    """The docs: enabling it while test points are disabled for the problem returns FAILED."""
    local_api_endpoint.enqueue_response(
        b'{"status":"FAILED","comment":"Test points are disabled"}',
        status=400,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    with pytest.raises(PolygonRequestFailedException) as excinfo:
        polygon.problem_enable_treat_points_from_checker_as_percent(PROBLEM_ID, True)

    assert excinfo.value.comment == 'Test points are disabled'
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.enableTreatPointsFromCheckerAsPercent', {
        'problemId': b'42',
        'enable': b'true',
    })


def test_test_previews_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """
    A generated preview with non-ASCII input next to one still being generated, which comes back
    without input and answer.
    """
    local_api_endpoint.enqueue_response(
        ('{"status":"OK","result":['
         '{"id":77,"session":"f3a9c1","creationTime":"Nov 4, 2026 1:19:03 PM",'
         '"updateTime":"Nov 4, 2026 1:19:05 PM","problemId":42,"testset":"tests","testIndex":1,'
         '"useInStatements":true,"input":"абв\\n","inputSha1":"%s","answer":"3\\n",'
         '"changeAfterLastGenerate":false},'
         '{"session":"f3a9c1","problemId":42,"testset":"tests","testIndex":2,'
         '"useInStatements":false,"changeAfterLastGenerate":true}]}' % ('a' * 40)).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    generated, pending = polygon.problem_preview_tests(PROBLEM_ID, 'tests')

    assert generated.input == 'абв\n'
    assert generated.answer == '3\n'
    assert generated.creation_time == 'Nov 4, 2026 1:19:03 PM'
    assert generated.use_in_statements is True
    assert pending.test_index == 2
    assert pending.input is None
    assert pending.answer is None
    assert pending.change_after_last_generate is True
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.previewTests', {
        'problemId': b'42',
        'testset': b'tests',
    })


def test_materials_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    local_api_endpoint.enqueue_response(
        ('{"status":"OK","result":[{"name":"разбор","publishStrategy":"WITH_TUTORIAL","items":['
         '{"type":"TEST_INPUTS","tests":[{"testset":"tests","index":1,"all":false,"asInput":false}]},'
         '{"type":"TEST_ANSWERS","tests":[{"testset":"tests","all":false,"asInput":true}]},'
         '{"type":"SOURCE_FILES","names":["gen.cpp"]}]}]}').encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    material, = polygon.problem_materials(PROBLEM_ID)

    assert material.name == 'разбор'
    assert material.publish_strategy == MaterialPublishStrategy.WITH_TUTORIAL
    inputs, answers, sources = material.items
    assert inputs.tests[0].index == 1
    assert answers.tests[0].as_input is True
    assert sources.type == MaterialItemType.SOURCE_FILES
    assert sources.names == ['gen.cpp']
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.materials', {'problemId': b'42'})


def test_set_material_sends_the_items_and_accepts_a_response_without_a_result(local_api_endpoint, polygon):
    """
    The docs: a successful problem.setMaterial answers {"status":"OK"} with no result field. The
    items go in the request body as JSON, which non-ASCII names have to survive.
    """
    local_api_endpoint.enqueue_response(
        b'{"status":"OK"}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    result = polygon.problem_set_material(PROBLEM_ID, 'разбор', MaterialPublishStrategy.WITH_TUTORIAL, [
        MaterialItem(MaterialItemType.TEST_INPUTS, tests=[MaterialTest('tests', all=True)]),
        MaterialItem(MaterialItemType.RESOURCE_FILES, names=['картинка.png']),
    ])

    assert result is None
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.setMaterial', {
        'problemId': b'42',
        'name': 'разбор'.encode('utf-8'),
        'publishStrategy': b'WITH_TUTORIAL',
        'items': (b'[{"type":"TEST_INPUTS","tests":[{"testset":"tests","all":true}]},'
                  b'{"type":"RESOURCE_FILES","names":["\\u043a\\u0430\\u0440\\u0442\\u0438\\u043d'
                  b'\\u043a\\u0430.png"]}]'),
    })
    assert json.loads(request.fields['items'])[1]['names'] == ['картинка.png']


def test_remove_material_sends_the_lowercase_flag(local_api_endpoint, polygon):
    """The docs: only the lowercase values true and false are accepted for remove."""
    local_api_endpoint.enqueue_response(
        b'{"status":"OK"}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    polygon.problem_set_material(PROBLEM_ID, 'statements', remove=True)

    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.setMaterial', {
        'problemId': b'42',
        'name': b'statements',
        'remove': b'true',
    })


def test_invocations_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """The verification of a package, one invocation per verified testset."""
    local_api_endpoint.enqueue_response(
        b'{"status":"OK","result":['
        b'{"id":502,"description":"Package #12 verification","testset":"tests","status":"RUNNING",'
        b'"creationTimeSeconds":1790000100,"packageId":12,"violateTag":false,'
        b'"solutions":["main.cpp","wa.cpp"],"tests":[1,2,3]},'
        b'{"id":501,"description":"Package #12 verification","testset":"samples","status":"FINISHED",'
        b'"creationTimeSeconds":1790000000,"packageId":12,"violateTag":false,'
        b'"solutions":["main.cpp","wa.cpp"],"tests":[1]}]}',
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    running, finished = polygon.problem_invocations(PROBLEM_ID, package_id=12)

    assert (running.id, running.status, running.testset) == (502, InvocationStatus.RUNNING, 'tests')
    assert (finished.id, finished.status, finished.testset) == (501, InvocationStatus.FINISHED, 'samples')
    assert running.tests == [1, 2, 3]
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.invocations', {
        'problemId': b'42',
        'packageId': b'12',
    })


def test_invocation_results_are_parsed_from_a_full_api_response(local_api_endpoint, polygon):
    """
    A finished invocation in which a solution tagged TL gets WA, which violates its tag, and a run
    without a solution name, whose solution source is no longer stored.
    """
    local_api_endpoint.enqueue_response(
        ('{"status":"OK","result":{'
         '"invocation":{"id":501,"description":"проверка","testset":"tests","status":"FINISHED",'
         '"creationTimeSeconds":1790000000,"violateTag":true,"solutions":["main.cpp","tl.cpp"],"tests":[1]},'
         '"solutionTags":[{"name":"main.cpp","tag":"MA"},'
         '{"name":"tl.cpp","tag":"TL","groupTags":{"subtask1":"OK"}}],'
         '"runs":[{"id":1,"solution":"main.cpp","test":1,"verdict":"OK","timeMillis":31,'
         '"memoryBytes":4194304,"comment":"ok 1 number","violateTag":false},'
         '{"id":2,"solution":"tl.cpp","test":1,"verdict":"WA","timeMillis":980,"memoryBytes":4194304,'
         '"points":1.5,"violateTag":true},'
         '{"id":3,"test":1,"verdict":"RJ","violateTag":false}]}}').encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    results = polygon.problem_invocation(PROBLEM_ID, 501)

    assert results.invocation.description == 'проверка'
    assert results.invocation.package_id is None
    main_tags, tl_tags = results.solution_tags
    assert main_tags.tag == SolutionTag.MA
    assert tl_tags.group_tags == {'subtask1': SolutionTag.OK}
    assert tl_tags.testset_tags == {}
    main_run, tl_run, lost_run = results.runs
    assert (main_run.verdict, main_run.time_millis, main_run.points) == (InvocationRunVerdict.OK, 31, None)
    assert (tl_run.verdict, tl_run.violate_tag, tl_run.points) == (InvocationRunVerdict.WA, True, 1.5)
    assert (lost_run.solution, lost_run.verdict, lost_run.time_millis) == (None, InvocationRunVerdict.RJ, None)
    request, = local_api_endpoint.requests
    _assert_signed_request(request, 'problem.invocation', {
        'problemId': b'42',
        'invocationId': b'501',
    })
