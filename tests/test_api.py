"""
Tests for the parts of the wrapper that need no network access: argument
formatting, local argument validation, JSON parsing and the text/bytes split of
response bodies (with requests.post replaced by a stub).
"""

import functools
import inspect
from collections import namedtuple
from types import SimpleNamespace

import pytest

from polygon_api import (
    AiTips,
    Caution,
    CautionCategory,
    CautionSeverity,
    CheckerTest,
    CheckerTestVerdict,
    FileType,
    ManualTest,
    Package,
    PackageReadinessIssue,
    PackageState,
    PackageType,
    Polygon,
    Problem,
    ProblemCautions,
    ProblemInfo,
    RenderResult,
    RenderStatements,
    RenderStatus,
    RenderedStatement,
    SolutionTag,
    SourceAiTip,
    Statement,
    StatementAiTip,
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


class TestProblemParsing:
    """
    problems.list, contest.problems and problem.create all return Problem objects. note and
    workingCopyRevision are documented as possibly absent, so both are read leniently.
    """

    def test_from_json_with_all_fields(self, polygon):
        problem = Problem.from_json(polygon, {
            'id': 42,
            'owner': 'mmirzayanov',
            'name': 'a-plus-b',
            'note': 'do not publish yet',
            'deleted': False,
            'favourite': True,
            'accessType': 'OWNER',
            'revision': 7,
            'workingCopyRevision': 8,
            'latestPackage': 6,
            'modified': True,
        })
        assert problem.id == 42
        assert problem.owner == 'mmirzayanov'
        assert problem.name == 'a-plus-b'
        assert problem.note == 'do not publish yet'
        assert problem.deleted is False
        assert problem.favorite is True
        assert problem.access_type == 'OWNER'
        assert problem.revision == 7
        assert problem.working_copy_revision == 8
        assert problem.latest_package == 6
        assert problem.modified is True

    def test_note_and_working_copy_revision_default_to_none_when_absent(self, polygon):
        problem = Problem.from_json(polygon, {
            'id': 42,
            'owner': 'mmirzayanov',
            'name': 'a-plus-b',
            'deleted': False,
            'favourite': False,
            'accessType': 'READ',
            'revision': 7,
            'modified': False,
        })
        assert problem.note is None
        assert problem.working_copy_revision is None


class TestManualTestInputBytes:
    """
    problem.tests returns a manual test input twice: input is a lossy UTF-8 view, inputBase64 is
    the exact bytes. Reading only input silently corrupts every test whose input is not valid
    UTF-8, so input_bytes has to carry the decoded inputBase64.
    """

    def test_input_bytes_decodes_input_base64(self, polygon):
        test = api.Test.from_json(polygon, 1, 'tests', {
            'index': 3,
            'manual': True,
            'input': '\ufffd\ufffd\n',
            'inputBase64': 'AP8K',
            'useInStatements': False,
        })
        assert test.input_bytes == b'\x00\xff\n'
        assert test.input == '\ufffd\ufffd\n'

    def test_input_bytes_is_none_when_input_base64_is_absent(self, polygon):
        test = api.Test.from_json(polygon, 1, 'tests', {
            'index': 3,
            'manual': True,
            'input': '1 2\n',
            'useInStatements': False,
        })
        assert test.input == '1 2\n'
        assert test.input_bytes is None

    def test_positional_construction_stays_backwards_compatible(self, polygon):
        test = ManualTest(polygon, 1, 'tests', 3, '1 2\n', 'first', 10, 'a sample')
        assert test.index == 3
        assert test.input == '1 2\n'
        assert test.group == 'first'
        assert test.points == 10
        assert test.description == 'a sample'
        assert test.input_bytes is None


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

    def test_positional_construction_stays_backwards_compatible(self):
        info = ProblemInfo('input.txt', 'output.txt', False, 2000, 256)
        assert info.input_file == 'input.txt'
        assert info.output_file == 'output.txt'
        assert info.interactive is False
        assert info.time_limit == 2000
        assert info.memory_limit == 256
        assert info.well_formed is None
        assert info.skip_duplicated_tests_validation is None

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


class TestStatementParsing:
    """
    problem.statements returns showInReview and showCautionsAndGrammaticalFixes alongside the
    statement text. Both are read leniently, so a statement without them still parses.
    """

    def test_from_json_with_all_fields(self):
        statement = Statement.from_json({
            'encoding': 'UTF-8',
            'name': 'A + B',
            'legend': 'Add two numbers.',
            'input': 'Two integers.',
            'output': 'Their sum.',
            'scoring': 'Full points for a correct answer.',
            'interaction': None,
            'notes': 'Beware of overflow.',
            'tutorial': 'Just print a + b.',
            'showInReview': True,
            'showCautionsAndGrammaticalFixes': False,
        })
        assert statement.encoding == 'UTF-8'
        assert statement.name == 'A + B'
        assert statement.legend == 'Add two numbers.'
        assert statement.input == 'Two integers.'
        assert statement.output == 'Their sum.'
        assert statement.scoring == 'Full points for a correct answer.'
        assert statement.interaction is None
        assert statement.notes == 'Beware of overflow.'
        assert statement.tutorial == 'Just print a + b.'
        assert statement.show_in_review is True
        assert statement.show_cautions_and_grammatical_fixes is False

    def test_positional_construction_stays_backwards_compatible(self):
        statement = Statement('UTF-8', 'A + B', 'Add two numbers.', 'Two integers.', 'Their sum.',
                              'Full points for a correct answer.', None, 'Beware of overflow.', 'Just print a + b.')
        assert statement.encoding == 'UTF-8'
        assert statement.name == 'A + B'
        assert statement.legend == 'Add two numbers.'
        assert statement.notes == 'Beware of overflow.'
        assert statement.tutorial == 'Just print a + b.'
        assert statement.show_in_review is None
        assert statement.show_cautions_and_grammatical_fixes is None

    def test_review_flags_default_to_none_when_absent(self):
        statement = Statement.from_json({
            'encoding': 'UTF-8',
            'name': 'A + B',
            'legend': 'Add two numbers.',
            'input': 'Two integers.',
            'output': 'Their sum.',
            'notes': '',
            'tutorial': '',
        })
        assert statement.show_in_review is None
        assert statement.show_cautions_and_grammatical_fixes is None


class TestRenderResultParsing:
    """
    One HTML or PDF render. Everything except the status is optional: a FAILED render carries a
    message and no file, and a successful one carries contentBase64 only when the caller asked
    for the content.
    """

    def test_from_json_with_all_fields(self):
        result = RenderResult.from_json({
            'status': 'OK',
            'sha256': 'a' * 64,
            'sizeBytes': 23,
            'contentBase64': 'PHA+QWRkIHR3byBudW1iZXJzLjwvcD4=',
        })
        assert result.status == RenderStatus.OK
        assert result.sha256 == 'a' * 64
        assert result.size_bytes == 23
        assert result.content_bytes == b'<p>Add two numbers.</p>'
        assert result.message is None

    def test_content_bytes_decodes_content_base64(self):
        result = RenderResult.from_json({
            'status': 'OK',
            'contentBase64': 'JVBERi0xLjQKJUVPRgo=',
        })
        assert result.content_bytes == b'%PDF-1.4\n%EOF\n'

    def test_content_bytes_is_none_when_content_base64_is_absent(self):
        result = RenderResult.from_json({
            'status': 'OK',
            'sha256': 'b' * 64,
            'sizeBytes': 15,
        })
        assert result.content_bytes is None
        assert result.size_bytes == 15

    def test_a_failed_render_carries_only_a_message(self):
        result = RenderResult.from_json({
            'status': 'FAILED',
            'message': 'Rendering did not finish in 1 minute',
        })
        assert result.status == RenderStatus.FAILED
        assert result.message == 'Rendering did not finish in 1 minute'
        assert result.sha256 is None
        assert result.size_bytes is None
        assert result.content_bytes is None

    @pytest.mark.parametrize('status', ['OK', 'FAILED'])
    def test_every_documented_status_parses(self, status):
        assert RenderResult.from_json({'status': status}).status == RenderStatus[status]

    def test_status_is_serialized_by_name(self):
        assert str(RenderStatus.OK) == 'OK'
        assert str(RenderStatus.FAILED) == 'FAILED'


class TestRenderedStatementParsing:
    """The HTML and the PDF of one language render independently, so one can fail on its own."""

    def test_from_json_parses_the_nested_render_results(self):
        rendered = RenderedStatement.from_json({
            'language': 'english',
            'html': {'status': 'OK', 'sha256': 'c' * 64, 'sizeBytes': 23},
            'pdf': {'status': 'FAILED', 'message': 'LaTeX error'},
        })
        assert rendered.language == 'english'
        assert isinstance(rendered.html, RenderResult)
        assert isinstance(rendered.pdf, RenderResult)
        assert rendered.html.status == RenderStatus.OK
        assert rendered.html.size_bytes == 23
        assert rendered.pdf.status == RenderStatus.FAILED
        assert rendered.pdf.message == 'LaTeX error'


class TestRenderStatementsParsing:
    """
    problem.renderStatements returns statements for every language and tutorials only for the
    languages whose working copy has non-empty tutorial content, so the two lists differ in
    length and must not be mixed up.
    """

    def test_from_json_with_all_fields(self):
        rendered = RenderStatements.from_json({
            'revision': 7,
            'renderingTimeSeconds': 1756600000,
            'statements': [
                {
                    'language': 'english',
                    'html': {'status': 'OK', 'sha256': 'd' * 64, 'sizeBytes': 23},
                    'pdf': {'status': 'OK', 'sha256': 'e' * 64, 'sizeBytes': 15},
                },
                {
                    'language': 'russian',
                    'html': {'status': 'OK', 'sha256': 'f' * 64, 'sizeBytes': 31},
                    'pdf': {'status': 'FAILED', 'message': 'LaTeX error'},
                },
            ],
            'tutorials': [
                {
                    'language': 'english',
                    'html': {'status': 'OK', 'sha256': '0' * 64, 'sizeBytes': 42},
                    'pdf': {'status': 'OK', 'sha256': '1' * 64, 'sizeBytes': 50},
                },
            ],
        })
        assert rendered.revision == 7
        assert rendered.rendering_time_seconds == 1756600000
        assert [s.language for s in rendered.statements] == ['english', 'russian']
        assert [t.language for t in rendered.tutorials] == ['english']
        assert rendered.statements[1].pdf.status == RenderStatus.FAILED
        assert rendered.tutorials[0].html.size_bytes == 42

    def test_a_problem_without_tutorials_parses_into_an_empty_list(self):
        rendered = RenderStatements.from_json({
            'revision': 1,
            'renderingTimeSeconds': 1756600000,
            'statements': [
                {
                    'language': 'english',
                    'html': {'status': 'OK', 'sha256': '2' * 64, 'sizeBytes': 23},
                    'pdf': {'status': 'OK', 'sha256': '3' * 64, 'sizeBytes': 15},
                },
            ],
            'tutorials': [],
        })
        assert rendered.tutorials == []
        assert [s.language for s in rendered.statements] == ['english']

    def test_a_problem_without_statements_parses_into_empty_lists(self):
        rendered = RenderStatements.from_json({
            'revision': 1,
            'renderingTimeSeconds': 1756600000,
            'statements': [],
            'tutorials': [],
        })
        assert rendered.statements == []
        assert rendered.tutorials == []


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


class TestCautionParsing:
    def test_from_json(self):
        caution = Caution.from_json({
            'type': 'NO_TAGS',
            'severity': 'SOFT',
            'category': 'COMMON',
            'message': 'Problem has no tags.',
            'parameters': [],
        })
        assert caution.type == 'NO_TAGS'
        assert caution.severity == CautionSeverity.SOFT
        assert caution.category == CautionCategory.COMMON
        assert caution.message == 'Problem has no tags.'
        assert caution.parameters == []

    @pytest.mark.parametrize('severity', ['SOFT', 'HARD'])
    def test_every_documented_severity_parses(self, severity):
        caution = Caution.from_json({
            'type': 'NO_TAGS', 'severity': severity, 'category': 'COMMON',
            'message': '', 'parameters': [],
        })
        assert caution.severity == CautionSeverity[severity]

    @pytest.mark.parametrize('category', ['COMMON', 'STATEMENT', 'STRUCTURE', 'ISSUES'])
    def test_every_documented_category_parses(self, category):
        caution = Caution.from_json({
            'type': 'NO_TAGS', 'severity': 'SOFT', 'category': category,
            'message': '', 'parameters': [],
        })
        assert caution.category == CautionCategory[category]

    def test_severity_and_category_are_serialized_by_name(self):
        assert str(CautionSeverity.HARD) == 'HARD'
        assert str(CautionCategory.ISSUES) == 'ISSUES'

    @pytest.mark.parametrize('caution_type', ['NO_CHECKER_TESTS', 'NO_VALIDATOR_TESTS', 'SOMETHING_NEW'])
    def test_type_outside_the_documented_examples_parses(self, caution_type):
        """
        The docs give caution types as examples only - NO_CHECKER_TESTS and NO_VALIDATOR_TESTS are
        named in the method description but missing from the type list - so type must stay a string.
        """
        caution = Caution.from_json({
            'type': caution_type, 'severity': 'HARD', 'category': 'STRUCTURE',
            'message': '', 'parameters': [],
        })
        assert caution.type == caution_type
        assert isinstance(caution.type, str)

    def test_message_parameters_are_kept(self):
        caution = Caution.from_json({
            'type': 'TESTSET_SEEMS_TO_BE_INCOMPLETE',
            'severity': 'SOFT',
            'category': 'STRUCTURE',
            'message': 'Testset tests seems to be incomplete',
            'parameters': ['tests', '3'],
        })
        assert caution.parameters == ['tests', '3']


class TestPackageReadinessIssueParsing:
    def test_from_json(self):
        issue = PackageReadinessIssue.from_json({
            'type': 'INVALID_TEST_SCRIPT',
            'reason': 'tests',
            'message': 'Invalid test script for testset tests: unknown generator gen',
        })
        assert issue.type == 'INVALID_TEST_SCRIPT'
        assert issue.reason == 'tests'
        assert issue.message == 'Invalid test script for testset tests: unknown generator gen'

    def test_reason_defaults_to_none_when_absent(self):
        issue = PackageReadinessIssue.from_json({
            'type': 'HAS_MODIFICATIONS',
            'message': 'Problem has uncommitted changes',
        })
        assert issue.reason is None

    @pytest.mark.parametrize('issue_type', ['NO_CHECKER_TESTS', 'SOMETHING_NEW'])
    def test_type_outside_the_documented_examples_parses(self, issue_type):
        """The docs list package validation exception types as examples, so the set is open."""
        issue = PackageReadinessIssue.from_json({'type': issue_type, 'message': ''})
        assert issue.type == issue_type
        assert isinstance(issue.type, str)


class TestStatementAiTipParsing:
    def test_from_json(self):
        tip = StatementAiTip.from_json({
            'language': 'english',
            'source': 'Add two numbers.',
            'suggestion': 'Add two integers.',
            'processing': False,
        })
        assert tip.language == 'english'
        assert tip.source == 'Add two numbers.'
        assert tip.suggestion == 'Add two integers.'
        assert tip.processing is False

    def test_suggestion_is_absent_while_the_request_is_processed(self):
        """The docs: suggestion is absent when no suggestion is available, processing included."""
        tip = StatementAiTip.from_json({
            'language': 'russian',
            'source': 'Sum of two numbers.',
            'processing': True,
        })
        assert tip.processing is True
        assert tip.suggestion is None


class TestSourceAiTipParsing:
    def test_from_json(self):
        tip = SourceAiTip.from_json({
            'name': 'validator.cpp',
            'comment': 'The validator does not check the sum of n over all test cases.',
        })
        assert tip.name == 'validator.cpp'
        assert tip.comment == 'The validator does not check the sum of n over all test cases.'


class TestAiTipsParsing:
    def test_from_json(self):
        tips = AiTips.from_json({
            'disabled': False,
            'statements': [{
                'language': 'english',
                'source': 'Add two numbers.',
                'suggestion': 'Add two integers.',
                'processing': False,
            }],
            'validator': {'name': 'validator.cpp', 'comment': 'No sum check.'},
            'checker': {'name': 'check.cpp', 'comment': 'Reads a token instead of a line.'},
        })
        assert tips.disabled is False
        statement_tip, = tips.statements
        assert statement_tip.language == 'english'
        assert statement_tip.suggestion == 'Add two integers.'
        assert tips.validator.name == 'validator.cpp'
        assert tips.validator.comment == 'No sum check.'
        assert tips.checker.name == 'check.cpp'

    def test_sources_without_a_cached_comment_are_absent(self):
        """The docs: validator and checker may be absent if there is no cached useful comment."""
        tips = AiTips.from_json({'disabled': False, 'statements': []})
        assert tips.statements == []
        assert tips.validator is None
        assert tips.checker is None

    def test_disabled_tips_are_empty(self):
        """The docs: if disabled is true, statements is empty and validator and checker are absent."""
        tips = AiTips.from_json({'disabled': True, 'statements': []})
        assert tips.disabled is True
        assert tips.statements == []
        assert tips.validator is None
        assert tips.checker is None


EMPTY_AI_TIPS = {'disabled': True, 'statements': []}


class TestProblemCautionsParsing:
    def test_from_json(self):
        cautions = ProblemCautions.from_json({
            'common': [{'type': 'NO_TAGS', 'severity': 'SOFT', 'category': 'COMMON',
                        'message': 'No tags', 'parameters': []}],
            'statement': [{'type': 'NO_STATEMENT', 'severity': 'HARD', 'category': 'STATEMENT',
                           'message': 'No statement', 'parameters': []}],
            'structure': [{'type': 'NO_CHECKER', 'severity': 'HARD', 'category': 'STRUCTURE',
                           'message': 'No checker', 'parameters': []}],
            'issues': [{'type': 'OPENED_ISSUES', 'severity': 'SOFT', 'category': 'ISSUES',
                        'message': 'One opened issue', 'parameters': ['1']}],
            'packageReadinessIssues': [{'type': 'HAS_MODIFICATIONS',
                                        'message': 'Problem has uncommitted changes'}],
            'latestPackageWarnings': ['Solution a.cpp is not tested on all tests'],
            'ai': EMPTY_AI_TIPS,
        })
        common, = cautions.common
        assert common.type == 'NO_TAGS'
        assert common.category == CautionCategory.COMMON
        statement, = cautions.statement
        assert statement.severity == CautionSeverity.HARD
        structure, = cautions.structure
        assert structure.type == 'NO_CHECKER'
        issues, = cautions.issues
        assert issues.parameters == ['1']
        issue, = cautions.package_readiness_issues
        assert issue.type == 'HAS_MODIFICATIONS'
        assert cautions.latest_package_warnings == ['Solution a.cpp is not tested on all tests']
        assert cautions.ai.disabled is True

    def test_a_problem_without_cautions_parses_into_empty_lists(self):
        """All four caution arrays, the readiness issues, the warnings and ai are always present."""
        cautions = ProblemCautions.from_json({
            'common': [],
            'statement': [],
            'structure': [],
            'issues': [],
            'packageReadinessIssues': [],
            'latestPackageWarnings': [],
            'ai': EMPTY_AI_TIPS,
        })
        assert cautions.common == []
        assert cautions.statement == []
        assert cautions.structure == []
        assert cautions.issues == []
        assert cautions.package_readiness_issues == []
        assert cautions.latest_package_warnings == []
        assert isinstance(cautions.ai, AiTips)


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
    ('polygon', 'problem_view_statement_resource', (1, 'olymp.sty'), 'problem.viewStatementResource'),
    ('polygon', 'problem_test_input', (1, 'tests', 1), 'problem.testInput'),
    ('polygon', 'problem_test_answer', (1, 'tests', 1), 'problem.testAnswer'),
    ('problem', 'view_file', ('source', 'a.cpp'), 'problem.viewFile'),
    ('problem', 'view_solution', ('a.cpp',), 'problem.viewSolution'),
    ('problem', 'view_statement_resource', ('olymp.sty',), 'problem.viewStatementResource'),
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
    Text by default, bytes on request, for all ten entry points: the five Polygon methods
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


# The pin parameter. Polygon docs, https://codeforces.github.io/polygon-misc/API:
# "To access problem-specific API methods, add a problemId parameter to your request. [...] If the
# problem has the pin code, add the pin parameter to your request." The same holds for contest
# methods and their contestId. problem.create takes no pin: it has no problem to unlock yet.
#
# One row per entry point. polygon_method is None for the Problem shortcuts that have no method of
# their own on Polygon, and result is the JSON the wrapper has to parse out of the response.
PinRow = namedtuple('PinRow', ['polygon_method', 'polygon_args', 'problem_method', 'problem_args', 'result'])

PROBLEM_INFO_RESULT = ('{"inputFile": "in.txt", "outputFile": "out.txt", "interactive": false, '
                       '"timeLimit": 1000, "memoryLimit": 256}')
FILES_RESULT = '{"resourceFiles": [], "sourceFiles": [], "auxFiles": []}'
EMPTY_LIST_RESULT = '[]'
EMPTY_OBJECT_RESULT = '{}'
NULL_RESULT = 'null'
CAUTIONS_RESULT = ('{"common": [], "statement": [], '
                   '"structure": [{"type": "NO_CHECKER", "severity": "HARD", "category": "STRUCTURE", '
                   '"message": "Checker is not set", "parameters": []}], '
                   '"issues": [], '
                   '"packageReadinessIssues": [{"type": "CHECKER_IS_NOT_SET", "message": "Checker is not set"}], '
                   '"latestPackageWarnings": ["Solution a.cpp is not tested on all tests"], '
                   '"ai": {"disabled": true, "statements": []}}')
RENDER_STATEMENTS_RESULT = ('{"revision": 7, "renderingTimeSeconds": 1756600000, '
                            '"statements": [{"language": "english", '
                            '"html": {"status": "OK", "sha256": "%s", "sizeBytes": 23}, '
                            '"pdf": {"status": "FAILED", "message": "LaTeX error"}}], '
                            '"tutorials": []}' % ('a' * 64))

PIN_ROWS = [
    PinRow('problem_info', (1,), 'info', (), PROBLEM_INFO_RESULT),
    PinRow('problem_update_info', (1, ProblemInfo()), 'update_info', (ProblemInfo(),), NULL_RESULT),
    PinRow('problem_update_working_copy', (1,), 'update_working_copy', (), NULL_RESULT),
    PinRow('problem_discard_working_copy', (1,), 'discard_working_copy', (), NULL_RESULT),
    PinRow('problem_commit_changes', (1,), 'commit_changes', (), NULL_RESULT),
    PinRow('problem_view_tags', (1,), 'tags', (), NULL_RESULT),
    PinRow('problem_save_tags', (1, ['dp']), 'save_tags', (['dp'],), NULL_RESULT),
    PinRow('problem_view_general_description', (1,), 'general_description', (), NULL_RESULT),
    PinRow('problem_save_general_description', (1, 'text'), 'save_general_description', ('text',), NULL_RESULT),
    PinRow('problem_view_general_tutorial', (1,), 'general_tutorial', (), NULL_RESULT),
    PinRow('problem_save_general_tutorial', (1, 'text'), 'save_general_tutorial', ('text',), NULL_RESULT),
    PinRow('problem_statements', (1,), 'statements', (), EMPTY_OBJECT_RESULT),
    PinRow('problem_render_statements', (1,), 'render_statements', (), RENDER_STATEMENTS_RESULT),
    PinRow('problem_save_statement', (1, 'english', Statement()), 'save_statement',
           ('english', Statement()), NULL_RESULT),
    PinRow('problem_statement_resources', (1,), 'statement_resources', (), NULL_RESULT),
    PinRow('problem_view_statement_resource', (1, 'olymp.sty'), 'view_statement_resource',
           ('olymp.sty',), NULL_RESULT),
    PinRow('problem_save_statement_resource', (1, 'olymp.sty', 'body'), 'save_statement_resource',
           ('olymp.sty', 'body'), NULL_RESULT),
    PinRow('problem_enable_groups', (1, 'tests', True), 'enable_groups', ('tests', True), NULL_RESULT),
    PinRow('problem_enable_points', (1, True), 'enable_points', (True,), NULL_RESULT),
    PinRow('problem_save_test', (1, 'tests', 1, '1 2'), 'save_test', ('tests', 1, '1 2'), NULL_RESULT),
    PinRow('problem_set_test_group', (1, 'tests', 'first', 1), 'set_test_group',
           ('tests', 'first', 1), NULL_RESULT),
    PinRow('problem_solutions', (1,), 'solutions', (), EMPTY_LIST_RESULT),
    PinRow('problem_files', (1,), 'files', (), FILES_RESULT),
    PinRow(None, None, 'files_resource', (), FILES_RESULT),
    PinRow(None, None, 'files_source', (), FILES_RESULT),
    PinRow(None, None, 'files_aux', (), FILES_RESULT),
    PinRow('problem_tests', (1, 'tests'), 'tests', ('tests',), EMPTY_LIST_RESULT),
    PinRow('problem_script', (1, 'tests'), 'script', ('tests',), NULL_RESULT),
    PinRow('problem_test_input', (1, 'tests', 1), 'test_input', ('tests', 1), NULL_RESULT),
    PinRow('problem_test_answer', (1, 'tests', 1), 'test_answer', ('tests', 1), NULL_RESULT),
    PinRow('problem_save_test_group', (1, 'tests', 'first'), 'save_test_group', ('tests', 'first'), NULL_RESULT),
    PinRow('problem_view_test_group', (1, 'tests'), 'view_test_group', ('tests',), EMPTY_LIST_RESULT),
    PinRow('problem_view_file', (1, FileType.SOURCE, 'a.cpp'), 'view_file',
           (FileType.SOURCE, 'a.cpp'), NULL_RESULT),
    PinRow('problem_view_solution', (1, 'a.cpp'), 'view_solution', ('a.cpp',), NULL_RESULT),
    PinRow('problem_save_file', (1, FileType.SOURCE, 'a.cpp', 'int main() {}'), 'save_file',
           (FileType.SOURCE, 'a.cpp', 'int main() {}'), NULL_RESULT),
    PinRow('problem_save_solution', (1, 'a.cpp', 'int main() {}', SolutionTag.MA), 'save_solution',
           ('a.cpp', 'int main() {}', SolutionTag.MA), NULL_RESULT),
    PinRow('problem_save_script', (1, 'tests', 'gen 1'), 'save_script', ('tests', 'gen 1'), NULL_RESULT),
    PinRow('problem_edit_solution_extra_tags', (1, False, 'a.cpp', 'tests'), 'edit_solution_extra_tags',
           (False, 'a.cpp', 'tests'), NULL_RESULT),
    PinRow('problem_checker', (1,), 'checker', (), NULL_RESULT),
    PinRow('problem_set_checker', (1, 'check.cpp'), 'set_checker', ('check.cpp',), NULL_RESULT),
    PinRow('problem_checker_tests', (1,), 'checker_tests', (), EMPTY_LIST_RESULT),
    PinRow('problem_save_checker_test', (1, 1), 'save_checker_test', (1,), NULL_RESULT),
    PinRow('problem_validator', (1,), 'validator', (), NULL_RESULT),
    PinRow('problem_set_validator', (1, 'val.cpp'), 'set_validator', ('val.cpp',), NULL_RESULT),
    PinRow('problem_extra_validators', (1,), 'extra_validators', (), NULL_RESULT),
    PinRow('problem_validator_tests', (1,), 'validator_tests', (), EMPTY_LIST_RESULT),
    PinRow('problem_save_validator_test', (1, 1), 'save_validator_test', (1,), NULL_RESULT),
    PinRow('problem_interactor', (1,), 'interactor', (), NULL_RESULT),
    PinRow('problem_set_interactor', (1, 'int.cpp'), 'set_interactor', ('int.cpp',), NULL_RESULT),
    PinRow('problem_cautions', (1,), 'cautions', (), CAUTIONS_RESULT),
    PinRow('problem_packages', (1,), 'packages', (), EMPTY_LIST_RESULT),
    PinRow('problem_package', (1, 2), 'package', (2,), NULL_RESULT),
    PinRow('problem_build_package', (1, True, False), 'build_package', (True, False), NULL_RESULT),
]

POLYGON_PIN_ROWS = [row for row in PIN_ROWS if row.polygon_method is not None]


def _ok_body(result):
    return '{"status": "OK", "result": %s}' % result


def _sent_args(calls):
    return dict(calls[-1]['files'])


@pytest.fixture(
    params=POLYGON_PIN_ROWS,
    ids=[row.polygon_method for row in POLYGON_PIN_ROWS],
)
def polygon_pin_endpoint(request, polygon, monkeypatch):
    """Each problem-specific Polygon method, pre-bound to valid arguments."""
    row = request.param
    calls = _install_fake_post(monkeypatch, text=_ok_body(row.result))
    return SimpleNamespace(
        call=functools.partial(getattr(polygon, row.polygon_method), *row.polygon_args),
        calls=calls,
    )


@pytest.fixture(
    params=PIN_ROWS,
    ids=[row.problem_method for row in PIN_ROWS],
)
def problem_pin_endpoint(request, problem, monkeypatch):
    """Each public Problem method, pre-bound to valid arguments."""
    row = request.param
    calls = _install_fake_post(monkeypatch, text=_ok_body(row.result))
    return SimpleNamespace(
        problem=problem,
        call=functools.partial(getattr(problem, row.problem_method), *row.problem_args),
        calls=calls,
    )


class TestPinCoverage:
    """The tables below drive every pin test, so a new method without a pin fails here first."""

    def test_every_problem_specific_polygon_method_is_covered(self):
        covered = {row.polygon_method for row in POLYGON_PIN_ROWS}
        assert covered == {name for name in dir(Polygon) if name.startswith('problem_')} - {'problem_create'}

    def test_every_public_problem_method_is_covered(self):
        covered = {row.problem_method for row in PIN_ROWS}
        assert covered == {name for name in dir(Problem) if not name.startswith('_')} - {'from_json'}


class TestPolygonPin:
    def test_pin_is_sent_as_a_request_argument(self, polygon_pin_endpoint):
        polygon_pin_endpoint.call(pin='1234')
        assert _sent_args(polygon_pin_endpoint.calls)[b'pin'] == b'1234'

    def test_pin_is_omitted_when_not_passed(self, polygon_pin_endpoint):
        polygon_pin_endpoint.call()
        assert b'pin' not in _sent_args(polygon_pin_endpoint.calls)


class TestProblemPin:
    def test_the_pin_field_is_sent(self, problem_pin_endpoint):
        problem_pin_endpoint.problem.pin = '1234'
        problem_pin_endpoint.call()
        assert _sent_args(problem_pin_endpoint.calls)[b'pin'] == b'1234'

    def test_the_pin_argument_is_sent_without_a_field(self, problem_pin_endpoint):
        problem_pin_endpoint.call(pin='1234')
        assert _sent_args(problem_pin_endpoint.calls)[b'pin'] == b'1234'

    def test_the_pin_argument_overrides_the_field(self, problem_pin_endpoint):
        problem_pin_endpoint.problem.pin = '1234'
        problem_pin_endpoint.call(pin='5678')
        assert _sent_args(problem_pin_endpoint.calls)[b'pin'] == b'5678'

    def test_the_overridden_field_is_left_alone(self, problem_pin_endpoint):
        problem_pin_endpoint.problem.pin = '1234'
        problem_pin_endpoint.call(pin='5678')
        assert problem_pin_endpoint.problem.pin == '1234'

    def test_no_pin_is_sent_without_a_field_or_an_argument(self, problem_pin_endpoint):
        problem_pin_endpoint.call()
        assert b'pin' not in _sent_args(problem_pin_endpoint.calls)

    def test_the_field_defaults_to_none(self, problem):
        assert problem.pin is None

    def test_positional_construction_stays_backwards_compatible(self, polygon):
        problem = Problem(polygon, 1, 'owner', 'name', False, False, 'WRITE', 3, 2, False)
        assert problem.id == 1
        assert problem.pin is None


class TestMethodsWithoutPin:
    """problems.list and problem.create are not problem-specific, so neither takes a pin."""

    def test_problems_list_rejects_a_pin(self, polygon, post_calls):
        with pytest.raises(TypeError):
            polygon.problems_list(pin='1234')

    def test_problem_create_rejects_a_pin(self, polygon, post_calls):
        with pytest.raises(TypeError):
            polygon.problem_create('name', pin='1234')


class TestContestPin:
    def test_pin_is_sent_as_a_request_argument(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(EMPTY_OBJECT_RESULT))
        polygon.contest_problems(1, pin='1234')
        assert _sent_args(calls)[b'pin'] == b'1234'

    def test_pin_is_omitted_when_not_passed(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(EMPTY_OBJECT_RESULT))
        polygon.contest_problems(1)
        assert b'pin' not in _sent_args(calls)

    def test_the_contest_pin_does_not_become_the_problem_pin(self, polygon, monkeypatch):
        """
        The docs describe the contest pin and the problem pin as separate codes, so a contest pin
        must not be reused for the problems it returns.
        """
        _install_fake_post(monkeypatch, text=_ok_body('{"A": {"id": 1}}'))
        problems = polygon.contest_problems(1, pin='1234')
        assert problems['A'].pin is None


MANUAL_TEST_RESULT = '[{"index": 1, "manual": true, "input": "1 2", "useInStatements": false}]'
GENERATED_TEST_RESULT = '[{"index": 1, "manual": false, "scriptLine": "gen 1", "useInStatements": false}]'


class TestTestObjectPin:
    """
    Test objects issue their own requests through ManualTest.save, so they have to carry the pin
    of the problem they were listed from.
    """

    def test_a_test_carries_the_pin_of_its_problem(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(MANUAL_TEST_RESULT))
        problem.pin = '1234'
        assert problem.tests('tests')[0].pin == '1234'

    def test_a_generated_test_carries_the_pin_of_its_problem(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(GENERATED_TEST_RESULT))
        problem.pin = '1234'
        assert problem.tests('tests')[0].pin == '1234'

    def test_a_test_listed_without_a_pin_has_none(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(MANUAL_TEST_RESULT))
        assert problem.tests('tests')[0].pin is None

    def test_save_sends_the_pin_of_the_problem(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(MANUAL_TEST_RESULT))
        problem.pin = '1234'
        problem.tests('tests')[0].save()
        assert _sent_args(calls)[b'pin'] == b'1234'

    def test_save_sends_the_pin_of_the_listing_polygon_call(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(MANUAL_TEST_RESULT))
        polygon.problem_tests(1, 'tests', pin='1234')[0].save()
        assert _sent_args(calls)[b'pin'] == b'1234'

    def test_the_save_argument_overrides_the_carried_pin(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(MANUAL_TEST_RESULT))
        problem.pin = '1234'
        problem.tests('tests')[0].save(pin='5678')
        assert _sent_args(calls)[b'pin'] == b'5678'

    def test_save_sends_no_pin_without_one(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(MANUAL_TEST_RESULT))
        problem.tests('tests')[0].save()
        assert b'pin' not in _sent_args(calls)


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


class TestSaveStatementArguments:
    """
    The two review flags are optional parameters of problem.saveStatement. Saving a statement
    that leaves them unset must not mention them, otherwise editing a legend would also decide
    whether the statement shows up in the problem review.
    """

    def test_review_flags_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_save_statement(1, 'english', Statement(
            legend='Add two numbers.',
            show_in_review=False,
            show_cautions_and_grammatical_fixes=True,
        ))
        args = dict(calls[-1]['files'])
        assert args[b'showInReview'] == b'false'
        assert args[b'showCautionsAndGrammaticalFixes'] == b'true'

    def test_review_flags_are_omitted_when_left_unset(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_save_statement(1, 'english', Statement(legend='Add two numbers.'))
        args = dict(calls[-1]['files'])
        assert args[b'legend'] == b'Add two numbers.'
        assert b'showInReview' not in args
        assert b'showCautionsAndGrammaticalFixes' not in args


class TestProblemCautions:
    """problem.cautions takes no parameters of its own and returns a single object, not a list."""

    def test_only_the_problem_id_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(CAUTIONS_RESULT))
        polygon.problem_cautions(1)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.cautions'
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_the_result_is_parsed_into_problem_cautions(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(CAUTIONS_RESULT))
        cautions = polygon.problem_cautions(1)
        assert isinstance(cautions, ProblemCautions)
        structure, = cautions.structure
        assert structure.type == 'NO_CHECKER'
        assert structure.severity == CautionSeverity.HARD
        issue, = cautions.package_readiness_issues
        assert issue.type == 'CHECKER_IS_NOT_SET'
        assert cautions.latest_package_warnings == ['Solution a.cpp is not tested on all tests']
        assert cautions.ai.disabled is True

    def test_the_problem_shortcut_returns_the_same_object(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(CAUTIONS_RESULT))
        cautions = problem.cautions()
        assert isinstance(cautions, ProblemCautions)
        assert cautions.latest_package_warnings == ['Solution a.cpp is not tested on all tests']


class TestRenderStatements:
    """
    includeContent is the one optional parameter of problem.renderStatements. Leaving it unset
    must not mention it, so a caller only after the sha256 and the sizes does not pull whole
    PDFs over the wire.
    """

    def test_include_content_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(RENDER_STATEMENTS_RESULT))
        polygon.problem_render_statements(1, include_content=True)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.renderStatements'
        assert _sent_args(calls)[b'includeContent'] == b'true'

    def test_include_content_is_omitted_when_left_unset(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(RENDER_STATEMENTS_RESULT))
        polygon.problem_render_statements(1)
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_the_result_is_parsed_into_render_statements(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(RENDER_STATEMENTS_RESULT))
        rendered = polygon.problem_render_statements(1)
        assert isinstance(rendered, RenderStatements)
        assert rendered.revision == 7
        assert rendered.rendering_time_seconds == 1756600000
        statement, = rendered.statements
        assert statement.language == 'english'
        assert statement.html.status == RenderStatus.OK
        assert statement.html.sha256 == 'a' * 64
        assert statement.html.size_bytes == 23
        assert statement.html.content_bytes is None
        assert statement.pdf.status == RenderStatus.FAILED
        assert statement.pdf.message == 'LaTeX error'
        assert rendered.tutorials == []

    def test_the_problem_shortcut_returns_the_same_object(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(RENDER_STATEMENTS_RESULT))
        rendered = problem.render_statements()
        assert isinstance(rendered, RenderStatements)
        assert rendered.revision == 7

    def test_the_problem_shortcut_forwards_include_content(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(RENDER_STATEMENTS_RESULT))
        problem.render_statements(True)
        assert _sent_args(calls)[b'includeContent'] == b'true'


class TestViewStatementResource:
    """
    problem.viewStatementResource returns the resource file itself, not JSON, so the wrapper
    hands the body back untouched instead of looking for a status in it.
    """

    def test_the_resource_name_is_sent_under_its_documented_name(self, polygon, post_calls):
        polygon.problem_view_statement_resource(1, 'olymp.sty')
        assert post_calls[-1]['url'] == 'https://example.invalid/api/problem.viewStatementResource'
        assert _sent_args(post_calls)[b'name'] == b'olymp.sty'

    def test_the_body_is_returned_without_json_parsing(self, polygon, post_calls):
        assert polygon.problem_view_statement_resource(1, 'olymp.sty') == TEXT_BODY

    def test_the_problem_shortcut_sends_the_same_request(self, problem, post_calls):
        assert problem.view_statement_resource('olymp.sty') == TEXT_BODY
        assert post_calls[-1]['url'] == 'https://example.invalid/api/problem.viewStatementResource'
        assert _sent_args(post_calls)[b'name'] == b'olymp.sty'
