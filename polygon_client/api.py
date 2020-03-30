import hashlib
import json
import random
import requests
import string
import time
from enum import Enum, auto


class Polygon:
    """
    """

    # API methods
    _CONTEST_PROBLEMS = 'contest.problems'
    _PROBLEM_INFO = 'problem.info'
    _PROBLEM_UPDATE_INFO = 'problem.updateInfo'
    _PROBLEM_STATEMENTS = 'problem.statements'
    _PROBLEM_SAVE_STATEMENT = 'problem.saveStatement'
    _PROBLEM_STATEMENT_RESOURCES = 'problem.statementResources'
    _PROBLEM_SAVE_STATEMENT_RESOURCE = 'problem.saveStatementResource'
    _PROBLEMS_LIST = 'problems.list'
    _PROBLEM_CHECKER = 'problem.checker'
    _PROBLEM_VALIDATOR = 'problem.validator'
    _PROBLEM_INTERACTOR = 'problem.interactor'
    _PROBLEM_FILES = 'problem.files'
    _PROBLEM_SOLUTIONS = 'problem.solutions'
    _PROBLEM_VIEW_FILE = 'problem.viewFile'
    _PROBLEM_VIEW_SOLUTION = 'problem.viewSolution'
    _PROBLEM_SCRIPT = 'problem.script'
    _PROBLEM_TESTS = 'problem.tests'
    _PROBLEM_TEST_INPUT = 'problem.testInput'
    _PROBLEM_TEST_ANSWER = 'problem.testAnswer'
    _PROBLEM_SET_VALIDATOR = 'problem.setValidator'
    _PROBLEM_SET_CHECKER = 'problem.setChecker'
    _PROBLEM_SET_INTERACTOR = 'problem.setInteractor'
    _PROBLEM_SAVE_FILE = 'problem.saveFile'
    _PROBLEM_SAVE_SOLUTION = 'problem.saveSolution'
    _PROBLEM_EDIT_SOLUTION_EXTRA_TAGS = 'problem.editSolutionExtraTags'
    _PROBLEM_SAVE_SCRIPT = 'problem.saveScript'
    _PROBLEM_SAVE_TEST = 'problem.saveTest'
    _PROBLEM_ENABLE_GROUPS = 'problem.enableGroups'
    _PROBLEM_ENABLE_POINTS = 'problem.enablePoints'
    _PROBLEM_VIEW_TEST_GROUP = 'problem.viewTestGroup'
    _PROBLEM_SAVE_TEST_GROUP = 'problem.saveTestGroup'
    _PROBLEM_VIEW_TAGS = 'problem.viewTags'
    _PROBLEM_SAVE_TAGS = 'problem.saveTags'
    _PROBLEM_VIEW_GENERAL_DESCRIPTION = 'problem.viewGeneralDescription'
    _PROBLEM_SAVE_GENERAL_DESCRIPTION = 'problem.saveGeneralDescription'
    _PROBLEM_VIEW_GENERAL_TUTORIAL = 'problem.viewGeneralTutorial'
    _PROBLEM_SAVE_GENERAL_TUTORIAL = 'problem.saveGeneralTutorial'

    def __init__(self, api_url, api_key, api_secret):
        self.request_config = RequestConfig(api_url, api_key, api_secret)

    def problems_list(self, show_deleted=None, id=None, name=None, owner=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEMS_LIST,
            args={
                'showDeleted': show_deleted,
                'id': id,
                'name': name,
                'owner': owner,
            }
        )
        return [Problem.from_json(self, p_json) for p_json in response.result]

    def problem_info(self, problem_id):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_INFO,
            args={'problemId': problem_id},
        )
        return ProblemInfo.from_json(response.result)

    def problem_update_info(self, problem_id, problem_info):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_UPDATE_INFO,
            args={
                'problemId': problem_id,
                'inputFile': problem_info.input_file,
                'outputFile': problem_info.output_file,
                'interactive': problem_info.interactive,  # TODO
                'timeLimit': problem_info.time_limit,
                'memoryLimit': problem_info.memory_limit,
            },
        )
        return response.result

    def problem_view_tags(self, problem_id):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_VIEW_TAGS,
            args={'problemId': problem_id},
        )
        return response.result

    def problem_save_tags(self, problem_id, tags):
        """
        """
        tags_str = ','.join(tags)
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_TAGS,
            args={
                'problemId': problem_id,
                'tags': tags_str,
            },
        )
        return response.result

    def problem_view_general_description(self, problem_id):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_VIEW_GENERAL_DESCRIPTION,
            args={'problemId': problem_id},
        )
        return response.result

    def problem_save_general_description(self, problem_id, description):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_GENERAL_DESCRIPTION,
            args={
                'problemId': problem_id,
                'description': description,
            },
        )
        return response.result

    def problem_view_general_tutorial(self, problem_id):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_VIEW_GENERAL_TUTORIAL,
            args={'problemId': problem_id},
        )
        return response.result

    def problem_save_general_tutorial(self, problem_id, tutorial):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_GENERAL_TUTORIAL,
            args={
                'problemId': problem_id,
                'tutorial': tutorial,
            },
        )
        return response.result

    def problem_statements(self, problem_id):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_STATEMENTS,
            args={
                'problemId': problem_id,
            },
        )
        return {lang: Statement.from_json(statement_json) for lang, statement_json in response.result.items()}

    def problem_save_statement(self, problem_id, lang, problem_statement):
        """
        """
        if not isinstance(problem_statement, Statement):
            raise ValueError(
                "Expected Statement instance for problem_statement argument, but %s found" % type(problem_statement))
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_STATEMENT,
            args={
                'problemId': problem_id,
                'lang': lang,
                'encoding': problem_statement.encoding,
                'name': problem_statement.name,
                'legend': problem_statement.legend,
                'input': problem_statement.input,
                'output': problem_statement.output,
                'notes': problem_statement.notes,
                'tutorial': problem_statement.tutorial,
            },
        )
        return response.result

    def problem_enable_groups(self, problem_id, testset, enable):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_ENABLE_GROUPS,
            args={
                'problemId': problem_id,
                'testset': testset,
                'enable': enable,
            },
        )
        return response.result

    def problem_enable_points(self, problem_id, enable):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_ENABLE_POINTS,
            args={
                'problemId': problem_id,
                'enable': enable,
            },
        )
        return response.result

    def problem_save_test(self, problem_id, testset, test_index, test_input, test_group=None, test_points=None,
                          test_description=None, test_use_in_statements=None, test_input_for_statements=None,
                          test_output_for_statements=None, verify_input_output_for_statements=None, check_existing=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_TEST,
            args={
                'problemId': problem_id,
                'testset': testset,
                'testIndex': test_index,
                'testInput': test_input,
                'testGroup': test_group,
                'testPoints': test_points,
                'testDescription': test_description,
                'testUseInStatements': test_use_in_statements,
                'testInputForStatements': test_input_for_statements,
                'testOutputForStatements': test_output_for_statements,
                'verifyInputOutputForStatements': verify_input_output_for_statements,
                'checkExisting': check_existing,
            }
        )
        return response.result

    def problem_save_test_group(self, problem_id, testset, group, points_policy=None, feedback_policy=None,
                                dependencies=None):
        if isinstance(dependencies, list):
            dependencies = ",".join(map(str, dependencies))
        elif dependencies is not None:
            dependencies = str(dependencies)
        if not isinstance(points_policy, PointsPolicy):
            raise ValueError(
                "Expected PointsPolicy instance for points_policy argument, but %s found" % type(points_policy))
        if not isinstance(feedback_policy, FeedbackPolicy):
            raise ValueError(
                "Expected FeedbackPolicy instance for feedback_policy argument, but %s found" % type(feedback_policy))
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_TEST_GROUP,
            args={
                'problemId': problem_id,
                'testset': testset,
                'group': group,
                'pointsPolicy': points_policy,
                'feedbackPolicy': feedback_policy,
                'dependencies': dependencies,
            }
        )
        return response.result

    def problem_save_file(self, problem_id, type, name, file, source_type=None, resource_advanced_properties=None):
        stages = None if resource_advanced_properties.stages is None else \
            ';'.join(map(str, resource_advanced_properties.stages))
        assets = None if resource_advanced_properties.assets is None else \
            ';'.join(map(str, resource_advanced_properties.assets))
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_FILE,
            args={
                'problemId': problem_id,
                'type': type,
                'name': name,
                'file': file,
                'sourceType': source_type,
                'forTypes': resource_advanced_properties.for_types,
                'stages': stages,
                'assets': assets,
            }
        )
        return response.result

    def problem_save_solution(self, problem_id, name, file, source_type, tag, check_existing=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_SOLUTION,
            args={
                'problemId': problem_id,
                'name': name,
                'file': file,
                'sourceType': source_type,
                'tag': tag,
                'checkExisting': check_existing,
            }
        )
        return response.result

    def problem_set_checker(self, problem_id, checker):
        response = self._request_ok_or_raise(
            self._PROBLEM_SET_CHECKER,
            args={
                'problemId': problem_id,
                'checker': checker,
            },
        )
        return response.result

    def contest_problems(self, contest_id):
        """
        """
        response = self._request_ok_or_raise(
            self._CONTEST_PROBLEMS,
            args={'contestId': contest_id},
        )
        return {
            name: Problem.from_json(self, p_json)
            for name, p_json in response.result.items()
        }

    def _request_ok_or_raise(self, method_name, args=None):
        response = self._request(method_name, args=args)
        if response.status != Response.STATUS_OK:
            raise PolygonRequestFailedException(response.comment)
        return response

    def _request(self, method_name, args=None):
        request = Request(self.request_config, method_name, args)
        return request.issue()


class Problem:
    """
    Object representing Polygon problem
    """

    # JSON field names
    _ID_FIELD = 'id'
    _OWNER_FIELD = 'owner'
    _NAME_FIELD = 'name'
    _DELETED_FIELD = 'deleted'
    _FAVORITE_FIELD = 'favourite'
    _ACCESS_TYPE_FIELD = 'accessType'
    _REVISION_FIELD = 'revision'
    _LATEST_PACKAGE_FIELD = 'latestPackage'
    _MODIFIED_FIELD = 'modified'

    @classmethod
    def from_json(cls, polygon, problem_json):
        return cls(
            polygon=polygon,
            problem_id=problem_json.get(Problem._ID_FIELD),
            owner=problem_json.get(Problem._OWNER_FIELD),
            name=problem_json.get(Problem._NAME_FIELD),
            deleted=problem_json.get(Problem._DELETED_FIELD),
            favorite=problem_json.get(Problem._FAVORITE_FIELD),
            access_type=problem_json.get(Problem._ACCESS_TYPE_FIELD),
            revision=problem_json.get(Problem._REVISION_FIELD),
            latest_package=problem_json.get(Problem._LATEST_PACKAGE_FIELD),
            modified=problem_json.get(Problem._MODIFIED_FIELD),
        )

    def __init__(self, polygon, problem_id, owner, name, deleted, favorite, access_type, revision, latest_package,
                 modified):
        self._polygon = polygon

        self.id = problem_id
        self.owner = owner
        self.name = name
        self.deleted = deleted
        self.favorite = favorite
        self.access_type = access_type
        self.revision = revision
        self.latest_package = latest_package
        self.modified = modified

    def __str__(self):
        return '{}:{}'.format(self.name, self.id)

    def info(self):
        return self._polygon.problem_info(self.id)

    def update_info(self, problem_info):
        return self._polygon.problem_update_info(self.id, problem_info)

    def tags(self):
        return self._polygon.problem_view_tags(self.id)

    def save_tags(self, tags):
        return self._polygon.problem_save_tags(self.id, tags)

    def general_description(self):
        return self._polygon.problem_view_general_description(self.id)

    def save_general_description(self, description):
        return self._polygon.problem_save_general_description(self.id, description)

    def general_tutorial(self):
        return self._polygon.problem_view_general_tutorial(self.id)

    def save_general_tutorial(self, tutorial):
        return self._polygon.problem_save_general_tutorial(self.id, tutorial)

    def statements(self):
        return self._polygon.problem_statements(self.id)

    def save_statement(self, lang, problem_statement):
        return self._polygon.problem_save_statement(self.id, lang, problem_statement)

    def enable_groups(self, testset, enable):
        return self._polygon.problem_enable_groups(self.id, testset, enable)

    def enable_points(self, enable):
        return self._polygon.problem_enable_points(self.id, enable)

    def save_test(self, testset, test_index, test_input, test_group=None, test_points=None, test_description=None,
                  test_use_in_statements=None, test_input_for_statements=None, test_output_for_statements=None,
                  verify_input_output_for_statements=None, check_existing=None):
        return self._polygon.problem_save_test(self.id, testset, test_index, test_input, test_group, test_points,
                                               test_description, test_use_in_statements, test_input_for_statements,
                                               test_output_for_statements, verify_input_output_for_statements,
                                               check_existing)

    def save_test_group(self, testset, group, points_policy=None, feedback_policy=None, dependencies=None):
        return self._polygon.problem_save_test_group(self.id, testset, group,
                                                     points_policy, feedback_policy, dependencies)

    def save_file(self, type, name, file, source_type=None, resource_advanced_properties=None):
        return self._polygon.problem_save_file(self.id, type, name, file, source_type, resource_advanced_properties)

    def save_solution(self, name, file, source_type, tag, check_existing=None):
        return self._polygon.problem_save_solution(self.id, name, file, source_type, tag, check_existing)

    def set_checker(self, checker):
        return self._polygon.problem_set_checker(self.id, checker)


class ProblemInfo:
    """
    Object representing Polygon problem info
    """

    # JSON field names
    _INPUT_FILE = 'inputFile'
    _OUTPUT_FILE = 'outputFile'
    _INTERACTIVE = 'interactive'
    _TIME_LIMIT = 'timeLimit'
    _MEMORY_LIMIT = 'memoryLimit'

    @classmethod
    def from_json(cls, problem_info_json):
        return cls(
            input_file=problem_info_json[ProblemInfo._INPUT_FILE],
            output_file=problem_info_json[ProblemInfo._OUTPUT_FILE],
            interactive=problem_info_json[ProblemInfo._INTERACTIVE],
            time_limit=problem_info_json[ProblemInfo._TIME_LIMIT],
            memory_limit=problem_info_json[ProblemInfo._MEMORY_LIMIT],
        )

    def __init__(self, input_file=None, output_file=None, interactive=None, time_limit=None, memory_limit=None):
        self.input_file = input_file
        self.output_file = output_file
        self.interactive = interactive
        self.time_limit = time_limit
        self.memory_limit = memory_limit


class Statement:
    """
    Object: representing Polygon problem statement
    """
    _ENCODING = "encoding"
    _NAME = "name"
    _LEGEND = "legend"
    _INPUT = "input"
    _OUTPUT = "output"
    _NOTES = "notes"
    _TUTORIAL = "tutorial"

    @classmethod
    def from_json(cls, statement_json):
        return cls(
            encoding=statement_json[Statement._ENCODING],
            name=statement_json[Statement._NAME],
            legend=statement_json[Statement._LEGEND],
            input=statement_json[Statement._INPUT],
            output=statement_json[Statement._OUTPUT],
            notes=statement_json[Statement._NOTES],
            tutorial=statement_json[Statement._TUTORIAL],
        )

    def __init__(self, encoding=None, name=None, legend=None, input=None, output=None, notes=None, tutorial=None):
        self.encoding = encoding
        self.name = name
        self.legend = legend
        self.input = input
        self.output = output
        self.notes = notes
        self.tutorial = tutorial


class ResourceAdvancedProperties:
    """
    """
    _FOR_TYPES = "forTypes"
    _MAIN = "main"
    _STAGES = "stages"
    _ASSETS = "assets"

    @classmethod
    def from_json(cls, resource_advanced_properties):
        return cls(
            for_types=resource_advanced_properties[ResourceAdvancedProperties._FOR_TYPES],
            main=resource_advanced_properties[ResourceAdvancedProperties._MAIN],
            stages=resource_advanced_properties[ResourceAdvancedProperties._STAGES],
            assets=resource_advanced_properties[ResourceAdvancedProperties._ASSETS],
        )

    def __init__(self, for_types=None, main=None, stages=None, assets=None):
        self.for_types = for_types
        self.main = main
        self.stages = stages
        self.assets = assets


ResourceAdvancedProperties.DELETE = ResourceAdvancedProperties(for_types="")


class Request:
    """
    Request to Polygon API.
    TODO: update
    Usage example:
    >>> request = Request(Request.CONTEST_PROBLEMS,
    ...                   args={'contestId': contest_id})
    >>> response = request.issue()
    >>> problems = response["result"]
    """

    def __init__(self, config, method_name, args=None):
        if args is None:
            args = {}
        args = {key: value for key, value in args.items() if value is not None}
        for key in args:
            if isinstance(args[key], bool):
                args[key] = 'true' if args[key] else 'false'
        self.args = []
        for key, value in args.items():
            if isinstance(value, list):
                for it in value:
                    self.args.append((key, str(it)))
            else:
                self.args.append((key, str(value)))
        self.config = config
        self.method_name = method_name

    def issue(self):
        """Issues request and returns parsed JSON response"""

        args = list(self.args)
        args.append(('apiKey', self.config.api_key))
        args.append(('time', str(int(time.time()))))
        args.append(('apiSig', self.get_api_signature(args, self.config.api_secret)))
        response = requests.post(
            self.config.api_url + self.method_name, files=args)
        return Response(json.loads(response.text))

    def get_api_signature(self, args, api_secret):
        rand_bit = ''.join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in range(6))

        arg_tuples = list(sorted(args))
        args_bit = '&'.join(key + '=' + str(value) for key, value in arg_tuples)
        api_signature_string = '{}/{}?{}#{}'.format(
            rand_bit, self.method_name, args_bit, api_secret)
        api_signature = (
            rand_bit +
            hashlib.sha512(api_signature_string.encode('utf-8')).hexdigest())
        return api_signature


class Response:
    """
    """

    # JSON field names
    FIELD_STATUS = 'status'
    FIELD_COMMENT = 'comment'
    FIELD_RESULT = 'result'

    # Status values
    STATUS_OK = 'OK'
    STATUS_FAILED = 'FAILED'
    STATUS_UNKNOWN = 'UNKNOWN'

    def __init__(self, response_json):
        self.status = response_json.get(Response.FIELD_STATUS)
        if self.status not in [Response.STATUS_OK, Response.STATUS_FAILED]:
            self.status = Response.STATUS_UNKNOWN

        self.comment = response_json.get(Response.FIELD_COMMENT, '')
        self.result = response_json.get(Response.FIELD_RESULT)


class RequestConfig:
    def __init__(self, api_url, api_key, api_secret):
        if not api_url.endswith('/'):
            api_url += '/'
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret


class PolygonRequestFailedException(Exception):
    """Exception raised when Polygon returns FAILED as request status"""

    def __init__(self, comment):
        self.comment = comment


class PointsPolicy(Enum):
    COMPLETE_GROUP = auto()
    EACH_TEST = auto()

    def __str__(self):
        return self.name


class FeedbackPolicy(Enum):
    NONE = auto()
    POINTS = auto()
    ICPC = auto()
    COMPLETE = auto()

    def __str__(self):
        return self.name


class FileType(Enum):
    RESOURCE = auto()
    SOURCE = auto()
    AUX = auto()

    def __str__(self):
        return self.name.lower()


class SolutionTag(Enum):
    MA = auto()  # Main correct solution
    OK = auto()  # Accepted
    RJ = auto()  # Rejected, Incorrect
    TL = auto()  # Time limit exceeded
    TO = auto()  # Time limit exceeded or accepted
    WA = auto()  # Wrong answer
    PE = auto()  # Presentation error
    ML = auto()  # Memory limit exceeded
    RE = auto()  # Runtime error

    def __str__(self):
        return self.name


class Asset(Enum):
    VALIDATOR = auto()
    INTERACTOR = auto()
    CHECKER = auto()
    SOLUTION = auto()

    def __str__(self):
        return self.name


class Stage(Enum):
    COMPILE = auto()
    RUN = auto()

    def __str__(self):
        return self.name
