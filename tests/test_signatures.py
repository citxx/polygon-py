"""
Checks of the wrapper's signatures that hold for every method at once, so a new method or a new
parameter can't quietly break them.
"""

import inspect
import types

from polygon_api import api


def _functions_taking_a_pin(module):
    """
    Every function of the module with a pin parameter, by qualified name: module-level functions and
    the methods, constructors, class methods and static methods of the classes defined in it.
    """
    functions = {}
    for name, member in vars(module).items():
        if inspect.isfunction(member) and member.__module__ == module.__name__:
            functions[name] = member
        elif inspect.isclass(member) and member.__module__ == module.__name__:
            for attribute, value in vars(member).items():
                if isinstance(value, (classmethod, staticmethod)):
                    value = value.__func__
                if inspect.isfunction(value):
                    functions['%s.%s' % (name, attribute)] = value
    return {
        name: function for name, function in functions.items()
        if 'pin' in inspect.signature(function).parameters
    }


def _misplaced_pins(module):
    return sorted(
        name for name, function in _functions_taking_a_pin(module).items()
        if list(inspect.signature(function).parameters)[-1] != 'pin'
    )


class TestPinIsTheLastParameter:
    """
    pin is the last parameter wherever it is taken, so a parameter added later goes right before it,
    and pin=... means the same in every call.
    """

    def test_pin_is_the_last_parameter_everywhere(self):
        assert _misplaced_pins(api) == []

    def test_the_scan_reaches_methods_shortcuts_constructors_and_parsers(self):
        """Guards the check above against passing because the scan found nothing."""
        functions = _functions_taking_a_pin(api)
        for name in ('Polygon.problem_info', 'Polygon.problem_save_test', 'Polygon.contest_problems',
                     'Problem.__init__', 'Problem.save_test', 'Test.__init__', 'ManualTest.__init__',
                     'ManualTest.save', 'GeneratedTest.__init__', 'Test.from_json'):
            assert name in functions

    def test_a_misplaced_pin_is_reported(self):
        module = types.ModuleType('fake_api')

        class Client:
            def good(self, problem_id, pin=None):
                pass

            def bad(self, problem_id, pin=None, extra=None):
                pass

            @classmethod
            def bad_class_method(cls, pin, extra):
                pass

            @staticmethod
            def bad_static_method(pin, extra):
                pass

            def without_pin(self, problem_id):
                pass

        def bad_function(pin=None, extra=None):
            pass

        def good_function(extra=None, pin=None):
            pass

        for member in (Client, bad_function, good_function):
            member.__module__ = module.__name__
            setattr(module, member.__name__, member)

        assert _misplaced_pins(module) == [
            'Client.bad', 'Client.bad_class_method', 'Client.bad_static_method', 'bad_function',
        ]
