"""
Tests for the parts of the wrapper that need no network access: argument
formatting, local argument validation, JSON parsing and the text/bytes split of
response bodies (with requests.post replaced by a stub).
"""

import functools
import inspect
import json
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
    CommitResult,
    DeleteTestsFailedException,
    DeleteTestsResult,
    File,
    FileType,
    Invocation,
    InvocationResults,
    InvocationRun,
    InvocationRunVerdict,
    InvocationStatus,
    Issue,
    IssueComment,
    IssueStatus,
    IssueType,
    ManualTest,
    Material,
    MaterialItem,
    MaterialItemType,
    MaterialPublishStrategy,
    MaterialTest,
    Package,
    PackageReadinessIssue,
    PackageState,
    PackageType,
    Polygon,
    PolygonRequestFailedException,
    Problem,
    ProblemAccess,
    ProblemAccessType,
    ProblemCautions,
    ProblemInfo,
    RenderResult,
    RenderStatements,
    RenderStatus,
    RenderedStatement,
    SolutionTag,
    SolutionTags,
    SourceAiTip,
    Statement,
    StatementAiTip,
    Stress,
    StressCountertest,
    StressRun,
    StressRunStatus,
    StressRunVerdict,
    StressSolutionReport,
    StressSolutionVerdict,
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


class TestDeleteTestValidation:
    def test_requires_test_index_or_test_indices(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_delete_test(1, 'tests')

    def test_rejects_both_test_index_and_test_indices(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_delete_test(1, 'tests', test_index=1, test_indices=[1, 2])


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
        assert problem.access_type == ProblemAccessType.OWNER
        assert problem.revision == 7
        assert problem.working_copy_revision == 8
        assert problem.latest_package == 6
        assert problem.modified is True

    def test_access_type_defaults_to_none_when_absent(self, polygon):
        """
        accessType is absent from a Problem the caller builds by hand and from any response that
        omits it, so parsing must leave it None instead of raising on a missing enum name.
        """
        problem = Problem.from_json(polygon, {'id': 42})
        assert problem.access_type is None

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


class TestTestPointsParsing:
    """
    Test points are a double with at most two digits after the decimal point. Reading them through
    int() truncated 2.5 to 2, so a save of a test read back from Polygon wrote the wrong points,
    and a value sent as a string such as '2.5' raised instead.
    """

    @pytest.mark.parametrize('test_json', [
        {'index': 1, 'manual': True, 'input': '1 2\n', 'useInStatements': False},
        {'index': 1, 'manual': False, 'scriptLine': 'gen 1', 'useInStatements': False},
    ], ids=['manual', 'generated'])
    @pytest.mark.parametrize('points', [2.5, '2.5'], ids=['number', 'string'])
    def test_fractional_points_are_kept(self, polygon, test_json, points):
        test = api.Test.from_json(polygon, 1, 'tests', dict(test_json, points=points))
        assert test.points == 2.5

    @pytest.mark.parametrize('test_json', [
        {'index': 1, 'manual': True, 'input': '1 2\n', 'useInStatements': False},
        {'index': 1, 'manual': False, 'scriptLine': 'gen 1', 'useInStatements': False},
    ], ids=['manual', 'generated'])
    def test_whole_points_are_a_float(self, polygon, test_json):
        test = api.Test.from_json(polygon, 1, 'tests', dict(test_json, points=10))
        assert isinstance(test.points, float)
        assert test.points == 10.0

    @pytest.mark.parametrize('test_json', [
        {'index': 1, 'manual': True, 'input': '1 2\n', 'useInStatements': False},
        {'index': 1, 'manual': False, 'scriptLine': 'gen 1', 'useInStatements': False},
    ], ids=['manual', 'generated'])
    def test_absent_points_are_zero(self, polygon, test_json):
        test = api.Test.from_json(polygon, 1, 'tests', test_json)
        assert isinstance(test.points, float)
        assert test.points == 0.0


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


class TestVerifyInputOutputForStatementsParsing:
    """
    problem.tests returns verifyInputOutputForStatements as a JSON boolean. Comparing it with the
    string 'true' turned every value into False, so a save of a test read back from Polygon
    silently switched the verification off.
    """

    @pytest.mark.parametrize('test_json', [
        {'index': 1, 'manual': True, 'input': '1 2\n', 'useInStatements': True},
        {'index': 1, 'manual': False, 'scriptLine': 'gen 1', 'useInStatements': True},
    ], ids=['manual', 'generated'])
    @pytest.mark.parametrize('verify', [True, False])
    def test_boolean_is_kept(self, polygon, test_json, verify):
        test = api.Test.from_json(polygon, 1, 'tests', dict(test_json, verifyInputOutputForStatements=verify))
        assert test.verify_input_output_for_statements is verify

    @pytest.mark.parametrize('test_json', [
        {'index': 1, 'manual': True, 'input': '1 2\n', 'useInStatements': True},
        {'index': 1, 'manual': False, 'scriptLine': 'gen 1', 'useInStatements': True},
    ], ids=['manual', 'generated'])
    def test_absent_is_none(self, polygon, test_json):
        test = api.Test.from_json(polygon, 1, 'tests', test_json)
        assert test.verify_input_output_for_statements is None


class TestProblemInfoParsing:
    """
    problem.info returns wellFormed, skipDuplicatedTestsValidation, useInteractionLogInExampleTests,
    runTwice and interactiveSecondRun next to the limits. All of them are read leniently: a problem
    for which Polygon omits a flag (the docs give two of them only for interactive problems) must
    still yield a ProblemInfo instead of failing the whole call.
    """

    def test_from_json_with_all_fields(self):
        info = ProblemInfo.from_json({
            'inputFile': 'input.txt',
            'outputFile': 'output.txt',
            'interactive': True,
            'useInteractionLogInExampleTests': True,
            'wellFormed': True,
            'skipDuplicatedTestsValidation': False,
            'runTwice': True,
            'interactiveSecondRun': False,
            'timeLimit': 2000,
            'memoryLimit': 256,
        })
        assert info.input_file == 'input.txt'
        assert info.output_file == 'output.txt'
        assert info.interactive is True
        assert info.use_interaction_log_in_example_tests is True
        assert info.well_formed is True
        assert info.skip_duplicated_tests_validation is False
        assert info.run_twice is True
        assert info.interactive_second_run is False
        assert info.time_limit == 2000
        assert info.memory_limit == 256

    def test_a_non_interactive_problem_without_the_interactive_only_flags(self):
        info = ProblemInfo.from_json({
            'inputFile': 'input.txt',
            'outputFile': 'output.txt',
            'interactive': False,
            'wellFormed': False,
            'skipDuplicatedTestsValidation': False,
            'runTwice': True,
            'timeLimit': 2000,
            'memoryLimit': 256,
        })
        assert info.run_twice is True
        assert info.use_interaction_log_in_example_tests is None
        assert info.interactive_second_run is None

    def test_positional_construction_stays_backwards_compatible(self):
        info = ProblemInfo('input.txt', 'output.txt', False, 2000, 256)
        assert info.input_file == 'input.txt'
        assert info.output_file == 'output.txt'
        assert info.interactive is False
        assert info.time_limit == 2000
        assert info.memory_limit == 256
        assert info.well_formed is None
        assert info.skip_duplicated_tests_validation is None
        assert info.use_interaction_log_in_example_tests is None
        assert info.run_twice is None
        assert info.interactive_second_run is None

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
        assert info.use_interaction_log_in_example_tests is None
        assert info.run_twice is None
        assert info.interactive_second_run is None


class TestTestDeletionFailureParsing:
    def test_from_json(self):
        failure = api.TestDeletionFailure.from_json({
            'index': 3,
            'reason': 'NOT_FOUND',
            'message': 'Test 3 not found',
        })
        assert failure.index == 3
        assert failure.reason == api.TestDeletionFailureReason.NOT_FOUND
        assert failure.message == 'Test 3 not found'

    @pytest.mark.parametrize('reason', ['DUPLICATE', 'NOT_FOUND', 'FREEMARKER_SCRIPT_TEST', 'DELETE_FAILED'])
    def test_every_documented_reason_parses(self, reason):
        failure = api.TestDeletionFailure.from_json({'index': 1, 'reason': reason, 'message': ''})
        assert failure.reason == api.TestDeletionFailureReason[reason]

    def test_reason_is_serialized_by_name(self):
        assert str(api.TestDeletionFailureReason.FREEMARKER_SCRIPT_TEST) == 'FREEMARKER_SCRIPT_TEST'


class TestDeleteTestsResultParsing:
    def test_from_json(self):
        result = DeleteTestsResult.from_json({'failures': [
            {'index': 2, 'reason': 'DUPLICATE', 'message': 'Test 2 is requested twice'},
            {'index': 5, 'reason': 'FREEMARKER_SCRIPT_TEST', 'message': 'Test 5 is generated by a script'},
        ]})
        assert [type(failure) for failure in result.failures] == [api.TestDeletionFailure] * 2
        assert [failure.index for failure in result.failures] == [2, 5]
        assert [failure.reason for failure in result.failures] == [
            api.TestDeletionFailureReason.DUPLICATE,
            api.TestDeletionFailureReason.FREEMARKER_SCRIPT_TEST,
        ]


class TestCommitResultParsing:
    def test_from_json(self):
        result = CommitResult.from_json({
            'committed': True,
            'conflictOccurred': False,
            'message': 'Changes committed',
        })
        assert result.committed is True
        assert result.conflict_occurred is False
        assert result.message == 'Changes committed'

    def test_a_commit_without_changes_is_not_committed(self):
        """
        The docs: with no changes the status is still OK, and only committed=false tells the
        caller that no revision was made.
        """
        result = CommitResult.from_json({
            'committed': False,
            'conflictOccurred': False,
            'message': 'No changes',
        })
        assert result.committed is False
        assert result.conflict_occurred is False
        assert result.message == 'No changes'

    def test_a_conflict_is_reported_beside_the_commit_flag(self):
        result = CommitResult.from_json({
            'committed': False,
            'conflictOccurred': True,
            'message': 'Conflict occurred',
        })
        assert result.committed is False
        assert result.conflict_occurred is True


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


class TestStatementResourcesParsing:
    """
    problem.statementResources is documented to return a list of File objects, see
    https://codeforces.github.io/polygon-misc/API. Statement resources carry neither sourceType
    nor resourceAdvancedProperties, so both stay None.
    """

    RESOURCES_RESULT = ('[{"name": "olymp.sty", "modificationTimeSeconds": 1600000000, '
                        '"length": 1024}]')

    def test_resources_are_parsed_into_file_objects(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(self.RESOURCES_RESULT))
        resources = polygon.problem_statement_resources(1)
        assert len(resources) == 1
        resource = resources[0]
        assert isinstance(resource, File)
        assert resource.name == 'olymp.sty'
        assert resource.modification_time_seconds == 1600000000
        assert resource.length == 1024

    def test_statement_resources_have_no_source_type_or_advanced_properties(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(self.RESOURCES_RESULT))
        resource = polygon.problem_statement_resources(1)[0]
        assert resource.source_type is None
        assert resource.resource_advanced_properties is None

    def test_a_problem_without_resources_parses_into_an_empty_list(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body('[]'))
        assert polygon.problem_statement_resources(1) == []

    def test_problem_shortcut_parses_the_same_way(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(self.RESOURCES_RESULT))
        resources = problem.statement_resources()
        assert [resource.name for resource in resources] == ['olymp.sty']
        assert isinstance(resources[0], File)


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


class TestProblemAccessParsing:
    def test_from_json(self):
        access = ProblemAccess.from_json({'login': 'alice', 'accessType': 'READ'})
        assert access.login == 'alice'
        assert access.access_type == ProblemAccessType.READ

    def test_a_user_group_keeps_its_leading_at_sign(self):
        """The docs: login is a user login, or a user-group name prefixed with @."""
        access = ProblemAccess.from_json({'login': '@editors', 'accessType': 'WRITE'})
        assert access.login == '@editors'
        assert access.access_type == ProblemAccessType.WRITE

    @pytest.mark.parametrize('access_type', ['READ', 'WRITE', 'OWNER'])
    def test_every_returned_access_type_parses(self, access_type):
        """problem.accesses returns READ, WRITE or OWNER; NONE is a set-only value."""
        access = ProblemAccess.from_json({'login': 'alice', 'accessType': access_type})
        assert access.access_type == ProblemAccessType[access_type]


ISSUE_JSON = {
    'id': 1234,
    'type': 'BUG',
    'status': 'CLOSED',
    'author': 'alice',
    'assignee': 'bob',
    'html': "<div class='markup'><p>Test 5 is invalid</p>\n</div>",
    'creationTimeSeconds': 1790000000,
    'modificationTimeSeconds': 1790003600,
    'comments': [
        {
            'author': 'bob',
            'html': "<div class='markup'><p>Fixed in revision 12</p>\n</div>",
            'creationTimeSeconds': 1790003600,
            'status': 'CLOSED',
        },
    ],
}


class TestIssueParsing:
    def test_from_json(self):
        """The example response of problem.issues in the docs."""
        issue = Issue.from_json(ISSUE_JSON)
        assert issue.id == 1234
        assert issue.type == IssueType.BUG
        assert issue.status == IssueStatus.CLOSED
        assert issue.author == 'alice'
        assert issue.assignee == 'bob'
        assert issue.html == "<div class='markup'><p>Test 5 is invalid</p>\n</div>"
        assert issue.creation_time_seconds == 1790000000
        assert issue.modification_time_seconds == 1790003600
        comment, = issue.comments
        assert isinstance(comment, IssueComment)
        assert comment.author == 'bob'
        assert comment.status == IssueStatus.CLOSED

    def test_assignee_defaults_to_none_when_absent(self):
        issue_json = dict(ISSUE_JSON, comments=[])
        del issue_json['assignee']
        assert Issue.from_json(issue_json).assignee is None

    def test_a_new_issue_parses_with_an_empty_comment_list(self):
        """The docs: problem.addIssue returns the issue with status OPENED and no comments."""
        issue = Issue.from_json(dict(ISSUE_JSON, status='OPENED', comments=[]))
        assert issue.status == IssueStatus.OPENED
        assert issue.comments == []

    def test_comments_keep_their_chronological_order(self):
        issue = Issue.from_json(dict(ISSUE_JSON, comments=[
            {'author': 'bob', 'html': '<p>first</p>', 'creationTimeSeconds': 1790001000},
            {'author': 'alice', 'html': '<p>second</p>', 'creationTimeSeconds': 1790002000},
        ]))
        assert [comment.html for comment in issue.comments] == ['<p>first</p>', '<p>second</p>']

    @pytest.mark.parametrize('issue_type', ['DISCUSSION', 'ENHANCEMENT', 'BUG'])
    def test_every_documented_type_parses(self, issue_type):
        assert Issue.from_json(dict(ISSUE_JSON, type=issue_type)).type == IssueType[issue_type]

    @pytest.mark.parametrize('status', ['OPENED', 'REOPENED', 'CLOSED'])
    def test_every_documented_status_parses(self, status):
        assert Issue.from_json(dict(ISSUE_JSON, status=status)).status == IssueStatus[status]

    def test_type_and_status_are_serialized_by_name(self):
        """problem.addIssue and problem.updateIssue take both as their bare names."""
        assert str(IssueType.ENHANCEMENT) == 'ENHANCEMENT'
        assert str(IssueStatus.REOPENED) == 'REOPENED'


class TestIssueCommentParsing:
    def test_from_json_with_every_change(self):
        comment = IssueComment.from_json({
            'author': 'bob',
            'html': '<p>Reassigning</p>',
            'creationTimeSeconds': 1790003600,
            'status': 'REOPENED',
            'type': 'ENHANCEMENT',
            'assignee': 'carol',
        })
        assert comment.author == 'bob'
        assert comment.html == '<p>Reassigning</p>'
        assert comment.creation_time_seconds == 1790003600
        assert comment.status == IssueStatus.REOPENED
        assert comment.type == IssueType.ENHANCEMENT
        assert comment.assignee == 'carol'

    def test_a_plain_comment_changes_nothing(self):
        """The docs: status, type and assignee are absent when the comment did not change them."""
        comment = IssueComment.from_json({
            'author': 'bob',
            'html': '<p>Looking into it</p>',
            'creationTimeSeconds': 1790003600,
        })
        assert comment.status is None
        assert comment.type is None
        assert comment.assignee is None


class TestProblemAccessTypeSerialization:
    @pytest.mark.parametrize('access_type', ['READ', 'WRITE', 'OWNER', 'NONE'])
    def test_every_access_type_is_serialized_by_name(self, access_type):
        """
        problem.setAccess takes the accessType as its bare name, so the enum has to stringify to
        NONE rather than to ProblemAccessType.NONE.
        """
        assert str(ProblemAccessType[access_type]) == access_type


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
NOTE_RESULT = '"a note"'
COMMIT_RESULT = '{"committed": true, "conflictOccurred": false, "message": "Changes committed"}'
CAUTIONS_RESULT = ('{"common": [], "statement": [], '
                   '"structure": [{"type": "NO_CHECKER", "severity": "HARD", "category": "STRUCTURE", '
                   '"message": "Checker is not set", "parameters": []}], '
                   '"issues": [], '
                   '"packageReadinessIssues": [{"type": "CHECKER_IS_NOT_SET", "message": "Checker is not set"}], '
                   '"latestPackageWarnings": ["Solution a.cpp is not tested on all tests"], '
                   '"ai": {"disabled": true, "statements": []}}')
ISSUE_RESULT = ('{"id": 1234, "type": "BUG", "status": "OPENED", "author": "alice", '
                '"html": "<p>Test 5 is invalid</p>", "creationTimeSeconds": 1790000000, '
                '"modificationTimeSeconds": 1790000000, "comments": []}')
ACCESSES_RESULT = ('[{"login": "@editors", "accessType": "WRITE"}, '
                   '{"login": "alice", "accessType": "READ"}, '
                   '{"login": "owner", "accessType": "OWNER"}]')
RENDER_STATEMENTS_RESULT = ('{"revision": 7, "renderingTimeSeconds": 1756600000, '
                            '"statements": [{"language": "english", '
                            '"html": {"status": "OK", "sha256": "%s", "sizeBytes": 23}, '
                            '"pdf": {"status": "FAILED", "message": "LaTeX error"}}], '
                            '"tutorials": []}' % ('a' * 64))

INVOCATION_RESULTS_RESULT = ('{"invocation": {"id": 501, "description": "", "testset": "tests", '
                             '"status": "PENDING", "creationTimeSeconds": 1790000000, "violateTag": false, '
                             '"solutions": [], "tests": []}, "solutionTags": [], "runs": []}')
STRESS_RESULT = ('{"index": 1, "scriptPattern": "gen [1..10]", "solutionNames": ["main.cpp", "wa.cpp"], '
                 '"timeLimit": 2000, "memoryLimit": 256, "totalTimeLimit": 60000, "ignoreValidators": false, '
                 '"description": ""}')
ADDED_TEST_RESULT = ('{"index": 5, "manual": false, "scriptLine": "gen 10 57 abacaba 2f8a91", '
                     '"description": "Added from stress #1", "useInStatements": false}')
SOLUTIONS_ITEM = MaterialItem(MaterialItemType.SOLUTIONS, names=['main.cpp'])

PIN_ROWS = [
    PinRow('problem_info', (1,), 'info', (), PROBLEM_INFO_RESULT),
    PinRow('problem_update_info', (1, ProblemInfo()), 'update_info', (ProblemInfo(),), NULL_RESULT),
    PinRow('problem_view_note', (1,), 'view_note', (), NOTE_RESULT),
    PinRow('problem_save_note', (1, 'a note'), 'save_note', ('a note',), NULL_RESULT),
    PinRow('problem_update_working_copy', (1,), 'update_working_copy', (), NULL_RESULT),
    PinRow('problem_discard_working_copy', (1,), 'discard_working_copy', (), NULL_RESULT),
    PinRow('problem_commit_changes', (1,), 'commit_changes', (), COMMIT_RESULT),
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
    PinRow('problem_delete_statement', (1, 'english'), 'delete_statement', ('english',), NULL_RESULT),
    PinRow('problem_statement_resources', (1,), 'statement_resources', (), EMPTY_LIST_RESULT),
    PinRow('problem_view_statement_resource', (1, 'olymp.sty'), 'view_statement_resource',
           ('olymp.sty',), NULL_RESULT),
    PinRow('problem_save_statement_resource', (1, 'olymp.sty', 'body'), 'save_statement_resource',
           ('olymp.sty', 'body'), NULL_RESULT),
    PinRow('problem_delete_statement_resource', (1, 'olymp.sty'), 'delete_statement_resource',
           ('olymp.sty',), NULL_RESULT),
    PinRow('problem_enable_groups', (1, 'tests', True), 'enable_groups', ('tests', True), NULL_RESULT),
    PinRow('problem_enable_points', (1, True), 'enable_points', (True,), NULL_RESULT),
    PinRow('problem_enable_treat_points_from_checker_as_percent', (1, True),
           'enable_treat_points_from_checker_as_percent', (True,), NULL_RESULT),
    PinRow('problem_save_test', (1, 'tests', 1, '1 2'), 'save_test', ('tests', 1, '1 2'), NULL_RESULT),
    PinRow('problem_set_test_group', (1, 'tests', 'first', 1), 'set_test_group',
           ('tests', 'first', 1), NULL_RESULT),
    PinRow('problem_delete_test', (1, 'tests', 1), 'delete_test', ('tests', 1), NULL_RESULT),
    PinRow('problem_solutions', (1,), 'solutions', (), EMPTY_LIST_RESULT),
    PinRow('problem_files', (1,), 'files', (), FILES_RESULT),
    PinRow(None, None, 'files_resource', (), FILES_RESULT),
    PinRow(None, None, 'files_source', (), FILES_RESULT),
    PinRow(None, None, 'files_aux', (), FILES_RESULT),
    PinRow('problem_tests', (1, 'tests'), 'tests', ('tests',), EMPTY_LIST_RESULT),
    PinRow('problem_preview_tests', (1, 'tests'), 'preview_tests', ('tests',), EMPTY_LIST_RESULT),
    PinRow('problem_script', (1, 'tests'), 'script', ('tests',), NULL_RESULT),
    PinRow('problem_clear_script', (1, 'tests'), 'clear_script', ('tests',), NULL_RESULT),
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
    PinRow('problem_delete_file', (1, FileType.SOURCE, 'a.cpp'), 'delete_file',
           (FileType.SOURCE, 'a.cpp'), NULL_RESULT),
    PinRow('problem_delete_solution', (1, 'a.cpp'), 'delete_solution', ('a.cpp',), NULL_RESULT),
    PinRow('problem_save_script', (1, 'tests', 'gen 1'), 'save_script', ('tests', 'gen 1'), NULL_RESULT),
    PinRow('problem_edit_solution_extra_tags', (1, False, 'a.cpp', 'tests'), 'edit_solution_extra_tags',
           (False, 'a.cpp', 'tests'), NULL_RESULT),
    PinRow('problem_checker', (1,), 'checker', (), NULL_RESULT),
    PinRow('problem_set_checker', (1, 'check.cpp'), 'set_checker', ('check.cpp',), NULL_RESULT),
    PinRow('problem_checker_tests', (1,), 'checker_tests', (), EMPTY_LIST_RESULT),
    PinRow('problem_save_checker_test', (1, 1), 'save_checker_test', (1,), NULL_RESULT),
    PinRow('problem_delete_checker_test', (1, 1), 'delete_checker_test', (1,), NULL_RESULT),
    PinRow('problem_validator', (1,), 'validator', (), NULL_RESULT),
    PinRow('problem_set_validator', (1, 'val.cpp'), 'set_validator', ('val.cpp',), NULL_RESULT),
    PinRow('problem_extra_validators', (1,), 'extra_validators', (), NULL_RESULT),
    PinRow('problem_validator_tests', (1,), 'validator_tests', (), EMPTY_LIST_RESULT),
    PinRow('problem_save_validator_test', (1, 1), 'save_validator_test', (1,), NULL_RESULT),
    PinRow('problem_delete_validator_test', (1, 1), 'delete_validator_test', (1,), NULL_RESULT),
    PinRow('problem_interactor', (1,), 'interactor', (), NULL_RESULT),
    PinRow('problem_set_interactor', (1, 'int.cpp'), 'set_interactor', ('int.cpp',), NULL_RESULT),
    PinRow('problem_cautions', (1,), 'cautions', (), CAUTIONS_RESULT),
    PinRow('problem_issues', (1,), 'issues', (), EMPTY_LIST_RESULT),
    PinRow('problem_add_issue', (1, IssueType.BUG, 'Test 5 is invalid'), 'add_issue',
           (IssueType.BUG, 'Test 5 is invalid'), ISSUE_RESULT),
    PinRow('problem_update_issue', (1, 1234), 'update_issue', (1234,), ISSUE_RESULT),
    PinRow('problem_accesses', (1,), 'accesses', (), ACCESSES_RESULT),
    PinRow('problem_set_access', (1, 'alice', ProblemAccessType.READ), 'set_access',
           ('alice', ProblemAccessType.READ), NULL_RESULT),
    PinRow('problem_materials', (1,), 'materials', (), EMPTY_LIST_RESULT),
    PinRow('problem_set_material', (1, 'statements', MaterialPublishStrategy.NONE, [SOLUTIONS_ITEM]),
           'set_material', ('statements', MaterialPublishStrategy.NONE, [SOLUTIONS_ITEM]), NULL_RESULT),
    PinRow('problem_packages', (1,), 'packages', (), EMPTY_LIST_RESULT),
    PinRow('problem_package', (1, 2), 'package', (2,), NULL_RESULT),
    PinRow('problem_build_package', (1, True, False), 'build_package', (True, False), NULL_RESULT),
    PinRow('problem_invocations', (1,), 'invocations', (), EMPTY_LIST_RESULT),
    PinRow('problem_invocation', (1, 501), 'invocation', (501,), INVOCATION_RESULTS_RESULT),
    PinRow('problem_stresses', (1,), 'stresses', (), EMPTY_LIST_RESULT),
    PinRow('problem_save_stress', (1, 1), 'save_stress', (1,), STRESS_RESULT),
    PinRow('problem_delete_stress', (1, 1), 'delete_stress', (1,), NULL_RESULT),
    PinRow('problem_run_stresses', (1,), 'run_stresses', (), NULL_RESULT),
    PinRow('problem_cancel_stresses', (1,), 'cancel_stresses', (), NULL_RESULT),
    PinRow('problem_add_stress_countertest', (1, 1, 'tests'), 'add_stress_countertest', (1, 'tests'),
           ADDED_TEST_RESULT),
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
    The flags are optional API parameters. They have to reach Polygon under their documented
    names when set - including the False that clears a flag - and stay out of the request
    entirely when unset, so a partial update can not touch a flag it never mentioned.
    """

    FLAGS = [b'wellFormed', b'skipDuplicatedTestsValidation', b'useInteractionLogInExampleTests', b'runTwice',
             b'interactiveSecondRun']

    def test_flags_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_update_info(1, ProblemInfo(well_formed=True, skip_duplicated_tests_validation=False))
        args = dict(calls[-1]['files'])
        assert args[b'wellFormed'] == b'true'
        assert args[b'skipDuplicatedTestsValidation'] == b'false'

    def test_the_interactive_flags_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_update_info(1, ProblemInfo(interactive=True, use_interaction_log_in_example_tests=True,
                                                   run_twice=True, interactive_second_run=False))
        args = dict(calls[-1]['files'])
        assert args[b'useInteractionLogInExampleTests'] == b'true'
        assert args[b'runTwice'] == b'true'
        assert args[b'interactiveSecondRun'] == b'false'

    def test_flags_are_omitted_when_left_unset(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_update_info(1, ProblemInfo(time_limit=2000))
        args = dict(calls[-1]['files'])
        assert args[b'timeLimit'] == b'2000'
        for flag in self.FLAGS:
            assert flag not in args

    def test_switching_interactive_off_drops_the_interactive_only_flags(self, polygon, monkeypatch):
        """
        Polygon rejects any value of the two for a non-interactive problem, even False, and checks
        them against the interactive value of the same request. Sending them back from a ProblemInfo
        read while the problem was interactive would make switching it off fail.
        """
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_update_info(1, ProblemInfo(interactive=False, use_interaction_log_in_example_tests=True,
                                                   run_twice=True, interactive_second_run=False))
        args = dict(calls[-1]['files'])
        assert args[b'interactive'] == b'false'
        assert args[b'runTwice'] == b'true'
        assert b'useInteractionLogInExampleTests' not in args
        assert b'interactiveSecondRun' not in args

    def test_the_interactive_only_flags_are_sent_when_interactive_is_left_unset(self, polygon, monkeypatch):
        """Without interactive in the request, Polygon checks them against the stored value instead."""
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_update_info(1, ProblemInfo(use_interaction_log_in_example_tests=False,
                                                   interactive_second_run=True))
        args = dict(calls[-1]['files'])
        assert b'interactive' not in args
        assert args[b'useInteractionLogInExampleTests'] == b'false'
        assert args[b'interactiveSecondRun'] == b'true'

    def test_run_twice_alone_sends_nothing_else(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_update_info(1, ProblemInfo(run_twice=False))
        assert set(dict(calls[-1]['files'])) == {b'problemId', b'runTwice', b'apiKey', b'time', b'apiSig'}

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.update_info(ProblemInfo(run_twice=True, interactive_second_run=True))
        args = dict(calls[-1]['files'])
        assert args[b'runTwice'] == b'true'
        assert args[b'interactiveSecondRun'] == b'true'


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


class TestClearScript:
    """
    problem.clearScript is problem.saveScript with the source dropped: it clears the generation
    script of one testset, so the testset is the only argument the request carries.
    """

    def test_the_testset_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_clear_script(1, 'tests')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.clearScript'
        assert _sent_args(calls)[b'testset'] == b'tests'

    def test_nothing_beyond_the_testset_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_clear_script(1, 'tests')
        assert set(_sent_args(calls)) == {b'problemId', b'testset', b'apiKey', b'time', b'apiSig'}

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.clear_script('tests')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.clearScript'
        assert _sent_args(calls)[b'testset'] == b'tests'


class TestProblemAccesses:
    """problem.accesses takes no parameters of its own and returns a list of direct entries."""

    def test_only_the_problem_id_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ACCESSES_RESULT))
        polygon.problem_accesses(1)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.accesses'
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_every_entry_is_parsed_into_a_problem_access(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(ACCESSES_RESULT))
        accesses = polygon.problem_accesses(1)
        assert [type(access) for access in accesses] == [ProblemAccess] * 3
        assert [access.login for access in accesses] == ['@editors', 'alice', 'owner']
        assert [access.access_type for access in accesses] == [
            ProblemAccessType.WRITE,
            ProblemAccessType.READ,
            ProblemAccessType.OWNER,
        ]

    def test_a_problem_with_no_shared_access_parses_into_an_empty_list(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        assert polygon.problem_accesses(1) == []

    def test_the_problem_shortcut_returns_the_same_objects(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(ACCESSES_RESULT))
        accesses = problem.accesses()
        assert [access.login for access in accesses] == ['@editors', 'alice', 'owner']
        assert accesses[0].access_type == ProblemAccessType.WRITE


class TestSetAccess:
    """
    problem.setAccess takes a login and the required access state, and answers with a bare
    status and no result field.
    """

    def test_the_login_and_access_type_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_set_access(1, 'alice', ProblemAccessType.WRITE)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.setAccess'
        args = _sent_args(calls)
        assert args[b'problemId'] == b'1'
        assert args[b'login'] == b'alice'
        assert args[b'accessType'] == b'WRITE'

    def test_removing_a_direct_entry_sends_none_as_the_access_type(self, polygon, monkeypatch):
        """
        NONE is how the API spells "remove the direct entry", so it has to reach the wire as the
        bare name rather than be dropped as a Python None would be.
        """
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_set_access(1, 'alice', ProblemAccessType.NONE)
        assert _sent_args(calls)[b'accessType'] == b'NONE'

    def test_a_bare_string_access_type_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_set_access(1, 'alice', 'WRITE')

    def test_an_access_type_from_another_enum_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_set_access(1, 'alice', CautionSeverity.HARD)

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.set_access('alice', ProblemAccessType.READ)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.setAccess'
        args = _sent_args(calls)
        assert args[b'login'] == b'alice'
        assert args[b'accessType'] == b'READ'


class TestProblemNote:
    """
    problem.note and problem.saveNote read and write the problem note, which lives outside the
    working copy. Problem already carries a note attribute holding the value that came with the
    problem object (see TestProblemParsing), and an instance attribute shadows a method of the
    same name, so the fetching shortcut is view_note rather than note, and problem_view_note on
    Polygon is named to match it.
    """

    def test_only_the_problem_id_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(NOTE_RESULT))
        polygon.problem_view_note(1)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.note'
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_the_note_is_returned_as_a_string(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(NOTE_RESULT))
        assert polygon.problem_view_note(1) == 'a note'

    def test_an_unset_note_is_returned_as_an_empty_string(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body('""'))
        assert polygon.problem_view_note(1) == ''

    def test_the_note_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(NULL_RESULT))
        polygon.problem_save_note(1, 'a note')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.saveNote'
        assert _sent_args(calls)[b'note'] == b'a note'

    def test_an_empty_note_is_sent_rather_than_dropped(self, polygon, monkeypatch):
        """An empty note is how a caller clears it, so it has to reach the API."""
        calls = _install_fake_post(monkeypatch, text=_ok_body(NULL_RESULT))
        polygon.problem_save_note(1, '')
        assert _sent_args(calls)[b'note'] == b''

    def test_the_view_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(NOTE_RESULT))
        assert problem.view_note() == 'a note'
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.note'

    def test_the_save_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(NULL_RESULT))
        problem.save_note('a note')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.saveNote'
        assert _sent_args(calls)[b'note'] == b'a note'


class TestCommitChanges:
    """
    problem.commitChanges answers with a CommitResult. A commit with nothing to commit is not a
    failure: the status stays OK and the result says committed=false, so that is the flag a
    caller has to look at. A failed commit answers FAILED and raises like any other method.
    """

    def test_the_flags_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(COMMIT_RESULT))
        polygon.problem_commit_changes(1, minor_changes=True, message='Fix the checker')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.commitChanges'
        args = _sent_args(calls)
        assert args[b'minorChanges'] == b'true'
        assert args[b'message'] == b'Fix the checker'

    def test_only_the_problem_id_is_sent_when_left_unset(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(COMMIT_RESULT))
        polygon.problem_commit_changes(1)
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_the_result_is_parsed_into_a_commit_result(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(COMMIT_RESULT))
        result = polygon.problem_commit_changes(1)
        assert isinstance(result, CommitResult)
        assert result.committed is True
        assert result.conflict_occurred is False
        assert result.message == 'Changes committed'

    def test_nothing_to_commit_is_returned_rather_than_raised(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(
            '{"committed": false, "conflictOccurred": false, "message": "No changes"}'))
        result = polygon.problem_commit_changes(1)
        assert result.committed is False
        assert result.message == 'No changes'

    def test_a_failed_commit_raises_with_the_comment(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text='{"status": "FAILED", "comment": "Working copy has conflicts"}')
        with pytest.raises(PolygonRequestFailedException) as excinfo:
            polygon.problem_commit_changes(1)
        assert excinfo.value.comment == 'Working copy has conflicts'

    def test_the_problem_shortcut_returns_the_same_object(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(COMMIT_RESULT))
        result = problem.commit_changes(minor_changes=False, message='Fix the checker')
        assert isinstance(result, CommitResult)
        assert result.committed is True
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.commitChanges'
        args = _sent_args(calls)
        assert args[b'minorChanges'] == b'false'
        assert args[b'message'] == b'Fix the checker'


class TestDeleteSolution:
    """
    problem.deleteSolution takes the exact solution name and answers FAILED when there is no
    such solution.
    """

    def test_the_name_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_solution(1, 'wa.cpp')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteSolution'
        assert _sent_args(calls)[b'name'] == b'wa.cpp'

    def test_nothing_beyond_the_name_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_solution(1, 'wa.cpp')
        assert set(_sent_args(calls)) == {b'problemId', b'name', b'apiKey', b'time', b'apiSig'}

    def test_a_missing_solution_raises_with_the_comment(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text='{"status": "FAILED", "comment": "Solution not found"}')
        with pytest.raises(PolygonRequestFailedException) as excinfo:
            polygon.problem_delete_solution(1, 'wa.cpp')
        assert excinfo.value.comment == 'Solution not found'

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.delete_solution('wa.cpp')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteSolution'
        assert _sent_args(calls)[b'name'] == b'wa.cpp'


class TestDeleteFile:
    """
    problem.deleteFile takes the file type and the exact file name, the same pair that
    problem.viewFile and problem.saveFile take.
    """

    @pytest.mark.parametrize('file_type, sent_type', [
        (FileType.RESOURCE, b'resource'),
        (FileType.SOURCE, b'source'),
        (FileType.AUX, b'aux'),
    ])
    def test_the_type_and_name_are_sent_under_their_documented_names(
            self, polygon, monkeypatch, file_type, sent_type):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_file(1, file_type, 'gen.cpp')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteFile'
        args = _sent_args(calls)
        assert args[b'type'] == sent_type
        assert args[b'name'] == b'gen.cpp'

    def test_nothing_beyond_the_type_and_name_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_file(1, FileType.SOURCE, 'gen.cpp')
        assert set(_sent_args(calls)) == {b'problemId', b'type', b'name', b'apiKey', b'time', b'apiSig'}

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.delete_file(FileType.AUX, 'notes.txt')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteFile'
        args = _sent_args(calls)
        assert args[b'type'] == b'aux'
        assert args[b'name'] == b'notes.txt'


class TestDeleteStatement:
    """
    problem.deleteStatement takes the language exactly as problem.statements returns it and
    answers FAILED when there is no statement in that language.
    """

    def test_the_language_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_statement(1, 'russian')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteStatement'
        assert _sent_args(calls)[b'lang'] == b'russian'

    def test_nothing_beyond_the_language_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_statement(1, 'russian')
        assert set(_sent_args(calls)) == {b'problemId', b'lang', b'apiKey', b'time', b'apiSig'}

    def test_a_missing_statement_raises_with_the_comment(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text='{"status": "FAILED", "comment": "Statement not found"}')
        with pytest.raises(PolygonRequestFailedException) as excinfo:
            polygon.problem_delete_statement(1, 'russian')
        assert excinfo.value.comment == 'Statement not found'

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.delete_statement('russian')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteStatement'
        assert _sent_args(calls)[b'lang'] == b'russian'


class TestDeleteStatementResource:
    """problem.deleteStatementResource takes the exact resource name as problem.statementResources returns it."""

    def test_the_name_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_statement_resource(1, 'picture.png')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteStatementResource'
        assert _sent_args(calls)[b'name'] == b'picture.png'

    def test_nothing_beyond_the_name_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_statement_resource(1, 'picture.png')
        assert set(_sent_args(calls)) == {b'problemId', b'name', b'apiKey', b'time', b'apiSig'}

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.delete_statement_resource('picture.png')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteStatementResource'
        assert _sent_args(calls)[b'name'] == b'picture.png'


class TestDeleteValidatorTest:
    """
    problem.deleteValidatorTest takes only the index of the validator test: unlike
    problem.saveValidatorTest it has no testset or group to narrow it down, as validator tests are
    numbered across the problem.
    """

    def test_the_index_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_validator_test(1, 3)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteValidatorTest'
        assert _sent_args(calls)[b'testIndex'] == b'3'

    def test_nothing_beyond_the_index_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_validator_test(1, 3)
        assert set(_sent_args(calls)) == {b'problemId', b'testIndex', b'apiKey', b'time', b'apiSig'}

    def test_a_missing_test_raises_with_the_comment(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text='{"status": "FAILED", "comment": "Validator test not found"}')
        with pytest.raises(PolygonRequestFailedException) as excinfo:
            polygon.problem_delete_validator_test(1, 3)
        assert excinfo.value.comment == 'Validator test not found'

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.delete_validator_test(3)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteValidatorTest'
        assert _sent_args(calls)[b'testIndex'] == b'3'


class TestDeleteCheckerTest:
    """problem.deleteCheckerTest takes only the index of the checker test."""

    def test_the_index_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_checker_test(1, 3)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteCheckerTest'
        assert _sent_args(calls)[b'testIndex'] == b'3'

    def test_nothing_beyond_the_index_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_checker_test(1, 3)
        assert set(_sent_args(calls)) == {b'problemId', b'testIndex', b'apiKey', b'time', b'apiSig'}

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.delete_checker_test(3)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteCheckerTest'
        assert _sent_args(calls)[b'testIndex'] == b'3'


DELETE_TESTS_FAILED_BODY = (
    '{"status": "FAILED", "comment": "Some tests can not be deleted.", '
    '"result": {"failures": [{"index": 7, "reason": "NOT_FOUND", "message": "Test 7 not found"}]}}'
)


class TestDeleteTest:
    """
    problem.deleteTest deletes one or more tests of a testset, given as repeated testIndex
    arguments or as a comma-separated testIndices list, like problem.setTestGroup. It is the one
    method whose FAILED answer carries a result: a DeleteTestsResult with a failure for every test
    that can not be deleted.
    """

    def test_the_testset_and_index_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_test(1, 'tests', 3)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteTest'
        args = _sent_args(calls)
        assert args[b'testset'] == b'tests'
        assert args[b'testIndex'] == b'3'
        assert b'testIndices' not in args

    def test_a_list_of_indices_is_sent_as_repeated_test_index_arguments(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_test(1, 'tests', test_index=[3, 4])
        assert [value for key, value in calls[-1]['files'] if key == b'testIndex'] == [b'3', b'4']

    def test_test_indices_are_joined_with_commas(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_test(1, 'tests', test_indices=[3, 4, 5])
        args = _sent_args(calls)
        assert args[b'testIndices'] == b'3,4,5'
        assert b'testIndex' not in args

    def test_failures_are_raised_with_the_parsed_result(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=DELETE_TESTS_FAILED_BODY)
        with pytest.raises(DeleteTestsFailedException) as excinfo:
            polygon.problem_delete_test(1, 'tests', test_indices=[6, 7])
        assert excinfo.value.comment == 'Some tests can not be deleted.'
        assert isinstance(excinfo.value.result, DeleteTestsResult)
        failure, = excinfo.value.result.failures
        assert failure.index == 7
        assert failure.reason == api.TestDeletionFailureReason.NOT_FOUND
        assert failure.message == 'Test 7 not found'

    def test_the_failure_is_still_a_polygon_request_failure(self, polygon, monkeypatch):
        """Callers catching every FAILED answer keep catching this one."""
        _install_fake_post(monkeypatch, text=DELETE_TESTS_FAILED_BODY)
        with pytest.raises(PolygonRequestFailedException):
            polygon.problem_delete_test(1, 'tests', 7)

    def test_a_failure_without_a_result_raises_the_plain_exception(self, polygon, monkeypatch):
        """A request rejected before any test is checked, e.g. for a bad pin, has no failures to list."""
        _install_fake_post(monkeypatch, text='{"status": "FAILED", "comment": "Invalid pin"}')
        with pytest.raises(PolygonRequestFailedException) as excinfo:
            polygon.problem_delete_test(1, 'tests', 7)
        assert type(excinfo.value) is PolygonRequestFailedException
        assert excinfo.value.comment == 'Invalid pin'

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.delete_test('tests', test_indices=[3, 4])
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.deleteTest'
        args = _sent_args(calls)
        assert args[b'testset'] == b'tests'
        assert args[b'testIndices'] == b'3,4'


class TestProblemIssues:
    """problem.issues takes no parameters of its own and returns every issue with its comments."""

    def test_only_the_problem_id_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        polygon.problem_issues(1)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.issues'
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_every_issue_is_parsed_into_an_issue(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body('[%s, %s]' % (ISSUE_RESULT, ISSUE_RESULT)))
        issues = polygon.problem_issues(1)
        assert [type(issue) for issue in issues] == [Issue] * 2
        assert issues[0].id == 1234
        assert issues[0].status == IssueStatus.OPENED

    def test_a_problem_without_issues_parses_into_an_empty_list(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        assert polygon.problem_issues(1) == []

    def test_the_problem_shortcut_returns_the_same_objects(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body('[%s]' % ISSUE_RESULT))
        issue, = problem.issues()
        assert issue.id == 1234


class TestAddIssue:
    """problem.addIssue takes the issue type, the Markdown content and an optional assignee."""

    def test_the_arguments_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        polygon.problem_add_issue(1, IssueType.BUG, 'Test 5 is invalid', assignee='bob')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.addIssue'
        args = _sent_args(calls)
        assert args[b'type'] == b'BUG'
        assert args[b'content'] == b'Test 5 is invalid'
        assert args[b'assignee'] == b'bob'

    def test_the_assignee_is_omitted_when_left_unset(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        polygon.problem_add_issue(1, IssueType.DISCUSSION, 'Should n be up to 10^9?')
        assert set(_sent_args(calls)) == {b'problemId', b'type', b'content', b'apiKey', b'time', b'apiSig'}

    def test_the_created_issue_is_returned(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        issue = polygon.problem_add_issue(1, IssueType.BUG, 'Test 5 is invalid')
        assert isinstance(issue, Issue)
        assert issue.id == 1234
        assert issue.comments == []

    def test_a_bare_string_type_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_add_issue(1, 'BUG', 'Test 5 is invalid')

    def test_a_type_from_another_enum_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_add_issue(1, IssueStatus.OPENED, 'Test 5 is invalid')

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        issue = problem.add_issue(IssueType.ENHANCEMENT, 'Add a test with n = 1', assignee='bob')
        assert issue.id == 1234
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.addIssue'
        args = _sent_args(calls)
        assert args[b'type'] == b'ENHANCEMENT'
        assert args[b'content'] == b'Add a test with n = 1'
        assert args[b'assignee'] == b'bob'


class TestUpdateIssue:
    """
    problem.updateIssue adds a comment to an issue and/or changes its status, type and assignee.
    Every change is optional, and a parameter that is not passed is not sent, so it stays as it is.
    """

    def test_the_arguments_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        polygon.problem_update_issue(1, 1234, comment='Fixed in revision 12', status=IssueStatus.CLOSED,
                                     issue_type=IssueType.ENHANCEMENT, assignee='carol')
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.updateIssue'
        args = _sent_args(calls)
        assert args[b'issueId'] == b'1234'
        assert args[b'comment'] == b'Fixed in revision 12'
        assert args[b'status'] == b'CLOSED'
        assert args[b'type'] == b'ENHANCEMENT'
        assert args[b'assignee'] == b'carol'

    def test_a_comment_alone_sends_nothing_else(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        polygon.problem_update_issue(1, 1234, comment='Looking into it')
        assert set(_sent_args(calls)) == {b'problemId', b'issueId', b'comment', b'apiKey', b'time', b'apiSig'}

    def test_an_empty_assignee_is_sent_rather_than_dropped(self, polygon, monkeypatch):
        """The docs: an empty assignee removes it, while an absent one leaves it unchanged."""
        calls = _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        polygon.problem_update_issue(1, 1234, assignee='')
        assert _sent_args(calls)[b'assignee'] == b''

    def test_the_updated_issue_is_returned(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        issue = polygon.problem_update_issue(1, 1234, comment='Looking into it')
        assert isinstance(issue, Issue)
        assert issue.id == 1234

    def test_a_bare_string_status_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_update_issue(1, 1234, status='CLOSED')

    def test_a_bare_string_type_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_update_issue(1, 1234, issue_type='BUG')

    def test_a_status_and_a_type_must_not_be_swapped(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_update_issue(1, 1234, status=IssueType.BUG)
        with pytest.raises(ValueError):
            polygon.problem_update_issue(1, 1234, issue_type=IssueStatus.CLOSED)

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ISSUE_RESULT))
        issue = problem.update_issue(1234, comment='Reopening', status=IssueStatus.REOPENED,
                                     issue_type=IssueType.BUG, assignee='')
        assert issue.id == 1234
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.updateIssue'
        args = _sent_args(calls)
        assert args[b'issueId'] == b'1234'
        assert args[b'comment'] == b'Reopening'
        assert args[b'status'] == b'REOPENED'
        assert args[b'type'] == b'BUG'
        assert args[b'assignee'] == b''


class TestEnableTreatPointsFromCheckerAsPercent:
    """
    problem.enableTreatPointsFromCheckerAsPercent is problem.enablePoints for the checker points:
    a single boolean, sent as the lowercase true or false the API expects.
    """

    URL = 'https://example.invalid/api/problem.enableTreatPointsFromCheckerAsPercent'

    @pytest.mark.parametrize('enable, sent', [(True, b'true'), (False, b'false')])
    def test_enable_is_sent_as_a_lowercase_boolean(self, polygon, monkeypatch, enable, sent):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_enable_treat_points_from_checker_as_percent(1, enable)
        assert calls[-1]['url'] == self.URL
        assert _sent_args(calls)[b'enable'] == sent

    def test_nothing_beyond_enable_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_enable_treat_points_from_checker_as_percent(1, True)
        assert set(_sent_args(calls)) == {b'problemId', b'enable', b'apiKey', b'time', b'apiSig'}

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.enable_treat_points_from_checker_as_percent(False)
        assert calls[-1]['url'] == self.URL
        assert _sent_args(calls)[b'enable'] == b'false'


GENERATED_PREVIEW_JSON = {
    'id': 77,
    'session': 'f3a9c1',
    'creationTime': 'Nov 4, 2026 1:19:03 PM',
    'updateTime': 'Nov 4, 2026 1:19:05 PM',
    'problemId': 1,
    'testset': 'tests',
    'testIndex': 3,
    'description': 'max test',
    'useInStatements': True,
    'input': '3\n1 2 3\n',
    'inputSha1': 'a' * 40,
    'answer': '6\n',
    'changeAfterLastGenerate': False,
    'testOverviewLog': 'Generated by gen 3',
}

PENDING_PREVIEW_JSON = {
    'session': 'f3a9c1',
    'problemId': 1,
    'testset': 'tests',
    'testIndex': 4,
    'useInStatements': False,
    'changeAfterLastGenerate': True,
}


class TestTestPreviewParsing:
    def test_a_generated_preview_keeps_every_field(self):
        preview = api.TestPreview.from_json(GENERATED_PREVIEW_JSON)
        assert preview.id == 77
        assert preview.session == 'f3a9c1'
        assert preview.creation_time == 'Nov 4, 2026 1:19:03 PM'
        assert preview.update_time == 'Nov 4, 2026 1:19:05 PM'
        assert preview.problem_id == 1
        assert preview.testset == 'tests'
        assert preview.test_index == 3
        assert preview.description == 'max test'
        assert preview.use_in_statements is True
        assert preview.input == '3\n1 2 3\n'
        assert preview.input_sha1 == 'a' * 40
        assert preview.answer == '6\n'
        assert preview.change_after_last_generate is False
        assert preview.test_overview_log == 'Generated by gen 3'

    def test_a_pending_preview_parses_with_the_absent_fields_as_none(self):
        """The docs: a preview still being generated comes back without input and answer."""
        preview = api.TestPreview.from_json(PENDING_PREVIEW_JSON)
        assert preview.test_index == 4
        assert preview.change_after_last_generate is True
        assert preview.id is None
        assert preview.creation_time is None
        assert preview.update_time is None
        assert preview.description is None
        assert preview.input is None
        assert preview.input_sha1 is None
        assert preview.answer is None
        assert preview.test_overview_log is None


class TestPreviewTests:
    """problem.previewTests takes a testset and returns a preview for each of its tests."""

    URL = 'https://example.invalid/api/problem.previewTests'

    def test_the_testset_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        polygon.problem_preview_tests(1, 'tests')
        assert calls[-1]['url'] == self.URL
        assert set(_sent_args(calls)) == {b'problemId', b'testset', b'apiKey', b'time', b'apiSig'}
        assert _sent_args(calls)[b'testset'] == b'tests'

    def test_every_preview_is_parsed_into_a_test_preview(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(json.dumps([GENERATED_PREVIEW_JSON, PENDING_PREVIEW_JSON])))
        previews = polygon.problem_preview_tests(1, 'tests')
        assert [type(preview) for preview in previews] == [api.TestPreview] * 2
        assert [preview.test_index for preview in previews] == [3, 4]
        assert [preview.answer for preview in previews] == ['6\n', None]

    def test_a_testset_without_tests_parses_into_an_empty_list(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        assert polygon.problem_preview_tests(1, 'tests') == []

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(json.dumps([GENERATED_PREVIEW_JSON])))
        preview, = problem.preview_tests('samples')
        assert preview.test_index == 3
        assert calls[-1]['url'] == self.URL
        assert _sent_args(calls)[b'testset'] == b'samples'


MATERIAL_JSON = {
    'name': 'statements',
    'publishStrategy': 'WITH_STATEMENT',
    'items': [
        {'type': 'TEST_INPUTS', 'tests': [{'testset': 'tests', 'index': 1, 'all': False, 'asInput': False},
                                          {'testset': 'samples', 'all': True, 'asInput': False}]},
        {'type': 'TEST_ANSWERS', 'tests': [{'testset': 'tests', 'all': False, 'asInput': True}]},
        {'type': 'SOLUTIONS', 'names': ['main.cpp', 'slow.py']},
    ],
}


class TestMaterialParsing:
    def test_a_material_keeps_its_name_strategy_and_items(self):
        material = Material.from_json(MATERIAL_JSON)
        assert material.name == 'statements'
        assert material.publish_strategy == MaterialPublishStrategy.WITH_STATEMENT
        assert [item.type for item in material.items] == [
            MaterialItemType.TEST_INPUTS,
            MaterialItemType.TEST_ANSWERS,
            MaterialItemType.SOLUTIONS,
        ]

    @pytest.mark.parametrize('strategy', list(MaterialPublishStrategy))
    def test_every_publish_strategy_is_parsed(self, strategy):
        material = Material.from_json(dict(MATERIAL_JSON, publishStrategy=strategy.name))
        assert material.publish_strategy == strategy

    def test_a_material_without_items_parses_into_an_empty_list(self):
        assert Material.from_json(dict(MATERIAL_JSON, items=[])).items == []


class TestMaterialItemParsing:
    def test_a_test_item_has_tests_and_no_names(self):
        item = MaterialItem.from_json(MATERIAL_JSON['items'][0])
        assert item.type == MaterialItemType.TEST_INPUTS
        assert [type(test) for test in item.tests] == [MaterialTest] * 2
        assert item.names is None

    def test_a_file_item_has_names_and_no_tests(self):
        item = MaterialItem.from_json(MATERIAL_JSON['items'][2])
        assert item.type == MaterialItemType.SOLUTIONS
        assert item.names == ['main.cpp', 'slow.py']
        assert item.tests is None

    @pytest.mark.parametrize('item_type', list(MaterialItemType))
    def test_every_item_type_is_parsed(self, item_type):
        assert MaterialItem.from_json({'type': item_type.name, 'names': []}).type == item_type

    def test_an_empty_legacy_list_is_kept_empty(self):
        """The docs: a list may be empty for materials created by the web editor."""
        assert MaterialItem.from_json({'type': 'AUX_FILES', 'names': []}).names == []


class TestMaterialTestParsing:
    def test_a_single_test_selection(self):
        test = MaterialTest.from_json({'testset': 'tests', 'index': 1, 'all': False, 'asInput': False})
        assert (test.testset, test.index, test.all, test.as_input) == ('tests', 1, False, False)

    def test_an_all_tests_selection_has_no_index(self):
        test = MaterialTest.from_json({'testset': 'samples', 'all': True, 'asInput': False})
        assert (test.index, test.all, test.as_input) == (None, True, False)

    def test_an_as_input_selection(self):
        test = MaterialTest.from_json({'testset': 'tests', 'all': False, 'asInput': True})
        assert (test.index, test.all, test.as_input) == (None, False, True)

    def test_omitted_flags_default_to_false(self):
        test = MaterialTest.from_json({'testset': 'tests', 'index': 3})
        assert (test.all, test.as_input) == (False, False)

    def test_a_null_index_parses_as_none(self):
        assert MaterialTest.from_json({'testset': 'tests', 'index': None, 'all': True}).index is None


class TestMaterialSerialization:
    def test_a_selection_omits_the_fields_left_at_their_defaults(self):
        assert MaterialTest('tests', index=2).to_json() == {'testset': 'tests', 'index': 2}
        assert MaterialTest('tests', all=True).to_json() == {'testset': 'tests', 'all': True}
        assert MaterialTest('tests', as_input=True).to_json() == {'testset': 'tests', 'asInput': True}

    def test_an_item_sends_only_the_list_that_is_set(self):
        assert MaterialItem(MaterialItemType.AUX_FILES, names=['a.txt']).to_json() == {
            'type': 'AUX_FILES', 'names': ['a.txt'],
        }
        assert MaterialItem(MaterialItemType.TEST_INPUTS, tests=[MaterialTest('tests', all=True)]).to_json() == {
            'type': 'TEST_INPUTS', 'tests': [{'testset': 'tests', 'all': True}],
        }

    def test_names_given_as_a_tuple_are_sent_as_a_list(self):
        assert MaterialItem(MaterialItemType.SOLUTIONS, names=('a.cpp',)).to_json()['names'] == ['a.cpp']

    def test_a_parsed_material_serializes_back_to_an_equivalent_selection(self):
        """A material read through problem.materials can be passed back to problem.setMaterial."""
        items = Material.from_json(MATERIAL_JSON).items
        assert [item.to_json() for item in items] == [
            {'type': 'TEST_INPUTS', 'tests': [{'testset': 'tests', 'index': 1},
                                              {'testset': 'samples', 'all': True}]},
            {'type': 'TEST_ANSWERS', 'tests': [{'testset': 'tests', 'asInput': True}]},
            {'type': 'SOLUTIONS', 'names': ['main.cpp', 'slow.py']},
        ]


class TestMaterials:
    """problem.materials takes no parameters of its own and returns every material of the working copy."""

    def test_only_the_problem_id_is_sent(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        polygon.problem_materials(1)
        assert calls[-1]['url'] == 'https://example.invalid/api/problem.materials'
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_every_material_is_parsed_into_a_material(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(json.dumps([MATERIAL_JSON, dict(MATERIAL_JSON, name='x')])))
        materials = polygon.problem_materials(1)
        assert [type(material) for material in materials] == [Material] * 2
        assert [material.name for material in materials] == ['statements', 'x']

    def test_a_problem_without_materials_parses_into_an_empty_list(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        assert polygon.problem_materials(1) == []

    def test_the_problem_shortcut_returns_the_same_objects(self, problem, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(json.dumps([MATERIAL_JSON])))
        material, = problem.materials()
        assert material.name == 'statements'


class TestSetMaterial:
    """
    problem.setMaterial saves a whole material (publish strategy and items, optionally renaming it)
    or removes one, and answers with a bare status and no result field.
    """

    URL = 'https://example.invalid/api/problem.setMaterial'
    ITEMS = [
        MaterialItem(MaterialItemType.TEST_INPUTS, tests=[MaterialTest('tests', index=1)]),
        MaterialItem(MaterialItemType.TEST_ANSWERS, tests=[MaterialTest('tests', as_input=True)]),
        MaterialItem(MaterialItemType.SOLUTIONS, names=['main.cpp']),
    ]

    def test_a_save_sends_the_strategy_and_the_items_as_compact_json(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text='{"status": "OK"}')
        result = polygon.problem_set_material(1, 'statements', MaterialPublishStrategy.WITH_STATEMENT, self.ITEMS)
        assert result is None
        assert calls[-1]['url'] == self.URL
        args = _sent_args(calls)
        assert set(args) == {b'problemId', b'name', b'publishStrategy', b'items', b'apiKey', b'time', b'apiSig'}
        assert args[b'name'] == b'statements'
        assert args[b'publishStrategy'] == b'WITH_STATEMENT'
        assert args[b'items'] == (
            b'[{"type":"TEST_INPUTS","tests":[{"testset":"tests","index":1}]},'
            b'{"type":"TEST_ANSWERS","tests":[{"testset":"tests","asInput":true}]},'
            b'{"type":"SOLUTIONS","names":["main.cpp"]}]'
        )

    def test_a_rename_sends_the_original_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text='{"status": "OK"}')
        polygon.problem_set_material(1, 'new', MaterialPublishStrategy.NONE, self.ITEMS, original_name='old')
        args = _sent_args(calls)
        assert args[b'name'] == b'new'
        assert args[b'originalName'] == b'old'

    def test_items_may_be_any_iterable(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text='{"status": "OK"}')
        polygon.problem_set_material(1, 'statements', MaterialPublishStrategy.NONE, iter(self.ITEMS[2:]))
        assert _sent_args(calls)[b'items'] == b'[{"type":"SOLUTIONS","names":["main.cpp"]}]'

    def test_a_removal_sends_only_the_name_and_the_flag(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text='{"status": "OK"}')
        polygon.problem_set_material(1, 'statements', remove=True)
        args = _sent_args(calls)
        assert set(args) == {b'problemId', b'name', b'remove', b'apiKey', b'time', b'apiSig'}
        assert args[b'remove'] == b'true'

    def test_remove_false_is_a_save(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text='{"status": "OK"}')
        polygon.problem_set_material(1, 'statements', MaterialPublishStrategy.NONE, self.ITEMS, remove=False)
        assert _sent_args(calls)[b'remove'] == b'false'

    @pytest.mark.parametrize('kwargs', [
        {'items': ITEMS},
        {'publish_strategy': MaterialPublishStrategy.NONE},
        {},
    ], ids=['no-strategy', 'no-items', 'neither'])
    def test_a_save_needs_both_the_strategy_and_the_items(self, polygon, kwargs):
        with pytest.raises(ValueError):
            polygon.problem_set_material(1, 'statements', **kwargs)

    @pytest.mark.parametrize('kwargs', [
        {'publish_strategy': MaterialPublishStrategy.NONE},
        {'items': ITEMS},
        {'original_name': 'old'},
    ], ids=['strategy', 'items', 'original-name'])
    def test_a_removal_takes_nothing_else(self, polygon, kwargs):
        with pytest.raises(ValueError):
            polygon.problem_set_material(1, 'statements', remove=True, **kwargs)

    def test_a_bare_string_strategy_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_set_material(1, 'statements', 'NONE', self.ITEMS)

    def test_an_item_that_is_not_a_material_item_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_set_material(1, 'statements', MaterialPublishStrategy.NONE,
                                         [{'type': 'SOLUTIONS', 'names': ['main.cpp']}])

    def test_an_item_with_a_bare_string_type_is_rejected(self, polygon):
        with pytest.raises(ValueError):
            polygon.problem_set_material(1, 'statements', MaterialPublishStrategy.NONE,
                                         [MaterialItem('SOLUTIONS', names=['main.cpp'])])

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text='{"status": "OK"}')
        problem.set_material('new', MaterialPublishStrategy.WITH_TUTORIAL, self.ITEMS[2:], original_name='old')
        assert calls[-1]['url'] == self.URL
        args = _sent_args(calls)
        assert args[b'name'] == b'new'
        assert args[b'originalName'] == b'old'
        assert args[b'publishStrategy'] == b'WITH_TUTORIAL'
        assert args[b'items'] == b'[{"type":"SOLUTIONS","names":["main.cpp"]}]'


INVOCATION_JSON = {
    'id': 501,
    'description': 'Package #12 verification',
    'testset': 'tests',
    'status': 'FINISHED',
    'creationTimeSeconds': 1790000000,
    'packageId': 12,
    'violateTag': True,
    'solutions': ['main.cpp', 'wa.cpp'],
    'tests': [1, 2],
}

RUN_JSON = {
    'id': 9001,
    'solution': 'wa.cpp',
    'test': 2,
    'verdict': 'WA',
    'timeMillis': 15,
    'memoryBytes': 2097152,
    'points': 0.5,
    'comment': 'wrong answer expected 13, found 12',
    'violateTag': False,
}


class TestInvocationParsing:
    def test_an_invocation_keeps_every_field(self):
        invocation = Invocation.from_json(INVOCATION_JSON)
        assert invocation.id == 501
        assert invocation.description == 'Package #12 verification'
        assert invocation.testset == 'tests'
        assert invocation.status == InvocationStatus.FINISHED
        assert invocation.creation_time_seconds == 1790000000
        assert invocation.package_id == 12
        assert invocation.violate_tag is True
        assert invocation.solutions == ['main.cpp', 'wa.cpp']
        assert invocation.tests == [1, 2]

    def test_an_invocation_from_the_invocations_page_has_no_package(self):
        json_without_package = {key: value for key, value in INVOCATION_JSON.items() if key != 'packageId'}
        assert Invocation.from_json(json_without_package).package_id is None

    @pytest.mark.parametrize('status', list(InvocationStatus))
    def test_every_status_is_parsed(self, status):
        assert Invocation.from_json(dict(INVOCATION_JSON, status=status.name)).status == status


class TestSolutionTagsParsing:
    def test_the_tag_and_the_extra_tags_are_parsed_into_solution_tags(self):
        tags = SolutionTags.from_json({
            'name': 'slow.cpp',
            'tag': 'TL',
            'testsetTags': {'samples': 'OK'},
            'groupTags': {'subtask1': 'OK', 'subtask2': 'TO'},
        })
        assert tags.name == 'slow.cpp'
        assert tags.tag == SolutionTag.TL
        assert tags.testset_tags == {'samples': SolutionTag.OK}
        assert tags.group_tags == {'subtask1': SolutionTag.OK, 'subtask2': SolutionTag.TO}

    def test_absent_fields_read_as_no_tag_and_no_extra_tags(self):
        """The docs: tag may be absent, and the mappings are left out when there are none."""
        tags = SolutionTags.from_json({'name': 'main.cpp'})
        assert tags.tag is None
        assert tags.testset_tags == {}
        assert tags.group_tags == {}

    def test_construction_without_extra_tags_gives_empty_mappings(self):
        tags = SolutionTags('main.cpp', SolutionTag.MA)
        assert tags.testset_tags == {}
        assert tags.group_tags == {}
        assert SolutionTags('a.cpp').testset_tags is not tags.testset_tags


class TestInvocationRunParsing:
    def test_a_run_keeps_every_field(self):
        run = InvocationRun.from_json(RUN_JSON)
        assert run.id == 9001
        assert run.solution == 'wa.cpp'
        assert run.test == 2
        assert run.verdict == InvocationRunVerdict.WA
        assert run.time_millis == 15
        assert run.memory_bytes == 2097152
        assert run.points == 0.5
        assert run.comment == 'wrong answer expected 13, found 12'
        assert run.violate_tag is False

    def test_a_waiting_run_has_no_measurements(self):
        """The docs: time and memory are present only for OK/WA/PE/TL/ML/IL/RE."""
        run = InvocationRun.from_json({'id': 9002, 'test': 1, 'verdict': 'NO', 'violateTag': False})
        assert run.verdict == InvocationRunVerdict.NO
        assert run.solution is None
        assert run.time_millis is None
        assert run.memory_bytes is None
        assert run.points is None
        assert run.comment is None

    @pytest.mark.parametrize('points', [3, '2.5'])
    def test_points_are_read_as_a_float(self, points):
        assert InvocationRun.from_json(dict(RUN_JSON, points=points)).points == float(points)

    @pytest.mark.parametrize('verdict', list(InvocationRunVerdict))
    def test_every_verdict_is_parsed(self, verdict):
        assert InvocationRun.from_json(dict(RUN_JSON, verdict=verdict.name)).verdict == verdict


class TestInvocationResultsParsing:
    def test_the_invocation_tags_and_runs_are_parsed(self):
        results = InvocationResults.from_json({
            'invocation': INVOCATION_JSON,
            'solutionTags': [{'name': 'main.cpp', 'tag': 'MA'}, {'name': 'wa.cpp', 'tag': 'WA'}],
            'runs': [dict(RUN_JSON, id=1, test=1, verdict='OK'), RUN_JSON],
        })
        assert isinstance(results.invocation, Invocation)
        assert results.invocation.id == 501
        assert [tags.tag for tags in results.solution_tags] == [SolutionTag.MA, SolutionTag.WA]
        assert [run.id for run in results.runs] == [1, 9001]

    def test_an_invocation_without_runs_yet(self):
        results = InvocationResults.from_json(json.loads(INVOCATION_RESULTS_RESULT))
        assert results.invocation.status == InvocationStatus.PENDING
        assert results.solution_tags == []
        assert results.runs == []


class TestInvocations:
    """problem.invocations takes an optional package id and returns the invocations, the newest first."""

    URL = 'https://example.invalid/api/problem.invocations'

    def test_only_the_problem_id_is_sent_without_a_package(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        polygon.problem_invocations(1)
        assert calls[-1]['url'] == self.URL
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_the_package_id_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        polygon.problem_invocations(1, package_id=12)
        assert _sent_args(calls)[b'packageId'] == b'12'

    def test_every_invocation_is_parsed_into_an_invocation(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(json.dumps([INVOCATION_JSON, dict(INVOCATION_JSON, id=500)])))
        invocations = polygon.problem_invocations(1)
        assert [type(invocation) for invocation in invocations] == [Invocation] * 2
        assert [invocation.id for invocation in invocations] == [501, 500]

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(json.dumps([INVOCATION_JSON])))
        invocation, = problem.invocations(package_id=12)
        assert invocation.id == 501
        assert calls[-1]['url'] == self.URL
        assert _sent_args(calls)[b'packageId'] == b'12'


class TestInvocation:
    """problem.invocation takes an invocation id and returns the invocation with its stored runs."""

    URL = 'https://example.invalid/api/problem.invocation'

    def test_the_invocation_id_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(INVOCATION_RESULTS_RESULT))
        polygon.problem_invocation(1, 501)
        assert calls[-1]['url'] == self.URL
        assert set(_sent_args(calls)) == {b'problemId', b'invocationId', b'apiKey', b'time', b'apiSig'}
        assert _sent_args(calls)[b'invocationId'] == b'501'

    def test_the_result_is_parsed_into_invocation_results(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(INVOCATION_RESULTS_RESULT))
        results = polygon.problem_invocation(1, 501)
        assert isinstance(results, InvocationResults)
        assert results.invocation.id == 501

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(INVOCATION_RESULTS_RESULT))
        results = problem.invocation(501)
        assert results.invocation.id == 501
        assert calls[-1]['url'] == self.URL
        assert _sent_args(calls)[b'invocationId'] == b'501'


REPORT_JSON = {
    'solutionName': 'wa.cpp',
    'verdict': 'WRONG_ANSWER',
    'consumedTime': 15,
    'consumedMemory': 2097152,
    'output': '12',
    'outputTruncated': False,
    'answer': '13',
    'answerTruncated': False,
    'comment': 'wrong answer expected 13, found 12',
}

COUNTERTEST_JSON = {
    'input': '57\n3 1 4 1 5 ...',
    'inputTruncated': True,
    'scriptLine': 'gen 10 57 abacaba 2f8a91',
    'reports': [REPORT_JSON],
}

FINISHED_RUN_JSON = {
    'status': 'FINISHED',
    'verdict': 'OK',
    'judgedTestCount': 412,
    'maxConsumedTime': 31,
    'maxConsumedMemory': 4194304,
    'countertest': COUNTERTEST_JSON,
}

STRESS_JSON = {
    'index': 1,
    'scriptPattern': 'gen 10 [5..100] abacaba',
    'solutionNames': ['main.cpp', 'wa.cpp'],
    'timeLimit': 2000,
    'memoryLimit': 256,
    'totalTimeLimit': 60000,
    'testset': 'tests',
    'group': 'small',
    'ignoreValidators': False,
    'description': 'small random tests',
    'run': FINISHED_RUN_JSON,
}


class TestStressParsing:
    def test_a_stress_keeps_every_field(self):
        stress = Stress.from_json(STRESS_JSON)
        assert stress.index == 1
        assert stress.script_pattern == 'gen 10 [5..100] abacaba'
        assert stress.solution_names == ['main.cpp', 'wa.cpp']
        assert stress.time_limit == 2000
        assert stress.memory_limit == 256
        assert stress.total_time_limit == 60000
        assert stress.testset == 'tests'
        assert stress.group == 'small'
        assert stress.ignore_validators is False
        assert stress.description == 'small random tests'
        assert isinstance(stress.run, StressRun)

    def test_a_stress_without_a_context_or_a_run(self):
        """The docs: testset and group are absent if not set, run if the stress has not been run."""
        stress = Stress.from_json(json.loads(STRESS_RESULT))
        assert stress.testset is None
        assert stress.group is None
        assert stress.description == ''
        assert stress.run is None


class TestStressRunParsing:
    def test_a_finished_run_keeps_its_statistics_and_countertest(self):
        run = StressRun.from_json(FINISHED_RUN_JSON)
        assert run.status == StressRunStatus.FINISHED
        assert run.verdict == StressRunVerdict.OK
        assert run.judged_test_count == 412
        assert run.max_consumed_time == 31
        assert run.max_consumed_memory == 4194304
        assert run.comment is None
        assert isinstance(run.countertest, StressCountertest)

    def test_a_running_run_has_only_its_status(self):
        run = StressRun.from_json({'status': 'RUNNING'})
        assert run.status == StressRunStatus.RUNNING
        assert run.verdict is None
        assert run.comment is None
        assert run.judged_test_count is None
        assert run.max_consumed_time is None
        assert run.max_consumed_memory is None
        assert run.countertest is None

    def test_a_failed_run_keeps_its_comment(self):
        run = StressRun.from_json({'status': 'FINISHED', 'verdict': 'FAILED', 'comment': 'Validator failed',
                                   'judgedTestCount': 0, 'maxConsumedTime': 0, 'maxConsumedMemory': 0})
        assert run.verdict == StressRunVerdict.FAILED
        assert run.comment == 'Validator failed'
        assert run.countertest is None

    @pytest.mark.parametrize('status', list(StressRunStatus))
    def test_every_status_is_parsed(self, status):
        assert StressRun.from_json({'status': status.name}).status == status

    @pytest.mark.parametrize('verdict', list(StressRunVerdict))
    def test_every_verdict_is_parsed(self, verdict):
        assert StressRun.from_json(dict(FINISHED_RUN_JSON, verdict=verdict.name)).verdict == verdict


class TestStressCountertestParsing:
    def test_a_countertest_keeps_its_script_line_input_and_reports(self):
        countertest = StressCountertest.from_json(COUNTERTEST_JSON)
        assert countertest.script_line == 'gen 10 57 abacaba 2f8a91'
        assert countertest.input == '57\n3 1 4 1 5 ...'
        assert countertest.input_truncated is True
        assert [type(report) for report in countertest.reports] == [StressSolutionReport]

    def test_a_countertest_rejected_before_its_input_was_received(self):
        """The docs: input is absent when, for example, a validator rejected the generated test."""
        countertest = StressCountertest.from_json({'scriptLine': 'gen 1 2', 'inputTruncated': False, 'reports': []})
        assert countertest.input is None
        assert countertest.reports == []


class TestStressSolutionReportParsing:
    def test_a_report_keeps_every_field(self):
        report = StressSolutionReport.from_json(REPORT_JSON)
        assert report.solution_name == 'wa.cpp'
        assert report.verdict == StressSolutionVerdict.WRONG_ANSWER
        assert report.consumed_time == 15
        assert report.consumed_memory == 2097152
        assert report.output == '12'
        assert report.output_truncated is False
        assert report.answer == '13'
        assert report.answer_truncated is False
        assert report.comment == 'wrong answer expected 13, found 12'

    def test_absent_output_answer_and_comment_read_as_none(self):
        report = StressSolutionReport.from_json({
            'solutionName': 'slow.cpp', 'verdict': 'TIME_LIMIT_EXCEEDED', 'consumedTime': 2000,
            'consumedMemory': 1048576, 'outputTruncated': False, 'answerTruncated': False,
        })
        assert report.output is None
        assert report.answer is None
        assert report.comment is None

    @pytest.mark.parametrize('verdict', list(StressSolutionVerdict))
    def test_every_verdict_is_parsed(self, verdict):
        assert StressSolutionReport.from_json(dict(REPORT_JSON, verdict=verdict.name)).verdict == verdict


class TestStresses:
    """problem.stresses returns a list of stresses, also when it is asked for a single one."""

    URL = 'https://example.invalid/api/problem.stresses'

    def test_only_the_problem_id_is_sent_without_an_index(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        polygon.problem_stresses(1)
        assert calls[-1]['url'] == self.URL
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_a_single_stress_comes_back_in_a_list(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body('[%s]' % STRESS_RESULT))
        stresses = polygon.problem_stresses(1, stress_index=1)
        assert _sent_args(calls)[b'stressIndex'] == b'1'
        assert [type(stress) for stress in stresses] == [Stress]

    def test_a_problem_without_stresses_parses_into_an_empty_list(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(EMPTY_LIST_RESULT))
        assert polygon.problem_stresses(1) == []

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body('[%s]' % STRESS_RESULT))
        stress, = problem.stresses(stress_index=1)
        assert stress.index == 1
        assert calls[-1]['url'] == self.URL
        assert _sent_args(calls)[b'stressIndex'] == b'1'


class TestSaveStress:
    """
    problem.saveStress creates a stress without an index and updates the stress with one, in which
    case a parameter that is not passed keeps its value and is not sent.
    """

    URL = 'https://example.invalid/api/problem.saveStress'

    def test_a_creation_sends_every_argument_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(STRESS_RESULT))
        polygon.problem_save_stress(1, script_pattern='gen [1..10] | gen 5', solution_names=['wa.cpp', 'tl.cpp'],
                                    time_limit=1000, memory_limit=64, total_time_limit=15000, testset='tests',
                                    group='small', ignore_validators=True, description='small tests')
        assert calls[-1]['url'] == self.URL
        args = _sent_args(calls)
        assert b'stressIndex' not in args
        assert args[b'scriptPattern'] == b'gen [1..10] | gen 5'
        assert args[b'solutionNames'] == b'wa.cpp,tl.cpp'
        assert args[b'timeLimit'] == b'1000'
        assert args[b'memoryLimit'] == b'64'
        assert args[b'totalTimeLimit'] == b'15000'
        assert args[b'testset'] == b'tests'
        assert args[b'group'] == b'small'
        assert args[b'ignoreValidators'] == b'true'
        assert args[b'description'] == b'small tests'

    def test_solution_names_may_be_a_comma_separated_string(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(STRESS_RESULT))
        polygon.problem_save_stress(1, script_pattern='gen [1..10]', solution_names='wa.cpp,tl.cpp')
        assert _sent_args(calls)[b'solutionNames'] == b'wa.cpp,tl.cpp'

    def test_an_update_sends_only_what_it_changes(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(STRESS_RESULT))
        polygon.problem_save_stress(1, stress_index=3, total_time_limit=120000)
        assert set(_sent_args(calls)) == {b'problemId', b'stressIndex', b'totalTimeLimit',
                                          b'apiKey', b'time', b'apiSig'}

    def test_empty_values_are_sent_to_clear_them(self, polygon, monkeypatch):
        """The docs: an empty testset, group or description clears it."""
        calls = _install_fake_post(monkeypatch, text=_ok_body(STRESS_RESULT))
        polygon.problem_save_stress(1, stress_index=3, testset='', group='', description='')
        args = _sent_args(calls)
        assert (args[b'testset'], args[b'group'], args[b'description']) == (b'', b'', b'')

    def test_the_saved_stress_is_returned(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(STRESS_RESULT))
        stress = polygon.problem_save_stress(1, script_pattern='gen [1..10]', solution_names=['wa.cpp'])
        assert isinstance(stress, Stress)
        assert stress.run is None

    @pytest.mark.parametrize('kwargs', [
        {'script_pattern': 'gen [1..10]'},
        {'solution_names': ['wa.cpp']},
        {},
    ], ids=['no-solutions', 'no-pattern', 'neither'])
    def test_a_creation_needs_the_pattern_and_the_solutions(self, polygon, kwargs):
        with pytest.raises(ValueError):
            polygon.problem_save_stress(1, **kwargs)

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(STRESS_RESULT))
        stress = problem.save_stress(script_pattern='gen [1..10]', solution_names=['wa.cpp'], ignore_validators=False)
        assert stress.index == 1
        assert calls[-1]['url'] == self.URL
        args = _sent_args(calls)
        assert args[b'scriptPattern'] == b'gen [1..10]'
        assert args[b'solutionNames'] == b'wa.cpp'
        assert args[b'ignoreValidators'] == b'false'


class TestDeleteStress:
    URL = 'https://example.invalid/api/problem.deleteStress'

    def test_the_index_is_sent_under_its_documented_name(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        polygon.problem_delete_stress(1, 2)
        assert calls[-1]['url'] == self.URL
        assert set(_sent_args(calls)) == {b'problemId', b'stressIndex', b'apiKey', b'time', b'apiSig'}
        assert _sent_args(calls)[b'stressIndex'] == b'2'

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        problem.delete_stress(2)
        assert calls[-1]['url'] == self.URL
        assert _sent_args(calls)[b'stressIndex'] == b'2'


@pytest.mark.parametrize('polygon_method, problem_method, api_method', [
    ('problem_run_stresses', 'run_stresses', 'problem.runStresses'),
    ('problem_cancel_stresses', 'cancel_stresses', 'problem.cancelStresses'),
], ids=['run', 'cancel'])
class TestRunAndCancelStresses:
    """
    problem.runStresses and problem.cancelStresses take the same optional comma-separated list of
    indices, and act on every stress of the problem without it.
    """

    def test_every_stress_is_meant_without_indices(self, polygon, monkeypatch, polygon_method, problem_method,
                                                   api_method):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        getattr(polygon, polygon_method)(1)
        assert calls[-1]['url'] == 'https://example.invalid/api/' + api_method
        assert set(_sent_args(calls)) == {b'problemId', b'apiKey', b'time', b'apiSig'}

    def test_a_list_of_indices_is_sent_comma_separated(self, polygon, monkeypatch, polygon_method, problem_method,
                                                       api_method):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        getattr(polygon, polygon_method)(1, [1, 3])
        assert _sent_args(calls)[b'stressIndices'] == b'1,3'

    def test_a_string_of_indices_is_sent_as_it_is(self, polygon, monkeypatch, polygon_method, problem_method,
                                                  api_method):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        getattr(polygon, polygon_method)(1, '2,4')
        assert _sent_args(calls)[b'stressIndices'] == b'2,4'

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch, polygon_method,
                                                         problem_method, api_method):
        calls = _install_fake_post(monkeypatch, text=OK_JSON_BODY)
        getattr(problem, problem_method)([2])
        assert calls[-1]['url'] == 'https://example.invalid/api/' + api_method
        assert _sent_args(calls)[b'stressIndices'] == b'2'


class TestAddStressCountertest:
    """problem.addStressCountertest adds the countertest of a stress to a testset and returns the test."""

    URL = 'https://example.invalid/api/problem.addStressCountertest'

    def test_the_index_and_the_testset_are_sent_under_their_documented_names(self, polygon, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ADDED_TEST_RESULT))
        polygon.problem_add_stress_countertest(1, 2, 'tests')
        assert calls[-1]['url'] == self.URL
        args = _sent_args(calls)
        assert set(args) == {b'problemId', b'stressIndex', b'testset', b'apiKey', b'time', b'apiSig'}
        assert args[b'stressIndex'] == b'2'
        assert args[b'testset'] == b'tests'

    def test_a_generated_test_is_returned(self, polygon, monkeypatch):
        _install_fake_post(monkeypatch, text=_ok_body(ADDED_TEST_RESULT))
        test = polygon.problem_add_stress_countertest(1, 2, 'tests')
        assert isinstance(test, api.GeneratedTest)
        assert test.index == 5
        assert test.testset == 'tests'
        assert test.script_line == 'gen 10 57 abacaba 2f8a91'
        assert test.description == 'Added from stress #1'

    def test_a_small_input_comes_back_as_a_manual_test(self, polygon, monkeypatch):
        """The docs: a small generated input may be stored as a manual test."""
        _install_fake_post(monkeypatch, text=_ok_body(
            '{"index": 5, "manual": true, "input": "57\\n", "useInStatements": false}'))
        test = polygon.problem_add_stress_countertest(1, 2, 'tests')
        assert isinstance(test, ManualTest)
        assert test.input == '57\n'

    def test_the_pin_is_kept_on_the_returned_test(self, polygon, monkeypatch):
        """Like the tests of problem.tests, the added test sends the same pin when it is saved."""
        _install_fake_post(monkeypatch, text=_ok_body(ADDED_TEST_RESULT))
        assert polygon.problem_add_stress_countertest(1, 2, 'tests', pin='1234').pin == '1234'

    def test_the_problem_shortcut_sends_the_same_request(self, problem, monkeypatch):
        calls = _install_fake_post(monkeypatch, text=_ok_body(ADDED_TEST_RESULT))
        problem.pin = '1234'
        test = problem.add_stress_countertest(2, 'samples')
        assert test.testset == 'samples'
        assert test.pin == '1234'
        assert calls[-1]['url'] == self.URL
        args = _sent_args(calls)
        assert args[b'stressIndex'] == b'2'
        assert args[b'testset'] == b'samples'
