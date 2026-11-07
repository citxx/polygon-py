import base64
import hashlib
import json
import random
import requests
import string
import time
from collections.abc import Iterable
from enum import Enum


def _comma_separated(value):
    """
    Formats a value for an API parameter accepting a comma-separated list.

    A string is passed through unchanged, any other iterable is joined with
    commas, and anything else is stringified. None is returned as is, so that
    Request omits the parameter altogether.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, Iterable):
        return ",".join(map(str, value))
    return str(value)


class Polygon:
    """
    """

    # API methods
    _CONTEST_PROBLEMS = 'contest.problems'
    _PROBLEM_INFO = 'problem.info'
    _PROBLEM_UPDATE_INFO = 'problem.updateInfo'
    _PROBLEM_NOTE = 'problem.note'
    _PROBLEM_SAVE_NOTE = 'problem.saveNote'
    _PROBLEM_UPDATE_WORKING_COPY = 'problem.updateWorkingCopy'
    _PROBLEM_DISCARD_WORKING_COPY = 'problem.discardWorkingCopy'
    _PROBLEM_COMMIT_CHANGES = 'problem.commitChanges'
    _PROBLEM_STATEMENTS = 'problem.statements'
    _PROBLEM_RENDER_STATEMENTS = 'problem.renderStatements'
    _PROBLEM_SAVE_STATEMENT = 'problem.saveStatement'
    _PROBLEM_DELETE_STATEMENT = 'problem.deleteStatement'
    _PROBLEM_STATEMENT_RESOURCES = 'problem.statementResources'
    _PROBLEM_VIEW_STATEMENT_RESOURCE = 'problem.viewStatementResource'
    _PROBLEM_SAVE_STATEMENT_RESOURCE = 'problem.saveStatementResource'
    _PROBLEM_DELETE_STATEMENT_RESOURCE = 'problem.deleteStatementResource'
    _PROBLEMS_LIST = 'problems.list'
    _PROBLEM_CREATE = 'problem.create'
    _PROBLEM_CHECKER = 'problem.checker'
    _PROBLEM_VALIDATOR = 'problem.validator'
    _PROBLEM_EXTRA_VALIDATORS = 'problem.extraValidators'
    _PROBLEM_INTERACTOR = 'problem.interactor'
    _PROBLEM_VALIDATOR_TESTS = 'problem.validatorTests'
    _PROBLEM_SAVE_VALIDATOR_TEST = 'problem.saveValidatorTest'
    _PROBLEM_DELETE_VALIDATOR_TEST = 'problem.deleteValidatorTest'
    _PROBLEM_CHECKER_TESTS = 'problem.checkerTests'
    _PROBLEM_SAVE_CHECKER_TEST = 'problem.saveCheckerTest'
    _PROBLEM_DELETE_CHECKER_TEST = 'problem.deleteCheckerTest'
    _PROBLEM_FILES = 'problem.files'
    _PROBLEM_SOLUTIONS = 'problem.solutions'
    _PROBLEM_VIEW_FILE = 'problem.viewFile'
    _PROBLEM_VIEW_SOLUTION = 'problem.viewSolution'
    _PROBLEM_SCRIPT = 'problem.script'
    _PROBLEM_CLEAR_SCRIPT = 'problem.clearScript'
    _PROBLEM_TESTS = 'problem.tests'
    _PROBLEM_PREVIEW_TESTS = 'problem.previewTests'
    _PROBLEM_TEST_INPUT = 'problem.testInput'
    _PROBLEM_TEST_ANSWER = 'problem.testAnswer'
    _PROBLEM_SET_VALIDATOR = 'problem.setValidator'
    _PROBLEM_SET_CHECKER = 'problem.setChecker'
    _PROBLEM_SET_INTERACTOR = 'problem.setInteractor'
    _PROBLEM_SAVE_FILE = 'problem.saveFile'
    _PROBLEM_DELETE_FILE = 'problem.deleteFile'
    _PROBLEM_SAVE_SOLUTION = 'problem.saveSolution'
    _PROBLEM_DELETE_SOLUTION = 'problem.deleteSolution'
    _PROBLEM_EDIT_SOLUTION_EXTRA_TAGS = 'problem.editSolutionExtraTags'
    _PROBLEM_SAVE_SCRIPT = 'problem.saveScript'
    _PROBLEM_SAVE_TEST = 'problem.saveTest'
    _PROBLEM_DELETE_TEST = 'problem.deleteTest'
    _PROBLEM_SET_TEST_GROUP = 'problem.setTestGroup'
    _PROBLEM_ENABLE_GROUPS = 'problem.enableGroups'
    _PROBLEM_ENABLE_POINTS = 'problem.enablePoints'
    _PROBLEM_ENABLE_TREAT_POINTS_FROM_CHECKER_AS_PERCENT = 'problem.enableTreatPointsFromCheckerAsPercent'
    _PROBLEM_VIEW_TEST_GROUP = 'problem.viewTestGroup'
    _PROBLEM_SAVE_TEST_GROUP = 'problem.saveTestGroup'
    _PROBLEM_VIEW_TAGS = 'problem.viewTags'
    _PROBLEM_SAVE_TAGS = 'problem.saveTags'
    _PROBLEM_VIEW_GENERAL_DESCRIPTION = 'problem.viewGeneralDescription'
    _PROBLEM_SAVE_GENERAL_DESCRIPTION = 'problem.saveGeneralDescription'
    _PROBLEM_VIEW_GENERAL_TUTORIAL = 'problem.viewGeneralTutorial'
    _PROBLEM_SAVE_GENERAL_TUTORIAL = 'problem.saveGeneralTutorial'
    _PROBLEM_MATERIALS = 'problem.materials'
    _PROBLEM_SET_MATERIAL = 'problem.setMaterial'
    _PROBLEM_PACKAGES = 'problem.packages'
    _PROBLEM_PACKAGE = 'problem.package'
    _PROBLEM_BUILD_PACKAGE = 'problem.buildPackage'
    _PROBLEM_INVOCATIONS = 'problem.invocations'
    _PROBLEM_INVOCATION = 'problem.invocation'
    _PROBLEM_STRESSES = 'problem.stresses'
    _PROBLEM_SAVE_STRESS = 'problem.saveStress'
    _PROBLEM_DELETE_STRESS = 'problem.deleteStress'
    _PROBLEM_RUN_STRESSES = 'problem.runStresses'
    _PROBLEM_CANCEL_STRESSES = 'problem.cancelStresses'
    _PROBLEM_ADD_STRESS_COUNTERTEST = 'problem.addStressCountertest'
    _PROBLEM_CAUTIONS = 'problem.cautions'
    _PROBLEM_ISSUES = 'problem.issues'
    _PROBLEM_ADD_ISSUE = 'problem.addIssue'
    _PROBLEM_UPDATE_ISSUE = 'problem.updateIssue'
    _PROBLEM_ACCESSES = 'problem.accesses'
    _PROBLEM_SET_ACCESS = 'problem.setAccess'

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

    def problem_create(self, name):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_CREATE,
            args={
                'name': name,
            }
        )
        return Problem.from_json(self, response.result)

    def problem_info(self, problem_id, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_INFO,
            args={'problemId': problem_id, 'pin': pin},
        )
        return ProblemInfo.from_json(response.result)

    def problem_update_info(self, problem_id, problem_info, pin=None):
        """
        Updates the problem info with the fields of problem_info that are not None. With
        interactive=False, use_interaction_log_in_example_tests and interactive_second_run are not
        sent: Polygon rejects any value of them for a non-interactive problem, so a ProblemInfo read
        from an interactive problem can be sent back with interactive switched off
        """
        # Polygon checks these two against the interactive value of the same request.
        send_interactive_only_flags = problem_info.interactive is not False
        response = self._request_ok_or_raise(
            self._PROBLEM_UPDATE_INFO,
            args={
                'problemId': problem_id,
                'inputFile': problem_info.input_file,
                'outputFile': problem_info.output_file,
                'interactive': problem_info.interactive,  # TODO
                'wellFormed': problem_info.well_formed,
                'skipDuplicatedTestsValidation': problem_info.skip_duplicated_tests_validation,
                'useInteractionLogInExampleTests':
                    problem_info.use_interaction_log_in_example_tests if send_interactive_only_flags else None,
                'runTwice': problem_info.run_twice,
                'interactiveSecondRun': problem_info.interactive_second_run if send_interactive_only_flags else None,
                'timeLimit': problem_info.time_limit,
                'memoryLimit': problem_info.memory_limit,
                'pin': pin,
            },
        )
        return response.result

    def problem_view_note(self, problem_id, pin=None):
        """
        Calls problem.note. Returns the problem note, an empty string if it is not set
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_NOTE,
            args={'problemId': problem_id, 'pin': pin},
        )
        return response.result

    def problem_save_note(self, problem_id, note, pin=None):
        """
        Saves the problem note, up to 50 characters, an empty string clears it.
        Applies at once, problem.commitChanges is not needed
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_NOTE,
            args={
                'problemId': problem_id,
                'note': note,
                'pin': pin,
            },
        )
        return response.result

    def problem_update_working_copy(self, problem_id, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_UPDATE_WORKING_COPY,
            args={'problemId': problem_id, 'pin': pin},
        )
        return response.result

    def problem_discard_working_copy(self, problem_id, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_DISCARD_WORKING_COPY,
            args={'problemId': problem_id, 'pin': pin},
        )
        return response.result

    def problem_commit_changes(self, problem_id, minor_changes=None, message=None, pin=None):
        """
        Commits the working copy. Having nothing to commit is not a failure: the returned
        CommitResult then has committed=False and the message "No changes"
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_COMMIT_CHANGES,
            args={
                'problemId': problem_id,
                'minorChanges': minor_changes,
                'message': message,
                'pin': pin,
            },
        )
        return CommitResult.from_json(response.result)

    def problem_view_tags(self, problem_id, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_VIEW_TAGS,
            args={'problemId': problem_id, 'pin': pin},
        )
        return response.result

    def problem_save_tags(self, problem_id, tags, pin=None):
        """
        """
        tags_str = ','.join(tags)
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_TAGS,
            args={
                'problemId': problem_id,
                'tags': tags_str,
                'pin': pin,
            },
        )
        return response.result

    def problem_view_general_description(self, problem_id, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_VIEW_GENERAL_DESCRIPTION,
            args={'problemId': problem_id, 'pin': pin},
        )
        return response.result

    def problem_save_general_description(self, problem_id, description, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_GENERAL_DESCRIPTION,
            args={
                'problemId': problem_id,
                'description': description,
                'pin': pin,
            },
        )
        return response.result

    def problem_view_general_tutorial(self, problem_id, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_VIEW_GENERAL_TUTORIAL,
            args={'problemId': problem_id, 'pin': pin},
        )
        return response.result

    def problem_save_general_tutorial(self, problem_id, tutorial, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_GENERAL_TUTORIAL,
            args={
                'problemId': problem_id,
                'tutorial': tutorial,
                'pin': pin,
            },
        )
        return response.result

    def problem_statements(self, problem_id, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_STATEMENTS,
            args={
                'problemId': problem_id,
                'pin': pin,
            },
        )
        return {lang: Statement.from_json(statement_json) for lang, statement_json in response.result.items()}

    def problem_render_statements(self, problem_id, include_content=None, pin=None):
        """
        Renders statements and tutorials of the current working copy, returning an independent
        HTML and PDF render result per language
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_RENDER_STATEMENTS,
            args={
                'problemId': problem_id,
                'includeContent': include_content,
                'pin': pin,
            },
        )
        return RenderStatements.from_json(response.result)

    def problem_save_statement(self, problem_id, lang, problem_statement, pin=None):
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
                'scoring': problem_statement.scoring,
                'interaction': problem_statement.interaction,
                'notes': problem_statement.notes,
                'tutorial': problem_statement.tutorial,
                'showInReview': problem_statement.show_in_review,
                'showCautionsAndGrammaticalFixes': problem_statement.show_cautions_and_grammatical_fixes,
                'pin': pin,
            },
        )
        return response.result

    def problem_delete_statement(self, problem_id, lang, pin=None):
        """
        Deletes the statement in the given language, as problem.statements names it. The statement
        resources are kept
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_DELETE_STATEMENT,
            args={
                'problemId': problem_id,
                'lang': lang,
                'pin': pin,
            },
        )
        return response.result

    def problem_statement_resources(self, problem_id, pin=None):
        """
        Returns a list of File objects, one per statement resource
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_STATEMENT_RESOURCES,
            args={
                'problemId': problem_id,
                'pin': pin,
            },
        )
        return [File.from_json(js) for js in response.result]

    def problem_view_statement_resource(self, problem_id, name, binary=False, pin=None):
        """
        Returns statement resource file, as bytes if binary is true
        """
        response = self._request_body(
            self._PROBLEM_VIEW_STATEMENT_RESOURCE,
            args={
                'problemId': problem_id,
                'name': name,
                'pin': pin,
            },
            binary=binary
        )
        return response

    def problem_save_statement_resource(self, problem_id, name, file, check_existing=None, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_STATEMENT_RESOURCE,
            args={
                'problemId': problem_id,
                'name': name,
                'file': file,
                'checkExisting': check_existing,
                'pin': pin,
            },
        )
        return response.result

    def problem_delete_statement_resource(self, problem_id, name, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_DELETE_STATEMENT_RESOURCE,
            args={
                'problemId': problem_id,
                'name': name,
                'pin': pin,
            },
        )
        return response.result

    def problem_enable_groups(self, problem_id, testset, enable, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_ENABLE_GROUPS,
            args={
                'problemId': problem_id,
                'testset': testset,
                'enable': enable,
                'pin': pin,
            },
        )
        return response.result

    def problem_enable_points(self, problem_id, enable, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_ENABLE_POINTS,
            args={
                'problemId': problem_id,
                'enable': enable,
                'pin': pin,
            },
        )
        return response.result

    def problem_enable_treat_points_from_checker_as_percent(self, problem_id, enable, pin=None):
        """
        Enables or disables treating the points returned by the checker as percents. Enabling it
        fails while test points are disabled for the problem
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_ENABLE_TREAT_POINTS_FROM_CHECKER_AS_PERCENT,
            args={
                'problemId': problem_id,
                'enable': enable,
                'pin': pin,
            },
        )
        return response.result

    def problem_save_test(self, problem_id, testset, test_index, test_input, test_group=None, test_points=None,
                          test_description=None, test_use_in_statements=None, test_input_for_statements=None,
                          test_output_for_statements=None, verify_input_output_for_statements=None,
                          check_existing=None, pin=None):
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
                'pin': pin,
            }
        )
        return response.result

    def problem_delete_test(self, problem_id, testset, test_index=None, test_indices=None, pin=None):
        """
        Deletes one or more tests of a testset. Every requested test is checked first: if one of them
        can not be deleted, none is, and DeleteTestsFailedException lists a failure for each such test.
        Only a DELETE_FAILED failure comes from the deletion itself, which may have removed some tests
        by then
        """
        if test_index is None and test_indices is None:
            raise ValueError("Either test_index or test_indices must be specified")
        if test_index is not None and test_indices is not None:
            raise ValueError("Only one of test_index or test_indices must be specified")

        test_indices = _comma_separated(test_indices)

        response = self._request(
            self._PROBLEM_DELETE_TEST,
            args={
                'problemId': problem_id,
                'testset': testset,
                'testIndex': test_index,
                'testIndices': test_indices,
                'pin': pin,
            }
        )
        if response.status != Response.STATUS_OK:
            if response.result is None:
                raise PolygonRequestFailedException(response.comment)
            raise DeleteTestsFailedException(response.comment, DeleteTestsResult.from_json(response.result))
        return response.result

    def problem_set_test_group(self, problem_id, testset, test_group, test_index=None, test_indices=None, pin=None):
        if test_index is None and test_indices is None:
            raise ValueError("Either test_index or test_indices must be specified")
        if test_index is not None and test_indices is not None:
            raise ValueError("Only one of test_index or test_indices must be specified")

        test_indices = _comma_separated(test_indices)

        response = self._request_ok_or_raise(
            self._PROBLEM_SET_TEST_GROUP,
            args={
                'problemId': problem_id,
                'testset': testset,
                'testGroup': test_group,
                'testIndex': test_index,
                'testIndices': test_indices,
                'pin': pin,
            }
        )
        return response.result

    def problem_solutions(self, problem_id, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_SOLUTIONS,
            args={
                'problemId': problem_id,
                'pin': pin,
            }
        )
        return [Solution.from_json(js) for js in response.result]

    def problem_files(self, problem_id, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_FILES,
            args={
                'problemId': problem_id,
                'pin': pin,
            }
        )
        return {type: [File.from_json(js) for js in response.result[str(type) + 'Files']] for type in FileType}

    def problem_tests(self, problem_id, testset, no_inputs=None, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_TESTS,
            args={
                'problemId': problem_id,
                'testset': testset,
                'noInputs': no_inputs,
                'pin': pin,
            }
        )
        return [Test.from_json(self, problem_id, testset, js, pin) for js in response.result]

    def problem_preview_tests(self, problem_id, testset, pin=None):
        """
        Returns the previews of the tests of a testset. A missing or stale preview may start being
        generated and come back without input and answer: repeat the request later to get them
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_PREVIEW_TESTS,
            args={
                'problemId': problem_id,
                'testset': testset,
                'pin': pin,
            }
        )
        return [TestPreview.from_json(js) for js in response.result]

    def problem_script(self, problem_id, testset, pin=None):
        """
        Returns test generation script
        """
        response = self._request_text(
            self._PROBLEM_SCRIPT,
            args={
                'problemId': problem_id,
                'testset': testset,
                'pin': pin,
            }
        )
        return response

    def problem_clear_script(self, problem_id, testset, pin=None):
        """
        Clears test generation script for the specified testset
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_CLEAR_SCRIPT,
            args={
                'problemId': problem_id,
                'testset': testset,
                'pin': pin,
            }
        )
        return response.result

    def problem_test_input(self, problem_id, testset, test_index, binary=False, pin=None):
        """
        Returns generated test input, as bytes if binary is true
        """
        response = self._request_body(
            self._PROBLEM_TEST_INPUT,
            args={
                'problemId': problem_id,
                'testset': testset,
                'testIndex': test_index,
                'pin': pin,
            },
            binary=binary
        )
        return response

    def problem_test_answer(self, problem_id, testset, test_index, binary=False, pin=None):
        """
        Returns generated test answer, as bytes if binary is true
        """
        response = self._request_body(
            self._PROBLEM_TEST_ANSWER,
            args={
                'problemId': problem_id,
                'testset': testset,
                'testIndex': test_index,
                'pin': pin,
            },
            binary=binary
        )
        return response

    def problem_save_test_group(self, problem_id, testset, group, points_policy=None, feedback_policy=None,
                                dependencies=None, pin=None):
        dependencies = _comma_separated(dependencies)
        if points_policy is not None and not isinstance(points_policy, PointsPolicy):
            raise ValueError(
                "Expected PointsPolicy instance for points_policy argument, but %s found" % type(points_policy))
        if feedback_policy is not None and not isinstance(feedback_policy, FeedbackPolicy):
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
                'pin': pin,
            }
        )
        return response.result

    def problem_view_test_group(self, problem_id, testset, group=None, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_VIEW_TEST_GROUP,
            args={
                'problemId': problem_id,
                'testset': testset,
                'group': group,
                'pin': pin,
            },
        )
        return [TestGroup.from_json(js) for js in response.result]

    def problem_view_file(self, problem_id, type, name, binary=False, pin=None):
        response = self._request_body(
            self._PROBLEM_VIEW_FILE,
            args={
                'problemId': problem_id,
                'type': type,
                'name': name,
                'pin': pin,
            },
            binary=binary
        )
        return response

    def problem_view_solution(self, problem_id, name, binary=False, pin=None):
        response = self._request_body(
            self._PROBLEM_VIEW_SOLUTION,
            args={
                'problemId': problem_id,
                'name': name,
                'pin': pin,
            },
            binary=binary
        )
        return response

    def problem_save_file(self, problem_id, type, name, file, source_type=None, resource_advanced_properties=None,
                          check_existing=None, pin=None):
        stages = None if resource_advanced_properties is None or resource_advanced_properties.stages is None else \
            ';'.join(map(str, resource_advanced_properties.stages))
        assets = None if resource_advanced_properties is None or resource_advanced_properties.assets is None else \
            ';'.join(map(str, resource_advanced_properties.assets))
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_FILE,
            args={
                'problemId': problem_id,
                'type': type,
                'name': name,
                'file': file,
                'sourceType': source_type,
                'forTypes': None if resource_advanced_properties is None else resource_advanced_properties.for_types,
                'stages': stages,
                'assets': assets,
                'checkExisting': check_existing,
                'pin': pin,
            }
        )
        return response.result

    def problem_delete_file(self, problem_id, type, name, pin=None):
        """
        Deletes a resource, source or aux file. olymp.sty, problem.tex and statements.ftl can't be
        deleted, nor a source file used as a generator in a test script or in a stress
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_DELETE_FILE,
            args={
                'problemId': problem_id,
                'type': type,
                'name': name,
                'pin': pin,
            }
        )
        return response.result

    def problem_save_solution(self, problem_id, name, file, tag, source_type=None, check_existing=None, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_SOLUTION,
            args={
                'problemId': problem_id,
                'name': name,
                'file': file,
                'sourceType': source_type,
                'tag': tag,
                'checkExisting': check_existing,
                'pin': pin,
            }
        )
        return response.result

    def problem_delete_solution(self, problem_id, name, pin=None):
        """
        Deletes a solution and removes it from the stresses; a stress left without solutions is deleted
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_DELETE_SOLUTION,
            args={
                'problemId': problem_id,
                'name': name,
                'pin': pin,
            }
        )
        return response.result

    def problem_save_script(self, problem_id, testset, source, pin=None):
        """
        Edit test generation script
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_SCRIPT,
            args={
                'problemId': problem_id,
                'testset': testset,
                'source': source,
                'pin': pin,
            }
        )
        return response.result

    def problem_edit_solution_extra_tags(self, problem_id, remove, name, testset=None, test_group=None,
                                         tag=None, pin=None):
        if (testset is None) == (test_group is None):
            raise ValueError("Exactly one of testset or test_group must be specified")
        if tag is not None and not isinstance(tag, SolutionTag):
            raise ValueError(
                "Expected SolutionTag instance for tag argument, but %s found" % type(tag))
        response = self._request_ok_or_raise(
            self._PROBLEM_EDIT_SOLUTION_EXTRA_TAGS,
            args={
                'problemId': problem_id,
                'remove': remove,
                'name': name,
                'testset': testset,
                'testGroup': test_group,
                'tag': tag,
                'pin': pin,
            }
        )
        return response.result

    def problem_checker(self, problem_id, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_CHECKER,
            args={
                'problemId': problem_id,
                'pin': pin,
            },
        )
        return response.result

    def problem_set_checker(self, problem_id, checker, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_SET_CHECKER,
            args={
                'problemId': problem_id,
                'checker': checker,
                'pin': pin,
            },
        )
        return response.result

    def problem_checker_tests(self, problem_id, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_CHECKER_TESTS,
            args={
                'problemId': problem_id,
                'pin': pin,
            },
        )
        return [CheckerTest.from_json(js) for js in response.result]

    def problem_save_checker_test(self, problem_id, test_index, test_input=None, test_output=None,
                                  test_answer=None, test_verdict=None, check_existing=None, pin=None):
        if test_verdict is not None and not isinstance(test_verdict, CheckerTestVerdict):
            raise ValueError(
                "Expected CheckerTestVerdict instance for test_verdict argument, but %s found" % type(test_verdict))
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_CHECKER_TEST,
            args={
                'problemId': problem_id,
                'testIndex': test_index,
                'testInput': test_input,
                'testOutput': test_output,
                'testAnswer': test_answer,
                'testVerdict': test_verdict,
                'checkExisting': check_existing,
                'pin': pin,
            },
        )
        return response.result

    def problem_delete_checker_test(self, problem_id, test_index, pin=None):
        """
        Deletes a checker test. The indices of the other checker tests do not change
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_DELETE_CHECKER_TEST,
            args={
                'problemId': problem_id,
                'testIndex': test_index,
                'pin': pin,
            },
        )
        return response.result

    def problem_validator(self, problem_id, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_VALIDATOR,
            args={
                'problemId': problem_id,
                'pin': pin,
            },
        )
        return response.result

    def problem_set_validator(self, problem_id, validator, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_SET_VALIDATOR,
            args={
                'problemId': problem_id,
                'validator': validator,
                'pin': pin,
            },
        )
        return response.result

    def problem_extra_validators(self, problem_id, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_EXTRA_VALIDATORS,
            args={
                'problemId': problem_id,
                'pin': pin,
            },
        )
        return response.result

    def problem_validator_tests(self, problem_id, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_VALIDATOR_TESTS,
            args={
                'problemId': problem_id,
                'pin': pin,
            },
        )
        return [ValidatorTest.from_json(js) for js in response.result]

    def problem_save_validator_test(self, problem_id, test_index, test_input=None, test_verdict=None,
                                    test_group=None, testset=None, check_existing=None, pin=None):
        if test_verdict is not None and not isinstance(test_verdict, ValidatorTestVerdict):
            raise ValueError(
                "Expected ValidatorTestVerdict instance for test_verdict argument, but %s found" % type(test_verdict))
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_VALIDATOR_TEST,
            args={
                'problemId': problem_id,
                'testIndex': test_index,
                'testInput': test_input,
                'testVerdict': test_verdict,
                'testGroup': test_group,
                'testset': testset,
                'checkExisting': check_existing,
                'pin': pin,
            },
        )
        return response.result

    def problem_delete_validator_test(self, problem_id, test_index, pin=None):
        """
        Deletes a validator test. The indices of the other validator tests do not change
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_DELETE_VALIDATOR_TEST,
            args={
                'problemId': problem_id,
                'testIndex': test_index,
                'pin': pin,
            },
        )
        return response.result

    def problem_interactor(self, problem_id, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_INTERACTOR,
            args={
                'problemId': problem_id,
                'pin': pin,
            },
        )
        return response.result

    def problem_set_interactor(self, problem_id, interactor, pin=None):
        response = self._request_ok_or_raise(
            self._PROBLEM_SET_INTERACTOR,
            args={
                'problemId': problem_id,
                'interactor': interactor,
                'pin': pin,
            },
        )
        return response.result

    def problem_materials(self, problem_id, pin=None):
        """
        Returns the publishable materials of the working copy, sorted by name. Stored legacy
        materials come back as they are, so one may hold an empty item or a reference that has
        become invalid
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_MATERIALS,
            args={'problemId': problem_id, 'pin': pin},
        )
        return [Material.from_json(js) for js in response.result]

    def problem_set_material(self, problem_id, name, publish_strategy=None, items=None, original_name=None,
                             remove=None, pin=None):
        """
        Creates or fully replaces the material called name, renaming original_name to name if it is
        given, or removes the material with remove=True. Saving needs publish_strategy and a list of
        MaterialItem objects; removing takes neither. Changes the working copy only:
        problem.commitChanges creates a revision
        """
        if remove:
            if publish_strategy is not None or items is not None or original_name is not None:
                raise ValueError("publish_strategy, items and original_name can't be specified with remove")
        else:
            if publish_strategy is None or items is None:
                raise ValueError("Both publish_strategy and items must be specified to save a material")
        if publish_strategy is not None and not isinstance(publish_strategy, MaterialPublishStrategy):
            raise ValueError(
                "Expected MaterialPublishStrategy instance for publish_strategy argument, but %s found"
                % type(publish_strategy))
        if items is not None:
            items = list(items)
            for item in items:
                if not isinstance(item, MaterialItem):
                    raise ValueError("Expected MaterialItem instances in items argument, but %s found" % type(item))
                if not isinstance(item.type, MaterialItemType):
                    raise ValueError(
                        "Expected MaterialItemType instance for MaterialItem.type, but %s found" % type(item.type))
            # Compact separators: the docs cap items at 262144 characters.
            items = json.dumps([item.to_json() for item in items], separators=(',', ':'))
        response = self._request_ok_or_raise(
            self._PROBLEM_SET_MATERIAL,
            args={
                'problemId': problem_id,
                'name': name,
                'originalName': original_name,
                'publishStrategy': publish_strategy,
                'items': items,
                'remove': remove,
                'pin': pin,
            },
        )
        return response.result

    def problem_packages(self, problem_id, pin=None):
        """
        Returns list of packages
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_PACKAGES,
            args={'problemId': problem_id, 'pin': pin},
        )
        return [Package.from_json(js) for js in response.result]

    def problem_package(self, problem_id, package_id, type=None, pin=None):
        return self._request_raw(
            self._PROBLEM_PACKAGE,
            args={
                'problemId': problem_id,
                'packageId': package_id,
                'type': type,
                'pin': pin,
            },
        )

    def problem_build_package(self, problem_id, verify, full, pin=None):
        """
        Start building a package
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_BUILD_PACKAGE,
            args={
                'problemId': problem_id,
                'verify': verify,
                'full': full,
                'pin': pin,
            }
        )
        return response.result

    def problem_invocations(self, problem_id, package_id=None, pin=None):
        """
        Returns the invocations of the working copy, the newest first: the solution runs started on
        the Invocations page and the verification runs of packages. With package_id, only the
        verification of that package, one invocation per verified testset
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_INVOCATIONS,
            args={
                'problemId': problem_id,
                'packageId': package_id,
                'pin': pin,
            },
        )
        return [Invocation.from_json(js) for js in response.result]

    def problem_invocation(self, problem_id, invocation_id, pin=None):
        """
        Returns an invocation with the runs of its solutions on its tests stored so far. They are
        complete only once the invocation is FINISHED and has a run for each solution and test
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_INVOCATION,
            args={
                'problemId': problem_id,
                'invocationId': invocation_id,
                'pin': pin,
            },
        )
        return InvocationResults.from_json(response.result)

    def problem_stresses(self, problem_id, stress_index=None, pin=None):
        """
        Returns the stresses of the problem with the latest run of each, in the order of their
        indices. With stress_index, only that stress, still in a list: use it to poll a running stress
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_STRESSES,
            args={
                'problemId': problem_id,
                'stressIndex': stress_index,
                'pin': pin,
            },
        )
        return [Stress.from_json(js) for js in response.result]

    def problem_save_stress(self, problem_id, stress_index=None, script_pattern=None, solution_names=None,
                            time_limit=None, memory_limit=None, total_time_limit=None, testset=None, group=None,
                            ignore_validators=None, description=None, pin=None):
        """
        Creates a stress when stress_index is None, which needs script_pattern and solution_names, or
        updates the stress with that index, keeping the values left as None; an empty testset,
        group or description clears it. Returns the saved Stress without a run: every save discards
        the result of the previous run
        """
        if stress_index is None and (script_pattern is None or solution_names is None):
            raise ValueError("Both script_pattern and solution_names must be specified to create a stress")
        solution_names = _comma_separated(solution_names)
        response = self._request_ok_or_raise(
            self._PROBLEM_SAVE_STRESS,
            args={
                'problemId': problem_id,
                'stressIndex': stress_index,
                'scriptPattern': script_pattern,
                'solutionNames': solution_names,
                'timeLimit': time_limit,
                'memoryLimit': memory_limit,
                'totalTimeLimit': total_time_limit,
                'testset': testset,
                'group': group,
                'ignoreValidators': ignore_validators,
                'description': description,
                'pin': pin,
            },
        )
        return Stress.from_json(response.result)

    def problem_delete_stress(self, problem_id, stress_index, pin=None):
        """
        Deletes a stress and the result of its run; the tests added from it are kept. A running
        stress is not cancelled: call problem.cancelStresses first to free the invokers
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_DELETE_STRESS,
            args={
                'problemId': problem_id,
                'stressIndex': stress_index,
                'pin': pin,
            },
        )
        return response.result

    def problem_run_stresses(self, problem_id, stress_indices=None, pin=None):
        """
        Starts the stresses with the given indices, or all stresses of the problem, with the current
        files of the working copy, and returns at once: poll problem.stresses for the results. A
        PENDING or RUNNING stress is not restarted
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_RUN_STRESSES,
            args={
                'problemId': problem_id,
                'stressIndices': _comma_separated(stress_indices),
                'pin': pin,
            },
        )
        return response.result

    def problem_cancel_stresses(self, problem_id, stress_indices=None, pin=None):
        """
        Cancels the runs of the stresses with the given indices, or of all stresses of the problem,
        removing their results. Stresses that are not running keep their finished results
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_CANCEL_STRESSES,
            args={
                'problemId': problem_id,
                'stressIndices': _comma_separated(stress_indices),
                'pin': pin,
            },
        )
        return response.result

    def problem_add_stress_countertest(self, problem_id, stress_index, testset, pin=None):
        """
        Adds the countertest found by the latest finished run of a stress to the tests of a testset,
        generated by its script line, and returns the added test. A small input may be stored as a
        manual test
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_ADD_STRESS_COUNTERTEST,
            args={
                'problemId': problem_id,
                'stressIndex': stress_index,
                'testset': testset,
                'pin': pin,
            },
        )
        return Test.from_json(self, problem_id, testset, response.result, pin)

    def problem_cautions(self, problem_id, pin=None):
        """
        Returns structured cautions, package readiness issues and cached AI tips of the problem
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_CAUTIONS,
            args={'problemId': problem_id, 'pin': pin},
        )
        return ProblemCautions.from_json(response.result)

    def problem_issues(self, problem_id, pin=None):
        """
        Returns the issues of the problem with their comments, the most recently changed issue first
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_ISSUES,
            args={'problemId': problem_id, 'pin': pin},
        )
        return [Issue.from_json(js) for js in response.result]

    def problem_add_issue(self, problem_id, issue_type, content, assignee=None, pin=None):
        """
        Creates an issue with Markdown content and returns it. Applies at once, problem.commitChanges
        is not needed
        """
        if not isinstance(issue_type, IssueType):
            raise ValueError(
                "Expected IssueType instance for issue_type argument, but %s found" % type(issue_type))
        response = self._request_ok_or_raise(
            self._PROBLEM_ADD_ISSUE,
            args={
                'problemId': problem_id,
                'type': issue_type,
                'content': content,
                'assignee': assignee,
                'pin': pin,
            },
        )
        return Issue.from_json(response.result)

    def problem_update_issue(self, problem_id, issue_id, comment=None, status=None, issue_type=None, assignee=None,
                             pin=None):
        """
        Comments on an issue and/or changes its status, type and assignee, and returns the updated
        issue. A change left as None is not made; an empty assignee unassigns the issue. Applies at
        once, problem.commitChanges is not needed
        """
        if status is not None and not isinstance(status, IssueStatus):
            raise ValueError(
                "Expected IssueStatus instance for status argument, but %s found" % type(status))
        if issue_type is not None and not isinstance(issue_type, IssueType):
            raise ValueError(
                "Expected IssueType instance for issue_type argument, but %s found" % type(issue_type))
        response = self._request_ok_or_raise(
            self._PROBLEM_UPDATE_ISSUE,
            args={
                'problemId': problem_id,
                'issueId': issue_id,
                'comment': comment,
                'status': status,
                'type': issue_type,
                'assignee': assignee,
                'pin': pin,
            },
        )
        return Issue.from_json(response.result)

    def problem_accesses(self, problem_id, pin=None):
        """
        Returns the direct access-control entries of the problem, users and user groups alike
        """
        response = self._request_ok_or_raise(
            self._PROBLEM_ACCESSES,
            args={'problemId': problem_id, 'pin': pin},
        )
        return [ProblemAccess.from_json(js) for js in response.result]

    def problem_set_access(self, problem_id, login, access_type, pin=None):
        """
        Sets the direct access of one user to the problem, ProblemAccessType.NONE removing it
        """
        if not isinstance(access_type, ProblemAccessType):
            raise ValueError(
                "Expected ProblemAccessType instance for access_type argument, but %s found" % type(access_type))
        response = self._request_ok_or_raise(
            self._PROBLEM_SET_ACCESS,
            args={
                'problemId': problem_id,
                'login': login,
                'accessType': access_type,
                'pin': pin,
            },
        )
        return response.result

    def contest_problems(self, contest_id, pin=None):
        """
        """
        response = self._request_ok_or_raise(
            self._CONTEST_PROBLEMS,
            args={'contestId': contest_id, 'pin': pin},
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

    def _request_text(self, method_name, args=None):
        request = Request(self.request_config, method_name, args)
        return request.issue_text()

    def _request_raw(self, method_name, args=None):
        request = Request(self.request_config, method_name, args)
        return request.issue_raw()

    def _request_body(self, method_name, args=None, binary=False):
        if binary:
            return self._request_raw(method_name, args)
        return self._request_text(method_name, args)


class Problem:
    """
    Object representing Polygon problem
    """

    # JSON field names
    _ID_FIELD = 'id'
    _OWNER_FIELD = 'owner'
    _NAME_FIELD = 'name'
    _NOTE_FIELD = 'note'
    _DELETED_FIELD = 'deleted'
    _FAVORITE_FIELD = 'favourite'
    _ACCESS_TYPE_FIELD = 'accessType'
    _REVISION_FIELD = 'revision'
    _WORKING_COPY_REVISION_FIELD = 'workingCopyRevision'
    _LATEST_PACKAGE_FIELD = 'latestPackage'
    _MODIFIED_FIELD = 'modified'

    @classmethod
    def from_json(cls, polygon, problem_json):
        access_type = problem_json.get(Problem._ACCESS_TYPE_FIELD)
        return cls(
            polygon=polygon,
            problem_id=problem_json.get(Problem._ID_FIELD),
            owner=problem_json.get(Problem._OWNER_FIELD),
            name=problem_json.get(Problem._NAME_FIELD),
            deleted=problem_json.get(Problem._DELETED_FIELD),
            favorite=problem_json.get(Problem._FAVORITE_FIELD),
            access_type=None if access_type is None else ProblemAccessType[access_type],
            revision=problem_json.get(Problem._REVISION_FIELD),
            latest_package=problem_json.get(Problem._LATEST_PACKAGE_FIELD),
            modified=problem_json.get(Problem._MODIFIED_FIELD),
            note=problem_json.get(Problem._NOTE_FIELD),
            working_copy_revision=problem_json.get(Problem._WORKING_COPY_REVISION_FIELD),
        )

    def __init__(self, polygon, problem_id, owner, name, deleted, favorite, access_type, revision, latest_package,
                 modified, note=None, working_copy_revision=None, pin=None):
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
        self.note = note
        self.working_copy_revision = working_copy_revision
        self.pin = pin

    def __str__(self):
        return '{}:{}'.format(self.name, self.id)

    def _resolve_pin(self, pin):
        """
        The pin to send: the one passed to a single call wins, otherwise the pin of the problem.
        """
        return self.pin if pin is None else pin

    def info(self, pin=None):
        return self._polygon.problem_info(self.id, pin=self._resolve_pin(pin))

    def update_info(self, problem_info, pin=None):
        return self._polygon.problem_update_info(self.id, problem_info, pin=self._resolve_pin(pin))

    def view_note(self, pin=None):
        """
        Calls problem.note. The note attribute holds the note that came with the problem object
        """
        return self._polygon.problem_view_note(self.id, pin=self._resolve_pin(pin))

    def save_note(self, note, pin=None):
        return self._polygon.problem_save_note(self.id, note, pin=self._resolve_pin(pin))

    def update_working_copy(self, pin=None):
        return self._polygon.problem_update_working_copy(self.id, pin=self._resolve_pin(pin))

    def discard_working_copy(self, pin=None):
        return self._polygon.problem_discard_working_copy(self.id, pin=self._resolve_pin(pin))

    def commit_changes(self, minor_changes=None, message=None, pin=None):
        return self._polygon.problem_commit_changes(self.id, minor_changes, message,
                                                    pin=self._resolve_pin(pin))

    def tags(self, pin=None):
        return self._polygon.problem_view_tags(self.id, pin=self._resolve_pin(pin))

    def save_tags(self, tags, pin=None):
        return self._polygon.problem_save_tags(self.id, tags, pin=self._resolve_pin(pin))

    def general_description(self, pin=None):
        return self._polygon.problem_view_general_description(self.id, pin=self._resolve_pin(pin))

    def save_general_description(self, description, pin=None):
        return self._polygon.problem_save_general_description(self.id, description, pin=self._resolve_pin(pin))

    def general_tutorial(self, pin=None):
        return self._polygon.problem_view_general_tutorial(self.id, pin=self._resolve_pin(pin))

    def save_general_tutorial(self, tutorial, pin=None):
        return self._polygon.problem_save_general_tutorial(self.id, tutorial, pin=self._resolve_pin(pin))

    def statements(self, pin=None):
        return self._polygon.problem_statements(self.id, pin=self._resolve_pin(pin))

    def render_statements(self, include_content=None, pin=None):
        return self._polygon.problem_render_statements(self.id, include_content, pin=self._resolve_pin(pin))

    def save_statement(self, lang, problem_statement, pin=None):
        return self._polygon.problem_save_statement(self.id, lang, problem_statement, pin=self._resolve_pin(pin))

    def delete_statement(self, lang, pin=None):
        return self._polygon.problem_delete_statement(self.id, lang, pin=self._resolve_pin(pin))

    def statement_resources(self, pin=None):
        return self._polygon.problem_statement_resources(self.id, pin=self._resolve_pin(pin))

    def view_statement_resource(self, name, binary=False, pin=None):
        return self._polygon.problem_view_statement_resource(self.id, name, binary, pin=self._resolve_pin(pin))

    def save_statement_resource(self, name, file, check_existing=None, pin=None):
        return self._polygon.problem_save_statement_resource(self.id, name, file, check_existing,
                                                             pin=self._resolve_pin(pin))

    def delete_statement_resource(self, name, pin=None):
        return self._polygon.problem_delete_statement_resource(self.id, name, pin=self._resolve_pin(pin))

    def enable_groups(self, testset, enable, pin=None):
        return self._polygon.problem_enable_groups(self.id, testset, enable, pin=self._resolve_pin(pin))

    def enable_points(self, enable, pin=None):
        return self._polygon.problem_enable_points(self.id, enable, pin=self._resolve_pin(pin))

    def enable_treat_points_from_checker_as_percent(self, enable, pin=None):
        return self._polygon.problem_enable_treat_points_from_checker_as_percent(self.id, enable,
                                                                                 pin=self._resolve_pin(pin))

    def save_test(self, testset, test_index, test_input, test_group=None, test_points=None, test_description=None,
                  test_use_in_statements=None, test_input_for_statements=None, test_output_for_statements=None,
                  verify_input_output_for_statements=None, check_existing=None, pin=None):
        return self._polygon.problem_save_test(self.id, testset, test_index, test_input, test_group, test_points,
                                               test_description, test_use_in_statements, test_input_for_statements,
                                               test_output_for_statements, verify_input_output_for_statements,
                                               check_existing, pin=self._resolve_pin(pin))

    def delete_test(self, testset, test_index=None, test_indices=None, pin=None):
        return self._polygon.problem_delete_test(self.id, testset, test_index, test_indices,
                                                 pin=self._resolve_pin(pin))

    def set_test_group(self, testset, test_group, test_index=None, test_indices=None, pin=None):
        return self._polygon.problem_set_test_group(self.id, testset, test_group, test_index, test_indices,
                                                    pin=self._resolve_pin(pin))

    def tests(self, testset, no_inputs=None, pin=None):
        return self._polygon.problem_tests(self.id, testset, no_inputs, pin=self._resolve_pin(pin))

    def preview_tests(self, testset, pin=None):
        return self._polygon.problem_preview_tests(self.id, testset, pin=self._resolve_pin(pin))

    def save_test_group(self, testset, group, points_policy=None, feedback_policy=None, dependencies=None, pin=None):
        return self._polygon.problem_save_test_group(self.id, testset, group,
                                                     points_policy, feedback_policy, dependencies,
                                                     pin=self._resolve_pin(pin))

    def view_test_group(self, testset, group=None, pin=None):
        return self._polygon.problem_view_test_group(self.id, testset, group, pin=self._resolve_pin(pin))

    def view_file(self, type, name, binary=False, pin=None):
        return self._polygon.problem_view_file(self.id, type, name, binary, pin=self._resolve_pin(pin))

    def view_solution(self, name, binary=False, pin=None):
        return self._polygon.problem_view_solution(self.id, name, binary, pin=self._resolve_pin(pin))

    def save_file(self, type, name, file, source_type=None, resource_advanced_properties=None, check_existing=None,
                  pin=None):
        return self._polygon.problem_save_file(self.id, type, name, file, source_type,
                                               resource_advanced_properties, check_existing,
                                               pin=self._resolve_pin(pin))

    def delete_file(self, type, name, pin=None):
        return self._polygon.problem_delete_file(self.id, type, name, pin=self._resolve_pin(pin))

    def save_solution(self, name, file, tag, source_type=None, check_existing=None, pin=None):
        return self._polygon.problem_save_solution(self.id, name, file, tag, source_type, check_existing,
                                                   pin=self._resolve_pin(pin))

    def delete_solution(self, name, pin=None):
        return self._polygon.problem_delete_solution(self.id, name, pin=self._resolve_pin(pin))

    def edit_solution_extra_tags(self, remove, name, testset=None, test_group=None, tag=None, pin=None):
        return self._polygon.problem_edit_solution_extra_tags(self.id, remove, name, testset, test_group, tag,
                                                              pin=self._resolve_pin(pin))

    def checker(self, pin=None):
        return self._polygon.problem_checker(self.id, pin=self._resolve_pin(pin))

    def set_checker(self, checker, pin=None):
        return self._polygon.problem_set_checker(self.id, checker, pin=self._resolve_pin(pin))

    def checker_tests(self, pin=None):
        return self._polygon.problem_checker_tests(self.id, pin=self._resolve_pin(pin))

    def save_checker_test(self, test_index, test_input=None, test_output=None,
                          test_answer=None, test_verdict=None, check_existing=None, pin=None):
        return self._polygon.problem_save_checker_test(self.id, test_index, test_input, test_output,
                                                       test_answer, test_verdict, check_existing,
                                                       pin=self._resolve_pin(pin))

    def delete_checker_test(self, test_index, pin=None):
        return self._polygon.problem_delete_checker_test(self.id, test_index, pin=self._resolve_pin(pin))

    def validator(self, pin=None):
        return self._polygon.problem_validator(self.id, pin=self._resolve_pin(pin))

    def set_validator(self, validator, pin=None):
        return self._polygon.problem_set_validator(self.id, validator, pin=self._resolve_pin(pin))

    def validator_tests(self, pin=None):
        return self._polygon.problem_validator_tests(self.id, pin=self._resolve_pin(pin))

    def save_validator_test(self, test_index, test_input=None, test_verdict=None,
                            test_group=None, testset=None, check_existing=None, pin=None):
        return self._polygon.problem_save_validator_test(self.id, test_index, test_input, test_verdict,
                                                         test_group, testset, check_existing,
                                                         pin=self._resolve_pin(pin))

    def delete_validator_test(self, test_index, pin=None):
        return self._polygon.problem_delete_validator_test(self.id, test_index, pin=self._resolve_pin(pin))

    def extra_validators(self, pin=None):
        return self._polygon.problem_extra_validators(self.id, pin=self._resolve_pin(pin))

    def interactor(self, pin=None):
        return self._polygon.problem_interactor(self.id, pin=self._resolve_pin(pin))

    def set_interactor(self, interactor, pin=None):
        return self._polygon.problem_set_interactor(self.id, interactor, pin=self._resolve_pin(pin))

    def solutions(self, pin=None):
        return self._polygon.problem_solutions(self.id, pin=self._resolve_pin(pin))

    def files(self, pin=None):
        return self._polygon.problem_files(self.id, pin=self._resolve_pin(pin))

    def files_resource(self, pin=None):
        return self.files(pin)[FileType.RESOURCE]

    def files_source(self, pin=None):
        return self.files(pin)[FileType.SOURCE]

    def files_aux(self, pin=None):
        return self.files(pin)[FileType.AUX]

    def script(self, testset, pin=None):
        return self._polygon.problem_script(self.id, testset, pin=self._resolve_pin(pin))

    def clear_script(self, testset, pin=None):
        return self._polygon.problem_clear_script(self.id, testset, pin=self._resolve_pin(pin))

    def test_input(self, testset, test_index, binary=False, pin=None):
        return self._polygon.problem_test_input(self.id, testset, test_index, binary, pin=self._resolve_pin(pin))

    def test_answer(self, testset, test_index, binary=False, pin=None):
        return self._polygon.problem_test_answer(self.id, testset, test_index, binary, pin=self._resolve_pin(pin))

    def save_script(self, testset, source, pin=None):
        return self._polygon.problem_save_script(self.id, testset, source, pin=self._resolve_pin(pin))

    def materials(self, pin=None):
        return self._polygon.problem_materials(self.id, pin=self._resolve_pin(pin))

    def set_material(self, name, publish_strategy=None, items=None, original_name=None, remove=None, pin=None):
        return self._polygon.problem_set_material(self.id, name, publish_strategy, items, original_name, remove,
                                                  pin=self._resolve_pin(pin))

    def packages(self, pin=None):
        return self._polygon.problem_packages(self.id, pin=self._resolve_pin(pin))

    def package(self, package_id, type=None, pin=None):
        return self._polygon.problem_package(self.id, package_id, type, pin=self._resolve_pin(pin))

    def build_package(self, verify, full, pin=None):
        return self._polygon.problem_build_package(self.id, verify, full, pin=self._resolve_pin(pin))

    def invocations(self, package_id=None, pin=None):
        return self._polygon.problem_invocations(self.id, package_id, pin=self._resolve_pin(pin))

    def invocation(self, invocation_id, pin=None):
        return self._polygon.problem_invocation(self.id, invocation_id, pin=self._resolve_pin(pin))

    def stresses(self, stress_index=None, pin=None):
        return self._polygon.problem_stresses(self.id, stress_index, pin=self._resolve_pin(pin))

    def save_stress(self, stress_index=None, script_pattern=None, solution_names=None, time_limit=None,
                    memory_limit=None, total_time_limit=None, testset=None, group=None, ignore_validators=None,
                    description=None, pin=None):
        return self._polygon.problem_save_stress(self.id, stress_index, script_pattern, solution_names, time_limit,
                                                 memory_limit, total_time_limit, testset, group, ignore_validators,
                                                 description, pin=self._resolve_pin(pin))

    def delete_stress(self, stress_index, pin=None):
        return self._polygon.problem_delete_stress(self.id, stress_index, pin=self._resolve_pin(pin))

    def run_stresses(self, stress_indices=None, pin=None):
        return self._polygon.problem_run_stresses(self.id, stress_indices, pin=self._resolve_pin(pin))

    def cancel_stresses(self, stress_indices=None, pin=None):
        return self._polygon.problem_cancel_stresses(self.id, stress_indices, pin=self._resolve_pin(pin))

    def add_stress_countertest(self, stress_index, testset, pin=None):
        return self._polygon.problem_add_stress_countertest(self.id, stress_index, testset,
                                                            pin=self._resolve_pin(pin))

    def cautions(self, pin=None):
        return self._polygon.problem_cautions(self.id, pin=self._resolve_pin(pin))

    def issues(self, pin=None):
        return self._polygon.problem_issues(self.id, pin=self._resolve_pin(pin))

    def add_issue(self, issue_type, content, assignee=None, pin=None):
        return self._polygon.problem_add_issue(self.id, issue_type, content, assignee, pin=self._resolve_pin(pin))

    def update_issue(self, issue_id, comment=None, status=None, issue_type=None, assignee=None, pin=None):
        return self._polygon.problem_update_issue(self.id, issue_id, comment, status, issue_type, assignee,
                                                  pin=self._resolve_pin(pin))

    def accesses(self, pin=None):
        return self._polygon.problem_accesses(self.id, pin=self._resolve_pin(pin))

    def set_access(self, login, access_type, pin=None):
        return self._polygon.problem_set_access(self.id, login, access_type, pin=self._resolve_pin(pin))


class ProblemInfo:
    """
    Object representing Polygon problem info
    """

    # JSON field names
    _INPUT_FILE = 'inputFile'
    _OUTPUT_FILE = 'outputFile'
    _INTERACTIVE = 'interactive'
    _WELL_FORMED = 'wellFormed'
    _SKIP_DUPLICATED_TESTS_VALIDATION = 'skipDuplicatedTestsValidation'
    _USE_INTERACTION_LOG_IN_EXAMPLE_TESTS = 'useInteractionLogInExampleTests'
    _RUN_TWICE = 'runTwice'
    _INTERACTIVE_SECOND_RUN = 'interactiveSecondRun'
    _TIME_LIMIT = 'timeLimit'
    _MEMORY_LIMIT = 'memoryLimit'

    @classmethod
    def from_json(cls, problem_info_json):
        return cls(
            input_file=problem_info_json[ProblemInfo._INPUT_FILE],
            output_file=problem_info_json[ProblemInfo._OUTPUT_FILE],
            interactive=problem_info_json[ProblemInfo._INTERACTIVE],
            well_formed=problem_info_json.get(ProblemInfo._WELL_FORMED, None),
            skip_duplicated_tests_validation=problem_info_json.get(
                ProblemInfo._SKIP_DUPLICATED_TESTS_VALIDATION, None),
            time_limit=problem_info_json[ProblemInfo._TIME_LIMIT],
            memory_limit=problem_info_json[ProblemInfo._MEMORY_LIMIT],
            # The docs give useInteractionLogInExampleTests and interactiveSecondRun only for
            # interactive problems, so all three are read leniently like the flags above.
            use_interaction_log_in_example_tests=problem_info_json.get(
                ProblemInfo._USE_INTERACTION_LOG_IN_EXAMPLE_TESTS, None),
            run_twice=problem_info_json.get(ProblemInfo._RUN_TWICE, None),
            interactive_second_run=problem_info_json.get(ProblemInfo._INTERACTIVE_SECOND_RUN, None),
        )

    def __init__(self, input_file=None, output_file=None, interactive=None, time_limit=None, memory_limit=None,
                 well_formed=None, skip_duplicated_tests_validation=None, use_interaction_log_in_example_tests=None,
                 run_twice=None, interactive_second_run=None):
        self.input_file = input_file
        self.output_file = output_file
        self.interactive = interactive
        self.time_limit = time_limit
        self.memory_limit = memory_limit
        self.well_formed = well_formed
        self.skip_duplicated_tests_validation = skip_duplicated_tests_validation
        self.use_interaction_log_in_example_tests = use_interaction_log_in_example_tests
        self.run_twice = run_twice
        self.interactive_second_run = interactive_second_run


class CommitResult:
    """
    Object: representing the result of a problem.commitChanges call
    """
    _COMMITTED = "committed"
    _CONFLICT_OCCURRED = "conflictOccurred"
    _MESSAGE = "message"

    @classmethod
    def from_json(cls, commit_result_json):
        return cls(
            committed=commit_result_json[CommitResult._COMMITTED],
            conflict_occurred=commit_result_json[CommitResult._CONFLICT_OCCURRED],
            message=commit_result_json[CommitResult._MESSAGE],
        )

    def __init__(self, committed, conflict_occurred, message):
        self.committed = committed
        self.conflict_occurred = conflict_occurred
        self.message = message


class Test:
    _INDEX = "index"
    _MANUAL = "manual"
    _INPUT = "input"
    _INPUT_BASE64 = "inputBase64"
    _DESCRIPTION = "description"
    _USE_IN_STATEMENTS = "useInStatements"
    _SCRIPT_LINE = "scriptLine"
    _GROUP = "group"
    _POINTS = "points"
    _INPUT_FOR_STATEMENTS = "inputForStatement"
    _OUTPUT_FOR_STATEMENTS = "outputForStatement"
    _VERIFY_INPUT_OUTPUT_FOR_STATEMENTS = "verifyInputOutputForStatements"

    @classmethod
    def from_json(cls, polygon, problem_id, testset, test_json, pin=None):
        if test_json['manual']:
            return ManualTest.from_json(polygon, problem_id, testset, test_json, pin)
        else:
            return GeneratedTest.from_json(polygon, problem_id, testset, test_json, pin)

    def __init__(self, polygon, problem_id, testset, index, group, points, description, use_in_statements,
                 input_for_statements, output_for_statements, verify_input_output_for_statements, pin=None):
        self._polygon = polygon
        self._problem_id = problem_id
        self.testset = testset
        self.index = index
        self.group = group
        self.points = points
        self.description = description
        self.use_in_statements = use_in_statements
        self.input_for_statements = input_for_statements
        self.output_for_statements = output_for_statements
        self.verify_input_output_for_statements = verify_input_output_for_statements
        self.pin = pin

    def _resolve_pin(self, pin):
        """
        The pin to send: the one passed to a single call wins, otherwise the pin of the test.
        """
        return self.pin if pin is None else pin


class ManualTest(Test):

    @classmethod
    def from_json(cls, polygon, problem_id, testset, test_json, pin=None):
        input_base64 = test_json.get(Test._INPUT_BASE64, None)
        return cls(
            polygon=polygon,
            problem_id=problem_id,
            testset=testset,
            index=int(test_json[Test._INDEX]),
            input=test_json.get(Test._INPUT, None),
            input_bytes=None if input_base64 is None else base64.b64decode(input_base64),
            group=test_json.get(Test._GROUP, ""),
            points=float(test_json.get(Test._POINTS, "0")),
            description=test_json.get(Test._DESCRIPTION, None),
            use_in_statements=test_json[Test._USE_IN_STATEMENTS],
            input_for_statements=test_json.get(Test._INPUT_FOR_STATEMENTS, None),
            output_for_statements=test_json.get(Test._OUTPUT_FOR_STATEMENTS, None),
            verify_input_output_for_statements=test_json.get(Test._VERIFY_INPUT_OUTPUT_FOR_STATEMENTS, None),
            pin=pin,
        )

    def __init__(self, polygon, problem_id, testset, index, input, group=None, points=None, description=None,
                 use_in_statements=None, input_for_statements=None, output_for_statements=None,
                 verify_input_output_for_statements=None, input_bytes=None, pin=None):
        super().__init__(polygon, problem_id, testset, index, group, points, description, use_in_statements,
                         input_for_statements, output_for_statements, verify_input_output_for_statements, pin)
        self.input = input
        self.input_bytes = input_bytes

    def save(self, pin=None):
        return self._polygon.problem_save_test(self._problem_id, self.testset, self.index, self.input,
                                               self.group, self.points, self.description, self.use_in_statements,
                                               self.input_for_statements, self.output_for_statements,
                                               self.verify_input_output_for_statements,
                                               pin=self._resolve_pin(pin))


class GeneratedTest(Test):
    @classmethod
    def from_json(cls, polygon, problem_id, testset, test_json, pin=None):
        return cls(
            polygon=polygon,
            problem_id=problem_id,
            testset=testset,
            index=int(test_json[Test._INDEX]),
            group=test_json.get(Test._GROUP, ""),
            points=float(test_json.get(Test._POINTS, "0")),
            description=test_json.get(Test._DESCRIPTION, None),
            use_in_statements=test_json[Test._USE_IN_STATEMENTS],
            script_line=test_json[Test._SCRIPT_LINE],
            input_for_statements=test_json.get(Test._INPUT_FOR_STATEMENTS, None),
            output_for_statements=test_json.get(Test._OUTPUT_FOR_STATEMENTS, None),
            verify_input_output_for_statements=test_json.get(Test._VERIFY_INPUT_OUTPUT_FOR_STATEMENTS, None),
            pin=pin,
        )

    def __init__(self, polygon, problem_id, testset, index, group, points, description, use_in_statements, script_line,
                 input_for_statements, output_for_statements, verify_input_output_for_statements, pin=None):
        super().__init__(polygon, problem_id, testset, index, group, points, description, use_in_statements,
                         input_for_statements, output_for_statements, verify_input_output_for_statements, pin)
        self.script_line = script_line


class TestPreview:
    """
    Object: representing the preview of one test, as returned by problem.previewTests
    """
    _ID = "id"
    _SESSION = "session"
    _CREATION_TIME = "creationTime"
    _UPDATE_TIME = "updateTime"
    _PROBLEM_ID = "problemId"
    _TESTSET = "testset"
    _TEST_INDEX = "testIndex"
    _DESCRIPTION = "description"
    _USE_IN_STATEMENTS = "useInStatements"
    _INPUT = "input"
    _INPUT_SHA1 = "inputSha1"
    _ANSWER = "answer"
    _CHANGE_AFTER_LAST_GENERATE = "changeAfterLastGenerate"
    _TEST_OVERVIEW_LOG = "testOverviewLog"

    @classmethod
    def from_json(cls, preview_json):
        return cls(
            preview_id=preview_json.get(TestPreview._ID, None),
            session=preview_json[TestPreview._SESSION],
            # Kept as the strings Polygon sends: the docs call them legacy Gson date strings, whose
            # format is not pinned down, so parsing them could fail on a server-side change.
            creation_time=preview_json.get(TestPreview._CREATION_TIME, None),
            update_time=preview_json.get(TestPreview._UPDATE_TIME, None),
            problem_id=preview_json[TestPreview._PROBLEM_ID],
            testset=preview_json[TestPreview._TESTSET],
            test_index=preview_json[TestPreview._TEST_INDEX],
            description=preview_json.get(TestPreview._DESCRIPTION, None),
            use_in_statements=preview_json[TestPreview._USE_IN_STATEMENTS],
            input=preview_json.get(TestPreview._INPUT, None),
            input_sha1=preview_json.get(TestPreview._INPUT_SHA1, None),
            answer=preview_json.get(TestPreview._ANSWER, None),
            change_after_last_generate=preview_json[TestPreview._CHANGE_AFTER_LAST_GENERATE],
            test_overview_log=preview_json.get(TestPreview._TEST_OVERVIEW_LOG, None),
        )

    def __init__(self, session, problem_id, testset, test_index, use_in_statements, change_after_last_generate,
                 preview_id=None, creation_time=None, update_time=None, description=None, input=None,
                 input_sha1=None, answer=None, test_overview_log=None):
        self.id = preview_id
        self.session = session
        self.creation_time = creation_time
        self.update_time = update_time
        self.problem_id = problem_id
        self.testset = testset
        self.test_index = test_index
        self.description = description
        self.use_in_statements = use_in_statements
        self.input = input
        self.input_sha1 = input_sha1
        self.answer = answer
        self.change_after_last_generate = change_after_last_generate
        self.test_overview_log = test_overview_log


class DeleteTestsResult:
    """
    Object: representing the failure details of a problem.deleteTest call
    """
    _FAILURES = "failures"

    @classmethod
    def from_json(cls, result_json):
        return cls(
            failures=[TestDeletionFailure.from_json(js) for js in result_json[DeleteTestsResult._FAILURES]],
        )

    def __init__(self, failures):
        self.failures = failures


class TestDeletionFailure:
    """
    Object: representing a test that problem.deleteTest can not delete
    """
    _INDEX = "index"
    _REASON = "reason"
    _MESSAGE = "message"

    @classmethod
    def from_json(cls, failure_json):
        return cls(
            index=failure_json[TestDeletionFailure._INDEX],
            reason=TestDeletionFailureReason[failure_json[TestDeletionFailure._REASON]],
            message=failure_json[TestDeletionFailure._MESSAGE],
        )

    def __init__(self, index, reason, message):
        self.index = index
        self.reason = reason
        self.message = message


class TestGroup:
    """
    """
    _NAME = "name"
    _POINTS_POLICY = "pointsPolicy"
    _FEEDBACK_POLICY = "feedbackPolicy"
    _DEPENDENCIES = "dependencies"

    @classmethod
    def from_json(cls, test_group_json):
        return cls(
            name=test_group_json[TestGroup._NAME],
            points_policy=PointsPolicy[test_group_json[TestGroup._POINTS_POLICY]],
            feedback_policy=FeedbackPolicy[test_group_json[TestGroup._FEEDBACK_POLICY]],
            dependencies=test_group_json[TestGroup._DEPENDENCIES],
        )

    def __init__(self, name, points_policy=None, feedback_policy=None, dependencies=None):
        self.name = name
        if points_policy is not None and not isinstance(points_policy, PointsPolicy):
            raise TypeError(
                "Expected PointsPolicy instance for points_policy argument, but %s found" % type(points_policy))
        if feedback_policy is not None and not isinstance(feedback_policy, FeedbackPolicy):
            raise TypeError(
                "Expected FeedbackPolicy instance for feedback_policy argument, but %s found" % type(feedback_policy))
        self.points_policy = points_policy
        self.feedback_policy = feedback_policy
        self.dependencies = dependencies


class Statement:
    """
    Object: representing Polygon problem statement
    """
    _ENCODING = "encoding"
    _NAME = "name"
    _LEGEND = "legend"
    _INPUT = "input"
    _OUTPUT = "output"
    _SCORING = "scoring"
    _INTERACTION = "interaction"
    _NOTES = "notes"
    _TUTORIAL = "tutorial"
    _SHOW_IN_REVIEW = "showInReview"
    _SHOW_CAUTIONS_AND_GRAMMATICAL_FIXES = "showCautionsAndGrammaticalFixes"

    @classmethod
    def from_json(cls, statement_json):
        return cls(
            encoding=statement_json[Statement._ENCODING],
            name=statement_json[Statement._NAME],
            legend=statement_json[Statement._LEGEND],
            input=statement_json[Statement._INPUT],
            output=statement_json[Statement._OUTPUT],
            scoring=statement_json.get(Statement._SCORING, None),
            interaction=statement_json.get(Statement._INTERACTION, None),
            notes=statement_json[Statement._NOTES],
            tutorial=statement_json[Statement._TUTORIAL],
            show_in_review=statement_json.get(Statement._SHOW_IN_REVIEW, None),
            show_cautions_and_grammatical_fixes=statement_json.get(
                Statement._SHOW_CAUTIONS_AND_GRAMMATICAL_FIXES, None),
        )

    def __init__(self, encoding=None, name=None, legend=None, input=None, output=None, scoring=None, interaction=None,
                 notes=None, tutorial=None, show_in_review=None, show_cautions_and_grammatical_fixes=None):
        self.encoding = encoding
        self.name = name
        self.legend = legend
        self.input = input
        self.output = output
        self.scoring = scoring
        self.interaction = interaction
        self.notes = notes
        self.tutorial = tutorial
        self.show_in_review = show_in_review
        self.show_cautions_and_grammatical_fixes = show_cautions_and_grammatical_fixes


class RenderResult:
    """
    Object: representing one HTML or PDF render of a statement or a tutorial
    """
    _STATUS = "status"
    _SHA256 = "sha256"
    _SIZE_BYTES = "sizeBytes"
    _CONTENT_BASE64 = "contentBase64"
    _MESSAGE = "message"

    @classmethod
    def from_json(cls, render_result_json):
        content_base64 = render_result_json.get(RenderResult._CONTENT_BASE64, None)
        return cls(
            status=RenderStatus[render_result_json[RenderResult._STATUS]],
            sha256=render_result_json.get(RenderResult._SHA256, None),
            size_bytes=render_result_json.get(RenderResult._SIZE_BYTES, None),
            content_bytes=None if content_base64 is None else base64.b64decode(content_base64),
            message=render_result_json.get(RenderResult._MESSAGE, None),
        )

    def __init__(self, status, sha256=None, size_bytes=None, content_bytes=None, message=None):
        self.status = status
        self.sha256 = sha256
        self.size_bytes = size_bytes
        self.content_bytes = content_bytes
        self.message = message


class RenderedStatement:
    """
    Object: representing the rendered files of one statement or tutorial language
    """
    _LANGUAGE = "language"
    _HTML = "html"
    _PDF = "pdf"

    @classmethod
    def from_json(cls, rendered_statement_json):
        return cls(
            language=rendered_statement_json[RenderedStatement._LANGUAGE],
            html=RenderResult.from_json(rendered_statement_json[RenderedStatement._HTML]),
            pdf=RenderResult.from_json(rendered_statement_json[RenderedStatement._PDF]),
        )

    def __init__(self, language, html, pdf):
        self.language = language
        self.html = html
        self.pdf = pdf


class RenderStatements:
    """
    Object: representing rendered statements and tutorials of a problem's current working copy
    """
    _REVISION = "revision"
    _RENDERING_TIME_SECONDS = "renderingTimeSeconds"
    _STATEMENTS = "statements"
    _TUTORIALS = "tutorials"

    @classmethod
    def from_json(cls, render_statements_json):
        def rendered(field):
            return [RenderedStatement.from_json(js) for js in render_statements_json[field]]

        return cls(
            revision=render_statements_json[RenderStatements._REVISION],
            rendering_time_seconds=render_statements_json[RenderStatements._RENDERING_TIME_SECONDS],
            statements=rendered(RenderStatements._STATEMENTS),
            tutorials=rendered(RenderStatements._TUTORIALS),
        )

    def __init__(self, revision, rendering_time_seconds, statements, tutorials):
        self.revision = revision
        self.rendering_time_seconds = rendering_time_seconds
        self.statements = statements
        self.tutorials = tutorials


class Material:
    """
    Object: representing one publishable material of a Polygon problem
    """
    _NAME = "name"
    _PUBLISH_STRATEGY = "publishStrategy"
    _ITEMS = "items"

    @classmethod
    def from_json(cls, material_json):
        return cls(
            name=material_json[Material._NAME],
            publish_strategy=MaterialPublishStrategy[material_json[Material._PUBLISH_STRATEGY]],
            items=[MaterialItem.from_json(js) for js in material_json[Material._ITEMS]],
        )

    def __init__(self, name, publish_strategy, items):
        self.name = name
        self.publish_strategy = publish_strategy
        self.items = items


class MaterialItem:
    """
    Object: representing one group of tests or files of a material. tests is set for TEST_INPUTS
    and TEST_ANSWERS, names (of files or solutions) for the other types
    """
    _TYPE = "type"
    _TESTS = "tests"
    _NAMES = "names"

    @classmethod
    def from_json(cls, item_json):
        tests = item_json.get(MaterialItem._TESTS, None)
        return cls(
            type=MaterialItemType[item_json[MaterialItem._TYPE]],
            tests=None if tests is None else [MaterialTest.from_json(js) for js in tests],
            names=item_json.get(MaterialItem._NAMES, None),
        )

    def __init__(self, type, tests=None, names=None):
        self.type = type
        self.tests = tests
        self.names = names

    def to_json(self):
        """The item as problem.setMaterial takes it, with only the lists that are set"""
        item_json = {MaterialItem._TYPE: str(self.type)}
        if self.tests is not None:
            item_json[MaterialItem._TESTS] = [test.to_json() for test in self.tests]
        if self.names is not None:
            item_json[MaterialItem._NAMES] = list(self.names)
        return item_json


class MaterialTest:
    """
    Object: representing one test selection of a material item: a single test by index, all
    tests of the testset, or (in TEST_ANSWERS) the selected input files reused as answers
    """
    _TESTSET = "testset"
    _INDEX = "index"
    _ALL = "all"
    _AS_INPUT = "asInput"

    @classmethod
    def from_json(cls, test_json):
        return cls(
            testset=test_json[MaterialTest._TESTSET],
            index=test_json.get(MaterialTest._INDEX, None),
            # problem.materials returns stored legacy materials unvalidated, and an omitted flag
            # means false, as it does on input to problem.setMaterial.
            all=test_json.get(MaterialTest._ALL, False),
            as_input=test_json.get(MaterialTest._AS_INPUT, False),
        )

    def __init__(self, testset, index=None, all=False, as_input=False):
        self.testset = testset
        self.index = index
        self.all = all
        self.as_input = as_input

    def to_json(self):
        """The selection as problem.setMaterial takes it, without the fields left at their defaults"""
        test_json = {MaterialTest._TESTSET: self.testset}
        if self.index is not None:
            test_json[MaterialTest._INDEX] = self.index
        if self.all:
            test_json[MaterialTest._ALL] = True
        if self.as_input:
            test_json[MaterialTest._AS_INPUT] = True
        return test_json


class Package:
    """
    Object: representing Polygon package
    """
    _ID = "id"
    _REVISION = "revision"
    _CREATION_TIME_SECONDS = "creationTimeSeconds"
    _STATE = "state"
    _COMMENT = "comment"
    _TYPE = "type"

    @classmethod
    def from_json(cls, package_json):
        return cls(
            id=package_json[Package._ID],
            revision=package_json[Package._REVISION],
            creation_time_seconds=package_json[Package._CREATION_TIME_SECONDS],
            state=PackageState[package_json[Package._STATE]],
            comment=package_json[Package._COMMENT],
            type=PackageType[package_json[Package._TYPE].upper()]
        )

    def __init__(self, id, revision, creation_time_seconds, state, comment, type):
        self.id = id
        self.revision = revision
        self.creation_time_seconds = creation_time_seconds
        self.state = state
        self.comment = comment
        self.type = type


class Invocation:
    """
    Object: representing an invocation: runs of solutions on the tests of a testset
    """
    _ID = "id"
    _DESCRIPTION = "description"
    _TESTSET = "testset"
    _STATUS = "status"
    _CREATION_TIME_SECONDS = "creationTimeSeconds"
    _PACKAGE_ID = "packageId"
    _VIOLATE_TAG = "violateTag"
    _SOLUTIONS = "solutions"
    _TESTS = "tests"

    @classmethod
    def from_json(cls, invocation_json):
        return cls(
            invocation_id=invocation_json[Invocation._ID],
            description=invocation_json[Invocation._DESCRIPTION],
            testset=invocation_json[Invocation._TESTSET],
            status=InvocationStatus[invocation_json[Invocation._STATUS]],
            creation_time_seconds=invocation_json[Invocation._CREATION_TIME_SECONDS],
            package_id=invocation_json.get(Invocation._PACKAGE_ID, None),
            violate_tag=invocation_json[Invocation._VIOLATE_TAG],
            solutions=invocation_json[Invocation._SOLUTIONS],
            tests=invocation_json[Invocation._TESTS],
        )

    def __init__(self, invocation_id, description, testset, status, creation_time_seconds, package_id,
                 violate_tag, solutions, tests):
        self.id = invocation_id
        self.description = description
        self.testset = testset
        self.status = status
        self.creation_time_seconds = creation_time_seconds
        self.package_id = package_id
        self.violate_tag = violate_tag
        self.solutions = solutions
        self.tests = tests


class SolutionTags:
    """
    Object: representing the tags of a solution as they were when an invocation started
    """
    _NAME = "name"
    _TAG = "tag"
    _TESTSET_TAGS = "testsetTags"
    _GROUP_TAGS = "groupTags"

    @classmethod
    def from_json(cls, tags_json):
        tag = tags_json.get(SolutionTags._TAG, None)

        def extra_tags(field):
            # The docs leave a mapping out when there are no extra tags, so absent reads as empty.
            return {name: SolutionTag[code] for name, code in tags_json.get(field, {}).items()}

        return cls(
            name=tags_json[SolutionTags._NAME],
            tag=None if tag is None else SolutionTag[tag],
            testset_tags=extra_tags(SolutionTags._TESTSET_TAGS),
            group_tags=extra_tags(SolutionTags._GROUP_TAGS),
        )

    def __init__(self, name, tag=None, testset_tags=None, group_tags=None):
        self.name = name
        self.tag = tag
        self.testset_tags = {} if testset_tags is None else testset_tags
        self.group_tags = {} if group_tags is None else group_tags


class InvocationRun:
    """
    Object: representing a stored run of a solution on a test of an invocation
    """
    _ID = "id"
    _SOLUTION = "solution"
    _TEST = "test"
    _VERDICT = "verdict"
    _TIME_MILLIS = "timeMillis"
    _MEMORY_BYTES = "memoryBytes"
    _POINTS = "points"
    _COMMENT = "comment"
    _VIOLATE_TAG = "violateTag"

    @classmethod
    def from_json(cls, run_json):
        points = run_json.get(InvocationRun._POINTS, None)
        return cls(
            run_id=run_json[InvocationRun._ID],
            solution=run_json.get(InvocationRun._SOLUTION, None),
            test=run_json[InvocationRun._TEST],
            verdict=InvocationRunVerdict[run_json[InvocationRun._VERDICT]],
            time_millis=run_json.get(InvocationRun._TIME_MILLIS, None),
            memory_bytes=run_json.get(InvocationRun._MEMORY_BYTES, None),
            # Read as a float like Test.points: the checker may return fractional points.
            points=None if points is None else float(points),
            comment=run_json.get(InvocationRun._COMMENT, None),
            violate_tag=run_json[InvocationRun._VIOLATE_TAG],
        )

    def __init__(self, run_id, solution, test, verdict, time_millis, memory_bytes, points, comment, violate_tag):
        self.id = run_id
        self.solution = solution
        self.test = test
        self.verdict = verdict
        self.time_millis = time_millis
        self.memory_bytes = memory_bytes
        self.points = points
        self.comment = comment
        self.violate_tag = violate_tag


class InvocationResults:
    """
    Object: representing the stored results of an invocation, as returned by problem.invocation
    """
    _INVOCATION = "invocation"
    _SOLUTION_TAGS = "solutionTags"
    _RUNS = "runs"

    @classmethod
    def from_json(cls, results_json):
        return cls(
            invocation=Invocation.from_json(results_json[InvocationResults._INVOCATION]),
            solution_tags=[SolutionTags.from_json(js) for js in results_json[InvocationResults._SOLUTION_TAGS]],
            runs=[InvocationRun.from_json(js) for js in results_json[InvocationResults._RUNS]],
        )

    def __init__(self, invocation, solution_tags, runs):
        self.invocation = invocation
        self.solution_tags = solution_tags
        self.runs = runs


class Stress:
    """
    Object: representing a stress of a Polygon problem, with the latest run of its current version
    """
    _INDEX = "index"
    _SCRIPT_PATTERN = "scriptPattern"
    _SOLUTION_NAMES = "solutionNames"
    _TIME_LIMIT = "timeLimit"
    _MEMORY_LIMIT = "memoryLimit"
    _TOTAL_TIME_LIMIT = "totalTimeLimit"
    _TESTSET = "testset"
    _GROUP = "group"
    _IGNORE_VALIDATORS = "ignoreValidators"
    _DESCRIPTION = "description"
    _RUN = "run"

    @classmethod
    def from_json(cls, stress_json):
        run = stress_json.get(Stress._RUN, None)
        return cls(
            index=stress_json[Stress._INDEX],
            script_pattern=stress_json[Stress._SCRIPT_PATTERN],
            solution_names=stress_json[Stress._SOLUTION_NAMES],
            time_limit=stress_json[Stress._TIME_LIMIT],
            memory_limit=stress_json[Stress._MEMORY_LIMIT],
            total_time_limit=stress_json[Stress._TOTAL_TIME_LIMIT],
            testset=stress_json.get(Stress._TESTSET, None),
            group=stress_json.get(Stress._GROUP, None),
            ignore_validators=stress_json[Stress._IGNORE_VALIDATORS],
            description=stress_json[Stress._DESCRIPTION],
            run=None if run is None else StressRun.from_json(run),
        )

    def __init__(self, index, script_pattern, solution_names, time_limit, memory_limit, total_time_limit,
                 testset, group, ignore_validators, description, run=None):
        self.index = index
        self.script_pattern = script_pattern
        self.solution_names = solution_names
        self.time_limit = time_limit
        self.memory_limit = memory_limit
        self.total_time_limit = total_time_limit
        self.testset = testset
        self.group = group
        self.ignore_validators = ignore_validators
        self.description = description
        self.run = run


class StressRun:
    """
    Object: representing the latest run of a stress. verdict and the statistics are set only once
    it is FINISHED; whether a countertest was found shows in countertest, not in verdict
    """
    _STATUS = "status"
    _VERDICT = "verdict"
    _COMMENT = "comment"
    _JUDGED_TEST_COUNT = "judgedTestCount"
    _MAX_CONSUMED_TIME = "maxConsumedTime"
    _MAX_CONSUMED_MEMORY = "maxConsumedMemory"
    _COUNTERTEST = "countertest"

    @classmethod
    def from_json(cls, run_json):
        verdict = run_json.get(StressRun._VERDICT, None)
        countertest = run_json.get(StressRun._COUNTERTEST, None)
        return cls(
            status=StressRunStatus[run_json[StressRun._STATUS]],
            verdict=None if verdict is None else StressRunVerdict[verdict],
            comment=run_json.get(StressRun._COMMENT, None),
            judged_test_count=run_json.get(StressRun._JUDGED_TEST_COUNT, None),
            max_consumed_time=run_json.get(StressRun._MAX_CONSUMED_TIME, None),
            max_consumed_memory=run_json.get(StressRun._MAX_CONSUMED_MEMORY, None),
            countertest=None if countertest is None else StressCountertest.from_json(countertest),
        )

    def __init__(self, status, verdict=None, comment=None, judged_test_count=None, max_consumed_time=None,
                 max_consumed_memory=None, countertest=None):
        self.status = status
        self.verdict = verdict
        self.comment = comment
        self.judged_test_count = judged_test_count
        self.max_consumed_time = max_consumed_time
        self.max_consumed_memory = max_consumed_memory
        self.countertest = countertest


class StressCountertest:
    """
    Object: representing a countertest found by a stress run
    """
    _SCRIPT_LINE = "scriptLine"
    _INPUT = "input"
    _INPUT_TRUNCATED = "inputTruncated"
    _REPORTS = "reports"

    @classmethod
    def from_json(cls, countertest_json):
        return cls(
            script_line=countertest_json[StressCountertest._SCRIPT_LINE],
            input=countertest_json.get(StressCountertest._INPUT, None),
            input_truncated=countertest_json[StressCountertest._INPUT_TRUNCATED],
            reports=[StressSolutionReport.from_json(js) for js in countertest_json[StressCountertest._REPORTS]],
        )

    def __init__(self, script_line, input, input_truncated, reports):
        self.script_line = script_line
        self.input = input
        self.input_truncated = input_truncated
        self.reports = reports


class StressSolutionReport:
    """
    Object: representing the result of a solution that failed a stress countertest
    """
    _SOLUTION_NAME = "solutionName"
    _VERDICT = "verdict"
    _CONSUMED_TIME = "consumedTime"
    _CONSUMED_MEMORY = "consumedMemory"
    _OUTPUT = "output"
    _OUTPUT_TRUNCATED = "outputTruncated"
    _ANSWER = "answer"
    _ANSWER_TRUNCATED = "answerTruncated"
    _COMMENT = "comment"

    @classmethod
    def from_json(cls, report_json):
        return cls(
            solution_name=report_json[StressSolutionReport._SOLUTION_NAME],
            verdict=StressSolutionVerdict[report_json[StressSolutionReport._VERDICT]],
            consumed_time=report_json[StressSolutionReport._CONSUMED_TIME],
            consumed_memory=report_json[StressSolutionReport._CONSUMED_MEMORY],
            output=report_json.get(StressSolutionReport._OUTPUT, None),
            output_truncated=report_json[StressSolutionReport._OUTPUT_TRUNCATED],
            answer=report_json.get(StressSolutionReport._ANSWER, None),
            answer_truncated=report_json[StressSolutionReport._ANSWER_TRUNCATED],
            comment=report_json.get(StressSolutionReport._COMMENT, None),
        )

    def __init__(self, solution_name, verdict, consumed_time, consumed_memory, output, output_truncated, answer,
                 answer_truncated, comment=None):
        self.solution_name = solution_name
        self.verdict = verdict
        self.consumed_time = consumed_time
        self.consumed_memory = consumed_memory
        self.output = output
        self.output_truncated = output_truncated
        self.answer = answer
        self.answer_truncated = answer_truncated
        self.comment = comment


class Solution:
    """
    Object: representing Polygon problem solution
    """
    _NAME = "name"
    _MODIFICATION_TIME_SECONDS = "modificationTimeSeconds"
    _LENGTH = "length"
    _SOURCE_TYPE = "sourceType"
    _TAG = "tag"

    @classmethod
    def from_json(cls, solution_json):
        return cls(
            name=solution_json[Solution._NAME],
            modification_time_seconds=solution_json[Solution._MODIFICATION_TIME_SECONDS],
            length=solution_json[Solution._LENGTH],
            source_type=solution_json[Solution._SOURCE_TYPE],
            tag=SolutionTag[solution_json[Solution._TAG]]
        )

    def __init__(self, name, modification_time_seconds, length, source_type, tag):
        self.name = name
        self.modification_time_seconds = modification_time_seconds
        self.length = length
        self.source_type = source_type
        self.tag = tag


class File:
    """
    Object: representing Polygon file (resource, source, or aux, not solutions)
    """
    _NAME = "name"
    _MODIFICATION_TIME_SECONDS = "modificationTimeSeconds"
    _LENGTH = "length"
    _SOURCE_TYPE = "sourceType"
    _RESOURCE_ADVANCED_PROPERTIES = "resourceAdvancedProperties"

    @classmethod
    def from_json(cls, file_json):
        return cls(
            name=file_json[File._NAME],
            modification_time_seconds=file_json[File._MODIFICATION_TIME_SECONDS],
            length=file_json[File._LENGTH],
            source_type=file_json.get(File._SOURCE_TYPE, None),
            resource_advanced_properties=(
                ResourceAdvancedProperties.from_json(file_json[File._RESOURCE_ADVANCED_PROPERTIES])
                if File._RESOURCE_ADVANCED_PROPERTIES in file_json else None
            ),
        )

    def __init__(self, name, modification_time_seconds, length, source_type, resource_advanced_properties):
        self.name = name
        self.modification_time_seconds = modification_time_seconds
        self.length = length
        self.source_type = source_type
        self.resource_advanced_properties = resource_advanced_properties


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
            stages=[Stage[stage] for stage in resource_advanced_properties[ResourceAdvancedProperties._STAGES]],
            assets=[Asset[asset] for asset in resource_advanced_properties[ResourceAdvancedProperties._ASSETS]],
        )

    def __init__(self, for_types=None, main=None, stages=None, assets=None):
        self.for_types = for_types
        self.main = main
        self.stages = stages
        self.assets = assets


ResourceAdvancedProperties.DELETE = ResourceAdvancedProperties(for_types="")


class ValidatorTest:
    """
    Object: representing Polygon validator test
    """
    _INDEX = "index"
    _INPUT = "input"
    _EXPECTED_VERDICT = "expectedVerdict"
    _TESTSET = "testset"
    _GROUP = "group"
    _RUN_VERDICT = "runVerdict"
    _RUN_COMMENT = "runComment"

    @classmethod
    def from_json(cls, validator_test_json):
        run_verdict = validator_test_json.get(ValidatorTest._RUN_VERDICT, None)
        return cls(
            index=validator_test_json[ValidatorTest._INDEX],
            input=validator_test_json[ValidatorTest._INPUT],
            expected_verdict=ValidatorTestVerdict[validator_test_json[ValidatorTest._EXPECTED_VERDICT]],
            testset=validator_test_json.get(ValidatorTest._TESTSET, None),
            group=validator_test_json.get(ValidatorTest._GROUP, None),
            run_verdict=ValidatorTestRunVerdict[run_verdict] if run_verdict is not None else None,
            run_comment=validator_test_json.get(ValidatorTest._RUN_COMMENT, None),
        )

    def __init__(self, index, input, expected_verdict, testset=None, group=None, run_verdict=None, run_comment=None):
        self.index = index
        self.input = input
        self.expected_verdict = expected_verdict
        self.testset = testset
        self.group = group
        self.run_verdict = run_verdict
        self.run_comment = run_comment


class CheckerTest:
    """
    Object: representing Polygon checker test
    """
    _INDEX = "index"
    _INPUT = "input"
    _OUTPUT = "output"
    _ANSWER = "answer"
    _EXPECTED_VERDICT = "expectedVerdict"
    _RUN_VERDICT = "runVerdict"
    _RUN_COMMENT = "runComment"

    @classmethod
    def from_json(cls, checker_test_json):
        return cls(
            index=checker_test_json[CheckerTest._INDEX],
            input=checker_test_json[CheckerTest._INPUT],
            output=checker_test_json[CheckerTest._OUTPUT],
            answer=checker_test_json[CheckerTest._ANSWER],
            expected_verdict=CheckerTestVerdict[checker_test_json[CheckerTest._EXPECTED_VERDICT]],
            # Kept as a plain string: for completed runs Polygon returns the raw checker interop verdict
            # name, which is not a closed set, so an enum would fail on custom checkers.
            run_verdict=checker_test_json.get(CheckerTest._RUN_VERDICT, None),
            run_comment=checker_test_json.get(CheckerTest._RUN_COMMENT, None),
        )

    def __init__(self, index, input, output, answer, expected_verdict, run_verdict=None, run_comment=None):
        self.index = index
        self.input = input
        self.output = output
        self.answer = answer
        self.expected_verdict = expected_verdict
        self.run_verdict = run_verdict
        self.run_comment = run_comment


class Caution:
    """
    Object: representing one Polygon problem caution
    """
    _TYPE = "type"
    _SEVERITY = "severity"
    _CATEGORY = "category"
    _MESSAGE = "message"
    _PARAMETERS = "parameters"

    @classmethod
    def from_json(cls, caution_json):
        return cls(
            # Kept as a plain string: the docs list caution types as examples, so the set is open
            # and an enum would fail on a type Polygon adds later.
            type=caution_json[Caution._TYPE],
            severity=CautionSeverity[caution_json[Caution._SEVERITY]],
            category=CautionCategory[caution_json[Caution._CATEGORY]],
            message=caution_json[Caution._MESSAGE],
            parameters=caution_json[Caution._PARAMETERS],
        )

    def __init__(self, type, severity, category, message, parameters):
        self.type = type
        self.severity = severity
        self.category = category
        self.message = message
        self.parameters = parameters


class PackageReadinessIssue:
    """
    Object: representing a pre-package state issue collected by Polygon package validation
    """
    _TYPE = "type"
    _REASON = "reason"
    _MESSAGE = "message"

    @classmethod
    def from_json(cls, issue_json):
        return cls(
            # Kept as a plain string for the same reason as Caution.type: the docs list package
            # validation exception types as examples only.
            type=issue_json[PackageReadinessIssue._TYPE],
            message=issue_json[PackageReadinessIssue._MESSAGE],
            reason=issue_json.get(PackageReadinessIssue._REASON, None),
        )

    def __init__(self, type, message, reason=None):
        self.type = type
        self.message = message
        self.reason = reason


class StatementAiTip:
    """
    Object: representing a cached AI correction tip for one statement language
    """
    _LANGUAGE = "language"
    _SOURCE = "source"
    _SUGGESTION = "suggestion"
    _PROCESSING = "processing"

    @classmethod
    def from_json(cls, tip_json):
        return cls(
            language=tip_json[StatementAiTip._LANGUAGE],
            source=tip_json[StatementAiTip._SOURCE],
            processing=tip_json[StatementAiTip._PROCESSING],
            suggestion=tip_json.get(StatementAiTip._SUGGESTION, None),
        )

    def __init__(self, language, source, processing, suggestion=None):
        self.language = language
        self.source = source
        self.processing = processing
        self.suggestion = suggestion


class SourceAiTip:
    """
    Object: representing a cached AI review comment for a source file
    """
    _NAME = "name"
    _COMMENT = "comment"

    @classmethod
    def from_json(cls, tip_json):
        return cls(
            name=tip_json[SourceAiTip._NAME],
            comment=tip_json[SourceAiTip._COMMENT],
        )

    def __init__(self, name, comment):
        self.name = name
        self.comment = comment


class AiTips:
    """
    Object: representing cached "Correction tips from AI" for the problem
    """
    _DISABLED = "disabled"
    _STATEMENTS = "statements"
    _VALIDATOR = "validator"
    _CHECKER = "checker"

    @classmethod
    def from_json(cls, ai_tips_json):
        validator = ai_tips_json.get(AiTips._VALIDATOR, None)
        checker = ai_tips_json.get(AiTips._CHECKER, None)
        return cls(
            disabled=ai_tips_json[AiTips._DISABLED],
            statements=[StatementAiTip.from_json(js) for js in ai_tips_json[AiTips._STATEMENTS]],
            validator=SourceAiTip.from_json(validator) if validator is not None else None,
            checker=SourceAiTip.from_json(checker) if checker is not None else None,
        )

    def __init__(self, disabled, statements, validator=None, checker=None):
        self.disabled = disabled
        self.statements = statements
        self.validator = validator
        self.checker = checker


class ProblemCautions:
    """
    Object: representing structured cautions of a Polygon problem
    """
    _COMMON = "common"
    _STATEMENT = "statement"
    _STRUCTURE = "structure"
    _ISSUES = "issues"
    _PACKAGE_READINESS_ISSUES = "packageReadinessIssues"
    _LATEST_PACKAGE_WARNINGS = "latestPackageWarnings"
    _AI = "ai"

    @classmethod
    def from_json(cls, cautions_json):
        def cautions(field):
            return [Caution.from_json(js) for js in cautions_json[field]]

        return cls(
            common=cautions(ProblemCautions._COMMON),
            statement=cautions(ProblemCautions._STATEMENT),
            structure=cautions(ProblemCautions._STRUCTURE),
            issues=cautions(ProblemCautions._ISSUES),
            package_readiness_issues=[
                PackageReadinessIssue.from_json(js)
                for js in cautions_json[ProblemCautions._PACKAGE_READINESS_ISSUES]
            ],
            latest_package_warnings=cautions_json[ProblemCautions._LATEST_PACKAGE_WARNINGS],
            ai=AiTips.from_json(cautions_json[ProblemCautions._AI]),
        )

    def __init__(self, common, statement, structure, issues, package_readiness_issues,
                 latest_package_warnings, ai):
        self.common = common
        self.statement = statement
        self.structure = structure
        self.issues = issues
        self.package_readiness_issues = package_readiness_issues
        self.latest_package_warnings = latest_package_warnings
        self.ai = ai


class ProblemAccess:
    """
    Object: representing one direct access-control entry of a Polygon problem
    """
    _LOGIN = "login"
    _ACCESS_TYPE = "accessType"

    @classmethod
    def from_json(cls, access_json):
        return cls(
            login=access_json[ProblemAccess._LOGIN],
            access_type=ProblemAccessType[access_json[ProblemAccess._ACCESS_TYPE]],
        )

    def __init__(self, login, access_type):
        self.login = login
        self.access_type = access_type


class Issue:
    """
    Object: representing an issue of a Polygon problem
    """
    _ID = "id"
    _TYPE = "type"
    _STATUS = "status"
    _AUTHOR = "author"
    _ASSIGNEE = "assignee"
    _HTML = "html"
    _CREATION_TIME_SECONDS = "creationTimeSeconds"
    _MODIFICATION_TIME_SECONDS = "modificationTimeSeconds"
    _COMMENTS = "comments"

    @classmethod
    def from_json(cls, issue_json):
        return cls(
            issue_id=issue_json[Issue._ID],
            type=IssueType[issue_json[Issue._TYPE]],
            status=IssueStatus[issue_json[Issue._STATUS]],
            author=issue_json[Issue._AUTHOR],
            assignee=issue_json.get(Issue._ASSIGNEE, None),
            html=issue_json[Issue._HTML],
            creation_time_seconds=issue_json[Issue._CREATION_TIME_SECONDS],
            modification_time_seconds=issue_json[Issue._MODIFICATION_TIME_SECONDS],
            comments=[IssueComment.from_json(js) for js in issue_json[Issue._COMMENTS]],
        )

    def __init__(self, issue_id, type, status, author, assignee, html, creation_time_seconds,
                 modification_time_seconds, comments):
        self.id = issue_id
        self.type = type
        self.status = status
        self.author = author
        self.assignee = assignee
        self.html = html
        self.creation_time_seconds = creation_time_seconds
        self.modification_time_seconds = modification_time_seconds
        self.comments = comments


class IssueComment:
    """
    Object: representing a comment on a problem issue, with the changes it made to the issue
    """
    _AUTHOR = "author"
    _HTML = "html"
    _CREATION_TIME_SECONDS = "creationTimeSeconds"
    _STATUS = "status"
    _TYPE = "type"
    _ASSIGNEE = "assignee"

    @classmethod
    def from_json(cls, comment_json):
        status = comment_json.get(IssueComment._STATUS)
        issue_type = comment_json.get(IssueComment._TYPE)
        return cls(
            author=comment_json[IssueComment._AUTHOR],
            html=comment_json[IssueComment._HTML],
            creation_time_seconds=comment_json[IssueComment._CREATION_TIME_SECONDS],
            status=None if status is None else IssueStatus[status],
            type=None if issue_type is None else IssueType[issue_type],
            assignee=comment_json.get(IssueComment._ASSIGNEE, None),
        )

    def __init__(self, author, html, creation_time_seconds, status=None, type=None, assignee=None):
        self.author = author
        self.html = html
        self.creation_time_seconds = creation_time_seconds
        self.status = status
        self.type = type
        self.assignee = assignee


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

    @staticmethod
    def _encoded_args(args):
        return [(Request._value_to_utf8_bytes(key), Request._value_to_utf8_bytes(value))
                for key, value in args]

    @staticmethod
    def _value_to_utf8_bytes(value):
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)
        return str(value).encode("utf-8")

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
                    self.args.append((key, it))
            else:
                self.args.append((key, value))
        self.config = config
        self.method_name = method_name

    def issue(self):
        """Issues request and returns parsed JSON response"""

        response_text = self.issue_text()
        try:
            response_json = json.loads(response_text)
        except json.decoder.JSONDecodeError as exc:
            raise HTTPRequestFailedException(f'Method {self.method_name} has not returned a valid JSON.') from exc
        return Response(response_json)

    def issue_text(self):
        """Issues request and returns the response body as text (useful e.g. for scripts and tests)"""

        return self._issue().text

    def issue_raw(self):
        """Issues request and returns the response body as bytes (useful e.g. for packages)"""

        return self._issue().content

    def _issue(self):
        """Issues request and returns the requests.Response as is"""

        args = list(self.args)
        args.append(('apiKey', self.config.api_key))
        args.append(('time', str(int(time.time()))))
        args = Request._encoded_args(args)
        args.append((b'apiSig', self.get_api_signature(args, Request._value_to_utf8_bytes(self.config.api_secret))))
        response = requests.post(
            self.config.api_url + self.method_name, files=args)
        if response.status_code not in [200, 400]:  # Polygon returns 400 and a descriptive JSON on user error
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as exc:
                raise HTTPRequestFailedException(
                    f'Method {self.method_name} returned HTTP code {response.status_code}') from exc
        return response

    def get_api_signature(self, args, api_secret):
        rand_bit = Request._value_to_utf8_bytes(''.join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in range(6)))

        arg_tuples = list(sorted(args))
        args_bit = b'&'.join(key + b'=' + value for key, value in arg_tuples)
        api_signature_string = rand_bit + b'/' + self.method_name.encode(
            'utf-8') + b'?' + args_bit + b'#' + api_secret
        api_signature = (
                rand_bit +
                Request._value_to_utf8_bytes(hashlib.sha512(api_signature_string).hexdigest()))
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


class DeleteTestsFailedException(PolygonRequestFailedException):
    """Exception raised when problem.deleteTest can not delete some of the requested tests"""

    def __init__(self, comment, result):
        super().__init__(comment)
        self.result = result


class HTTPRequestFailedException(Exception):
    """Exception raised when Polygon request is failed or Polygon does not return a JSON"""

    def __init__(self, comment):
        self.comment = comment


class PointsPolicy(Enum):
    COMPLETE_GROUP = 0
    EACH_TEST = 1

    def __str__(self):
        return self.name


class FeedbackPolicy(Enum):
    NONE = 0
    POINTS = 1
    ICPC = 2
    COMPLETE = 3

    def __str__(self):
        return self.name


class FileType(Enum):
    RESOURCE = 0
    SOURCE = 1
    AUX = 2

    def __str__(self):
        return self.name.lower()


class SolutionTag(Enum):
    MA = 0  # Main correct solution
    OK = 1  # Accepted
    RJ = 2  # Rejected, Incorrect
    TL = 3  # Time limit exceeded
    TO = 4  # Time limit exceeded or accepted
    WA = 5  # Wrong answer
    PE = 6  # Presentation error
    ML = 7  # Memory limit exceeded
    RE = 8  # Runtime error
    TM = 9  # Time limit exceeded or memory limit exceeded
    NR = 10  # Do not run

    def __str__(self):
        return self.name


class Asset(Enum):
    VALIDATOR = 0
    INTERACTOR = 1
    CHECKER = 2
    SOLUTION = 3

    def __str__(self):
        return self.name


class Stage(Enum):
    COMPILE = 0
    RUN = 1

    def __str__(self):
        return self.name


class PackageState(Enum):
    PENDING = 0
    RUNNING = 1
    READY = 2
    FAILED = 3

    def __str__(self):
        return self.name


class PackageType(Enum):
    STANDARD = 0
    LINUX = 1
    WINDOWS = 2

    def __str__(self):
        return self.name.lower()


class ValidatorTestVerdict(Enum):
    VALID = 0
    INVALID = 1

    def __str__(self):
        return self.name


class ValidatorTestRunVerdict(Enum):
    VALID = 0
    INVALID = 1
    IN_QUEUE = 2
    CANT_RUN = 3

    def __str__(self):
        return self.name


class CheckerTestVerdict(Enum):
    OK = 0
    WRONG_ANSWER = 1
    CRASHED = 2
    PRESENTATION_ERROR = 3

    def __str__(self):
        return self.name


class CautionSeverity(Enum):
    SOFT = 0
    HARD = 1

    def __str__(self):
        return self.name


class CautionCategory(Enum):
    COMMON = 0
    STATEMENT = 1
    STRUCTURE = 2
    ISSUES = 3

    def __str__(self):
        return self.name


class RenderStatus(Enum):
    OK = 0
    FAILED = 1

    def __str__(self):
        return self.name


class ProblemAccessType(Enum):
    READ = 0
    WRITE = 1
    OWNER = 2
    NONE = 3

    def __str__(self):
        return self.name


class TestDeletionFailureReason(Enum):
    DUPLICATE = 0
    NOT_FOUND = 1
    FREEMARKER_SCRIPT_TEST = 2
    DELETE_FAILED = 3

    def __str__(self):
        return self.name


class IssueType(Enum):
    DISCUSSION = 0
    ENHANCEMENT = 1
    BUG = 2

    def __str__(self):
        return self.name


class IssueStatus(Enum):
    OPENED = 0
    REOPENED = 1
    CLOSED = 2

    def __str__(self):
        return self.name


class MaterialPublishStrategy(Enum):
    NONE = 0
    WITH_TUTORIAL = 1
    WITH_STATEMENT = 2

    def __str__(self):
        return self.name


class MaterialItemType(Enum):
    TEST_INPUTS = 0
    TEST_ANSWERS = 1
    RESOURCE_FILES = 2
    SOURCE_FILES = 3
    AUX_FILES = 4
    SOLUTIONS = 5

    def __str__(self):
        return self.name


class InvocationStatus(Enum):
    PENDING = 0
    RUNNING = 1
    FINISHED = 2
    ABORTED = 3

    def __str__(self):
        return self.name


class InvocationRunVerdict(Enum):
    OK = 0  # Accepted
    WA = 1  # Wrong answer
    PE = 2  # Presentation error
    TL = 3  # Time limit exceeded
    ML = 4  # Memory limit exceeded
    IL = 5  # Idleness limit exceeded
    RE = 6  # Runtime error
    CE = 7  # Compilation error
    FL = 8  # Failed
    RJ = 9  # Skipped or rejected
    NO = 10  # Waiting
    TS = 11  # Being tested

    def __str__(self):
        return self.name


class StressRunStatus(Enum):
    PENDING = 0
    RUNNING = 1  # Includes waiting in queues
    FINISHED = 2

    def __str__(self):
        return self.name


class StressRunVerdict(Enum):
    OK = 0  # The stress ran normally, with or without a countertest
    FAILED = 1  # The run itself failed: the generator, a validator, the main solution and so on
    CRASHED = 2  # An unexpected failure

    def __str__(self):
        return self.name


class StressSolutionVerdict(Enum):
    WRONG_ANSWER = 0
    PRESENTATION_ERROR = 1
    TIME_LIMIT_EXCEEDED = 2
    MEMORY_LIMIT_EXCEEDED = 3
    IDLENESS_LIMIT_EXCEEDED = 4
    RUNTIME_ERROR = 5
    FAILED = 6
    CRASHED = 7
    TIME_LIMIT_EXCEEDED_OR_ACCEPTED = 8
    TIME_LIMIT_EXCEEDED_OR_MEMORY_LIMIT_EXCEEDED = 9

    def __str__(self):
        return self.name
