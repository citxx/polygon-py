"""
Tests for the parts of the wrapper that need no network access: argument
formatting, local argument validation and JSON parsing.
"""

import pytest

from polygon_api import (
    CheckerTest,
    CheckerTestVerdict,
    Package,
    PackageState,
    PackageType,
    Polygon,
    ValidatorTest,
    ValidatorTestVerdict,
)
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
