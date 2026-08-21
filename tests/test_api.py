"""
Tests for the parts of the wrapper that need no network access: argument
formatting, local argument validation, JSON parsing and the text/bytes split of
response bodies (with requests.post replaced by a stub).
"""

import functools
import inspect
from types import SimpleNamespace

import pytest

from polygon_api import (
    CheckerTest,
    CheckerTestVerdict,
    Package,
    PackageState,
    PackageType,
    Polygon,
    Problem,
    ProblemInfo,
    ValidatorTest,
    ValidatorTestRunVerdict,
    ValidatorTestVerdict,
)
from polygon_api import api
from polygon_api.api import Request, RequestConfig, Response, _comma_separated


@pytest.fixture
def polygon():
    return Polygon('https://example.invalid/api', 'key', 'secret')


@pytest.fixture
def config():
    return RequestConfig('https://example.invalid/api', 'key', 'secret')


class TestCommaSeparated:
    def test_none_is_passed_through(self):
        assert _comma_separated(None) is None

    def test_list_is_joined(self):
        assert _comma_separated([1, 2, 3]) == '1,2,3'

    def test_tuple_is_joined(self):
        assert _comma_separated((1, 2, 3)) == '1,2,3'

    def test_set_is_joined(self):
        assert set(_comma_separated({1, 2, 3}).split(',')) == {'1', '2', '3'}

    def test_range_is_joined(self):
        assert _comma_separated(range(1, 4)) == '1,2,3'

    def test_generator_is_joined(self):
        assert _comma_separated(i for i in [1, 2, 3]) == '1,2,3'

    def test_string_is_not_split_into_characters(self):
        assert _comma_separated('1,2,3') == '1,2,3'

    def test_single_index_string_is_passed_through(self):
        assert _comma_separated('5') == '5'

    def test_scalar_is_stringified(self):
        assert _comma_separated(5) == '5'

    def test_empty_list_becomes_empty_string(self):
        assert _comma_separated([]) == ''


class TestSetTestGroupValidation:
    def test_requires_test_index_or_test_indices(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_set_test_group(1, 'tests', 'group')

    def test_rejects_both_test_index_and_test_indices(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_set_test_group(1, 'tests', 'group', test_index=1, test_indices=[1, 2])


class TestVerdictValidation:
    def test_checker_test_rejects_wrong_enum(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_save_checker_test(1, 1, test_verdict=ValidatorTestVerdict.VALID)

    def test_checker_test_rejects_bare_string(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_save_checker_test(1, 1, test_verdict='OK')

    def test_validator_test_rejects_wrong_enum(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_save_validator_test(1, 1, test_verdict=CheckerTestVerdict.OK)

    def test_validator_test_rejects_bare_string(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_save_validator_test(1, 1, test_verdict='VALID')


class TestRequestArguments:
    def test_none_arguments_are_dropped(self, config):
        request = Request(config, 'problem.info', args={'problemId': 1, 'testset': None})
        assert request.args == [('problemId', 1)]

    def test_booleans_become_lowercase_literals(self, config):
        request = Request(config, 'problem.info', args={'yes': True, 'no': False})
        assert dict(request.args) == {'yes': 'true', 'no': 'false'}

    def test_list_argument_is_repeated_per_item(self, config):
        request = Request(config, 'problem.info', args={'tag': ['a', 'b']})
        assert request.args == [('tag', 'a'), ('tag', 'b')]

    def test_missing_args_is_treated_as_empty(self, config):
        assert Request(config, 'problem.info').args == []

    def test_api_url_gets_trailing_slash(self):
        assert RequestConfig('https://example.invalid/api', 'k', 's').api_url == 'https://example.invalid/api/'

    def test_existing_trailing_slash_is_kept(self):
        assert RequestConfig('https://example.invalid/api/', 'k', 's').api_url == 'https://example.invalid/api/'


class TestValueEncoding:
    def test_str_is_utf8_encoded(self):
        assert Request._value_to_utf8_bytes('тест') == 'тест'.encode('utf-8')

    def test_bytes_are_passed_through(self):
        assert Request._value_to_utf8_bytes(b'raw') == b'raw'

    def test_bytearray_becomes_bytes(self):
        value = Request._value_to_utf8_bytes(bytearray(b'raw'))
        assert value == b'raw'
        assert isinstance(value, bytes)

    def test_int_is_stringified(self):
        assert Request._value_to_utf8_bytes(5) == b'5'


class TestApiSignature:
    def test_has_random_prefix_and_sha512_digest(self, config):
        request = Request(config, 'problem.info', args={'problemId': 1})
        args = Request._encoded_args(request.args)
        signature = request.get_api_signature(args, b'secret')
        # 6 random characters followed by a sha512 hexdigest
        assert len(signature) == 6 + 128

    def test_differs_between_calls(self, config):
        request = Request(config, 'problem.info', args={'problemId': 1})
        args = Request._encoded_args(request.args)
        first = request.get_api_signature(args, b'secret')
        second = request.get_api_signature(args, b'secret')
        assert first != second


class TestResponse:
    def test_ok_status_is_kept(self):
        assert Response({'status': 'OK', 'result': 42}).status == Response.STATUS_OK

    def test_failed_status_is_kept(self):
        response = Response({'status': 'FAILED', 'comment': 'boom'})
        assert response.status == Response.STATUS_FAILED
        assert response.comment == 'boom'

    def test_unexpected_status_becomes_unknown(self):
        assert Response({'status': 'WEIRD'}).status == Response.STATUS_UNKNOWN

    def test_missing_status_becomes_unknown(self):
        assert Response({}).status == Response.STATUS_UNKNOWN

    def test_comment_defaults_to_empty_string(self):
        assert Response({'status': 'OK'}).comment == ''

    def test_result_is_extracted(self):
        assert Response({'status': 'OK', 'result': [1, 2]}).result == [1, 2]


class TestPackageParsing:
    """
    The API returns package state in upper case but package type in lower case,
    see https://codeforces.github.io/polygon-misc/API.
    """

    def test_from_json(self):
        package = Package.from_json({
            'id': 7,
            'revision': 3,
            'creationTimeSeconds': 1600000000,
            'state': 'READY',
            'comment': 'built',
            'type': 'standard',
        })
        assert package.id == 7
        assert package.revision == 3
        assert package.creation_time_seconds == 1600000000
        assert package.state == PackageState.READY
        assert package.comment == 'built'
        assert package.type == PackageType.STANDARD

    @pytest.mark.parametrize('state', ['PENDING', 'RUNNING', 'READY', 'FAILED'])
    def test_every_documented_state_parses(self, state):
        package = Package.from_json({
            'id': 1, 'revision': 1, 'creationTimeSeconds': 0,
            'state': state, 'comment': '', 'type': 'linux',
        })
        assert package.state == PackageState[state]

    @pytest.mark.parametrize('type_name', ['standard', 'linux', 'windows'])
    def test_every_documented_type_parses(self, type_name):
        package = Package.from_json({
            'id': 1, 'revision': 1, 'creationTimeSeconds': 0,
            'state': 'READY', 'comment': '', 'type': type_name,
        })
        assert package.type == PackageType[type_name.upper()]

    def test_state_is_serialized_in_upper_case(self):
        assert str(PackageState.READY) == 'READY'

    def test_type_is_serialized_in_lower_case(self):
        assert str(PackageType.STANDARD) == 'standard'


class TestProblemInfoParsing:
    """
    problem.info returns wellFormed and skipDuplicatedTestsValidation next to the limits. Both
    are read leniently: a problem for which Polygon omits a flag must still yield a ProblemInfo
    instead of failing the whole call.
    """

    def test_from_json_with_all_fields(self):
        info = ProblemInfo.from_json({
            'inputFile': 'input.txt',
            'outputFile': 'output.txt',
            'interactive': False,
            'wellFormed': True,
            'skipDuplicatedTestsValidation': False,
            'timeLimit': 2000,
            'memoryLimit': 256,
        })
        assert info.input_file == 'input.txt'
        assert info.output_file == 'output.txt'
        assert info.interactive is False
        assert info.well_formed is True
        assert info.skip_duplicated_tests_validation is False
        assert info.time_limit == 2000
        assert info.memory_limit == 256

    def test_flags_default_to_none_when_absent(self):
        info = ProblemInfo.from_json({
            'inputFile': 'stdin',
            'outputFile': 'stdout',
            'interactive': True,
            'timeLimit': 1000,
            'memoryLimit': 64,
        })
        assert info.well_formed is None
        assert info.skip_duplicated_tests_validation is None


class TestValidatorTestParsing:
    def test_from_json_with_all_fields(self):
        test = ValidatorTest.from_json({
            'index': 2,
            'input': '1 2',
            'expectedVerdict': 'VALID',
            'testset': 'tests',
            'group': 'first',
        })
        assert test.index == 2
        assert test.input == '1 2'
        assert test.expected_verdict == ValidatorTestVerdict.VALID
        assert test.testset == 'tests'
        assert test.group == 'first'

    def test_optional_fields_default_to_none(self):
        test = ValidatorTest.from_json({'index': 1, 'input': 'x', 'expectedVerdict': 'INVALID'})
        assert test.expected_verdict == ValidatorTestVerdict.INVALID
        assert test.testset is None
        assert test.group is None

    def test_run_verdict_and_run_comment_are_parsed(self):
        comment = 'FAIL Integer parameter [name=n] equals to 1000000000, violates the range [1, 1000000]'
        test = ValidatorTest.from_json({
            'index': 2,
            'input': '1000000000',
            'expectedVerdict': 'VALID',
            'runVerdict': 'INVALID',
            'runComment': comment,
        })
        assert test.run_verdict == ValidatorTestRunVerdict.INVALID
        assert test.run_comment == comment

    def test_run_fields_default_to_none_when_absent(self):
        test = ValidatorTest.from_json({'index': 1, 'input': 'x', 'expectedVerdict': 'VALID'})
        assert test.run_verdict is None
        assert test.run_comment is None

    @pytest.mark.parametrize('run_verdict', ['VALID', 'INVALID', 'IN_QUEUE', 'CANT_RUN'])
    def test_every_documented_run_verdict_parses(self, run_verdict):
        """
        IN_QUEUE and CANT_RUN are the reason runVerdict cannot reuse ValidatorTestVerdict:
        a test that has not been run yet is the ordinary case, not an edge case.
        """
        test = ValidatorTest.from_json({
            'index': 1, 'input': 'x', 'expectedVerdict': 'VALID', 'runVerdict': run_verdict,
        })
        assert test.run_verdict == ValidatorTestRunVerdict[run_verdict]

    def test_run_verdict_is_not_the_expected_verdict_enum(self):
        test = ValidatorTest.from_json({
            'index': 1, 'input': 'x', 'expectedVerdict': 'VALID', 'runVerdict': 'VALID',
        })
        assert test.run_verdict is ValidatorTestRunVerdict.VALID
        assert test.run_verdict != ValidatorTestVerdict.VALID

    def test_expected_verdict_is_parsed_independently_of_run_verdict(self):
        test = ValidatorTest.from_json({
            'index': 1, 'input': 'x', 'expectedVerdict': 'INVALID', 'runVerdict': 'VALID',
        })
        assert test.expected_verdict == ValidatorTestVerdict.INVALID
        assert test.run_verdict == ValidatorTestRunVerdict.VALID

    def test_run_comment_is_kept_without_a_run_verdict(self):
        test = ValidatorTest.from_json({
            'index': 1, 'input': 'x', 'expectedVerdict': 'VALID', 'runComment': 'ok',
        })
        assert test.run_verdict is None
        assert test.run_comment == 'ok'

    @pytest.mark.parametrize('run_verdict', ['VALID', 'INVALID', 'IN_QUEUE', 'CANT_RUN'])
    def test_run_verdict_is_serialized_by_name(self, run_verdict):
        assert str(ValidatorTestRunVerdict[run_verdict]) == run_verdict

    def test_run_verdict_values_cover_the_expected_verdict_values(self):
        assert set(ValidatorTestVerdict.__members__) <= set(ValidatorTestRunVerdict.__members__)

    def test_positional_construction_stays_backwards_compatible(self):
        test = ValidatorTest(2, '1 2', ValidatorTestVerdict.VALID, 'tests', 'first')
        assert test.index == 2
        assert test.input == '1 2'
        assert test.expected_verdict == ValidatorTestVerdict.VALID
        assert test.testset == 'tests'
        assert test.group == 'first'
        assert test.run_verdict is None
        assert test.run_comment is None


class TestCheckerTestParsing:
    def test_from_json(self):
        test = CheckerTest.from_json({
            'index': 1,
            'input': '1 2',
            'output': '3',
            'answer': '4',
            'expectedVerdict': 'WRONG_ANSWER',
        })
        assert test.index == 1
        assert test.input == '1 2'
        assert test.output == '3'
        assert test.answer == '4'
        assert test.expected_verdict == CheckerTestVerdict.WRONG_ANSWER

    @pytest.mark.parametrize('verdict', ['OK', 'WRONG_ANSWER', 'CRASHED', 'PRESENTATION_ERROR'])
    def test_every_documented_verdict_parses(self, verdict):
        test = CheckerTest.from_json({
            'index': 1, 'input': '', 'output': '', 'answer': '', 'expectedVerdict': verdict,
        })
        assert test.expected_verdict == CheckerTestVerdict[verdict]

    def test_run_verdict_and_run_comment_are_parsed(self):
        test = CheckerTest.from_json({
            'index': 1,
            'input': '1 2',
            'output': '3',
            'answer': '4',
            'expectedVerdict': 'WRONG_ANSWER',
            'runVerdict': 'WRONG_ANSWER',
            'runComment': 'wrong answer expected 4, found 3',
        })
        assert test.run_verdict == 'WRONG_ANSWER'
        assert test.run_comment == 'wrong answer expected 4, found 3'

    def test_run_fields_default_to_none_when_absent(self):
        test = CheckerTest.from_json({
            'index': 1, 'input': '', 'output': '', 'answer': '', 'expectedVerdict': 'OK',
        })
        assert test.run_verdict is None
        assert test.run_comment is None

    def test_run_verdict_stays_a_plain_string(self):
        test = CheckerTest.from_json({
            'index': 1, 'input': '', 'output': '', 'answer': '', 'expectedVerdict': 'OK',
            'runVerdict': 'OK',
        })
        assert isinstance(test.run_verdict, str)
        assert test.run_verdict != CheckerTestVerdict.OK

    @pytest.mark.parametrize('run_verdict', ['PARTIALLY_CORRECT', 'IN_QUEUE', 'CANT_RUN', 'UNEXPECTED_EOF'])
    def test_run_verdict_outside_the_expected_verdict_set_parses(self, run_verdict):
        """
        A completed run returns the raw checker interop verdict name, which custom checkers
        extend, so runVerdict must survive values CheckerTestVerdict does not know about.
        """
        assert run_verdict not in CheckerTestVerdict.__members__
        test = CheckerTest.from_json({
            'index': 1, 'input': '', 'output': '', 'answer': '', 'expectedVerdict': 'OK',
            'runVerdict': run_verdict,
        })
        assert test.run_verdict == run_verdict

    def test_expected_verdict_stays_an_enum_beside_a_string_run_verdict(self):
        test = CheckerTest.from_json({
            'index': 1, 'input': '', 'output': '', 'answer': '', 'expectedVerdict': 'CRASHED',
            'runVerdict': 'OK',
        })
        assert test.expected_verdict == CheckerTestVerdict.CRASHED
        assert test.run_verdict == 'OK'

    def test_positional_construction_stays_backwards_compatible(self):
        test = CheckerTest(1, '1 2', '3', '4', CheckerTestVerdict.OK)
        assert test.index == 1
        assert test.input == '1 2'
        assert test.output == '3'
        assert test.answer == '4'
        assert test.expected_verdict == CheckerTestVerdict.OK
        assert test.run_verdict is None
        assert test.run_comment is None


# Response bodies: the text/bytes split and the binary parameter.
#
# RAW_BODY is deliberately not valid UTF-8 and differs from TEXT_BODY. A regression that decodes
# the bytes by hand instead of returning response.text (or encodes the text instead of returning
# response.content) then fails loudly instead of quietly returning a wrong-but-decodable body.
TEXT_BODY = 'plain text body\n'
RAW_BODY = b'PK\x03\x04\xff\xfe'

OK_JSON_BODY = '{"status": "OK", "result": null}'


class _FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, text=TEXT_BODY, content=RAW_BODY, status_code=200):
        self.text = text
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        raise AssertionError('raise_for_status() must not be called for HTTP {}'.format(self.status_code))


def _install_fake_post(monkeypatch, text=TEXT_BODY, content=RAW_BODY):
    """Replaces requests.post with a stub and returns the list of recorded calls."""
    calls = []

    def post(url, files=None, **kwargs):
        calls.append({'url': url, 'files': files})
        return _FakeResponse(text, content)

    monkeypatch.setattr(api.requests, 'post', post)
    return calls


@pytest.fixture
def post_calls(monkeypatch):
    return _install_fake_post(monkeypatch)


@pytest.fixture
def problem(polygon):
    return Problem.from_json(polygon, {'id': 1})


# Owner fixture, method name, leading positional arguments, expected Polygon API method.
BINARY_ENDPOINTS = [
    ('polygon', 'problem_view_file', (1, 'source', 'a.cpp'), 'problem.viewFile'),
    ('polygon', 'problem_view_solution', (1, 'a.cpp'), 'problem.viewSolution'),
    ('polygon', 'problem_test_input', (1, 'tests', 1), 'problem.testInput'),
    ('polygon', 'problem_test_answer', (1, 'tests', 1), 'problem.testAnswer'),
    ('problem', 'view_file', ('source', 'a.cpp'), 'problem.viewFile'),
    ('problem', 'view_solution', ('a.cpp',), 'problem.viewSolution'),
    ('problem', 'test_input', ('tests', 1), 'problem.testInput'),
    ('problem', 'test_answer', ('tests', 1), 'problem.testAnswer'),
]


@pytest.fixture(
    params=BINARY_ENDPOINTS,
    ids=['{}.{}'.format(owner, name) for owner, name, _, _ in BINARY_ENDPOINTS],
)
def binary_endpoint(request, post_calls):
    """Each entry point taking the optional binary parameter, pre-bound to valid arguments."""
    owner, name, args, api_method = request.param
    return SimpleNamespace(
        call=functools.partial(getattr(request.getfixturevalue(owner), name), *args),
        api_method=api_method,
    )


@pytest.fixture
def request_body_dispatch(monkeypatch):
    """Replaces the text and bytes request helpers with markers, making the dispatch observable."""
    monkeypatch.setattr(api.Polygon, '_request_text', lambda self, method, args=None: ('text', method, args))
    monkeypatch.setattr(api.Polygon, '_request_raw', lambda self, method, args=None: ('raw', method, args))


class TestResponseBodyAccessors:
    """
    issue_text and issue_raw differ only in which attribute of the same requests.Response they
    return, and both go through _issue.
    """

    def test_raw_body_would_not_survive_manual_decoding(self):
        # Guards the fixture itself: the assertions below only mean something while the two
        # bodies differ and the bytes cannot be decoded as UTF-8.
        assert RAW_BODY != TEXT_BODY.encode('utf-8')
        with pytest.raises(UnicodeDecodeError):
            RAW_BODY.decode('utf-8')

    def test_issue_text_returns_response_text(self, config, post_calls):
        body = Request(config, 'problem.script').issue_text()
        assert isinstance(body, str)
        assert body == TEXT_BODY

    def test_issue_raw_returns_response_content(self, config, post_calls):
        body = Request(config, 'problem.package').issue_raw()
        assert isinstance(body, bytes)
        assert body == RAW_BODY

    def test_issue_returns_the_response_as_is(self, config, post_calls):
        response = Request(config, 'problem.viewFile')._issue()
        assert response.text == TEXT_BODY
        assert response.content == RAW_BODY

    def test_both_accessors_go_through_issue(self, config, monkeypatch):
        issued = []

        def fake_issue(self):
            issued.append(self.method_name)
            return _FakeResponse()

        monkeypatch.setattr(api.Request, '_issue', fake_issue)
        request = Request(config, 'problem.viewFile')
        assert request.issue_text() == TEXT_BODY
        assert request.issue_raw() == RAW_BODY
        assert issued == ['problem.viewFile', 'problem.viewFile']

    def test_each_accessor_issues_exactly_one_request(self, config, post_calls):
        Request(config, 'problem.viewFile').issue_text()
        Request(config, 'problem.viewFile').issue_raw()
        assert len(post_calls) == 2


class TestRequestBodyDispatch:
    """_request_body picks the text or the bytes helper and forwards the arguments unchanged."""

    def test_binary_false_dispatches_to_request_text(self, polygon, request_body_dispatch):
        result = polygon._request_body('problem.viewFile', {'problemId': 1}, binary=False)
        assert result == ('text', 'problem.viewFile', {'problemId': 1})

    def test_binary_true_dispatches_to_request_raw(self, polygon, request_body_dispatch):
        result = polygon._request_body('problem.viewFile', {'problemId': 1}, binary=True)
        assert result == ('raw', 'problem.viewFile', {'problemId': 1})

    def test_omitted_binary_dispatches_to_request_text(self, polygon, request_body_dispatch):
        result = polygon._request_body('problem.viewFile', {'problemId': 1})
        assert result == ('text', 'problem.viewFile', {'problemId': 1})

    def test_missing_args_are_forwarded_as_none(self, polygon, request_body_dispatch):
        assert polygon._request_body('problem.viewFile') == ('text', 'problem.viewFile', None)

    def test_binary_true_returns_the_undecoded_body(self, polygon, post_calls):
        assert polygon._request_body('problem.viewFile', binary=True) == RAW_BODY

    def test_binary_false_returns_the_decoded_body(self, polygon, post_calls):
        assert polygon._request_body('problem.viewFile', binary=False) == TEXT_BODY


class TestBinaryParameter:
    """
    Text by default, bytes on request, for all eight entry points: the four Polygon methods
    returning a file body and their Problem wrappers.
    """

    def test_omitted_binary_returns_text(self, binary_endpoint):
        body = binary_endpoint.call()
        assert isinstance(body, str)
        assert body == TEXT_BODY

    def test_binary_false_returns_text(self, binary_endpoint):
        body = binary_endpoint.call(binary=False)
        assert isinstance(body, str)
        assert body == TEXT_BODY

    def test_binary_true_returns_bytes(self, binary_endpoint):
        body = binary_endpoint.call(binary=True)
        assert isinstance(body, bytes)
        assert body == RAW_BODY

    def test_binary_can_be_passed_positionally(self, binary_endpoint):
        assert binary_endpoint.call(True) == RAW_BODY
        assert binary_endpoint.call(False) == TEXT_BODY

    def test_expected_api_method_is_called(self, binary_endpoint, post_calls):
        binary_endpoint.call()
        assert post_calls[-1]['url'] == 'https://example.invalid/api/' + binary_endpoint.api_method

    def test_binary_is_not_sent_as_a_request_argument(self, binary_endpoint, post_calls):
        binary_endpoint.call(binary=True)
        assert b'binary' not in dict(post_calls[-1]['files'])


class TestScriptIsAlwaysText:
    """problem.script returns a generation script: text only, with no binary parameter."""

    def test_script_returns_text(self, polygon, post_calls):
        body = polygon.problem_script(1, 'tests')
        assert isinstance(body, str)
        assert body == TEXT_BODY

    def test_problem_wrapper_returns_text(self, problem, post_calls):
        body = problem.script('tests')
        assert isinstance(body, str)
        assert body == TEXT_BODY

    def test_script_has_no_binary_parameter(self):
        assert 'binary' not in inspect.signature(Polygon.problem_script).parameters
        assert 'binary' not in inspect.signature(Problem.script).parameters

    def test_script_rejects_a_binary_argument(self, polygon, problem, post_calls):
        with pytest.raises(TypeError):
            polygon.problem_script(1, 'tests', binary=True)
        with pytest.raises(TypeError):
            problem.script('tests', binary=True)


class TestPackageIsAlwaysBytes:
    """problem.package returns an archive: bytes only, with no binary parameter."""

    def test_package_returns_bytes(self, polygon, post_calls):
        body = polygon.problem_package(1, 2)
        assert isinstance(body, bytes)
        assert body == RAW_BODY

    def test_problem_wrapper_returns_bytes(self, problem, post_calls):
        body = problem.package(2)
        assert isinstance(body, bytes)
        assert body == RAW_BODY

    def test_package_has_no_binary_parameter(self):
        assert 'binary' not in inspect.signature(Polygon.problem_package).parameters
        assert 'binary' not in inspect.signature(Problem.package).parameters

    def test_package_rejects_a_binary_argument(self, polygon, problem, post_calls):
        with pytest.raises(TypeError):
            polygon.problem_package(1, 2, binary=True)
        with pytest.raises(TypeError):
            problem.package(2, binary=True)


class TestBuildPackageArguments:
    """
    build_package takes verify before full. Both are sent as named API arguments, so swapping
    them would silently build a package with the wrong flags.
    """

    def test_flags_are_sent_under_their_own_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_build_package(1, verify=True, full=False)
        args = dict(calls[-1]['files'])
        assert args[b'verify'] == b'true'
        assert args[b'full'] == b'false'

    def test_problem_wrapper_keeps_the_verify_full_order(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.build_package(True, False)
        args = dict(calls[-1]['files'])
        assert args[b'verify'] == b'true'
        assert args[b'full'] == b'false'


class TestUpdateInfoArguments:
    """
    Both flags are optional API parameters. They have to reach Polygon under their documented
    names when set - including the False that clears a flag - and stay out of the request
    entirely when unset, so a partial update can not touch a flag it never mentioned.
    """

    def test_flags_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_update_info(1, ProblemInfo(well_formed=True, skip_duplicated_tests_validation=False))
        args = dict(calls[-1]['files'])
        assert args[b'wellFormed'] == b'true'
        assert args[b'skipDuplicatedTestsValidation'] == b'false'

    def test_flags_are_omitted_when_left_unset(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_update_info(1, ProblemInfo(time_limit=2000))
        args = dict(calls[-1]['files'])
        assert args[b'timeLimit'] == b'2000'
        assert b'wellFormed' not in args
        assert b'skipDuplicatedTestsValidation' not in args
