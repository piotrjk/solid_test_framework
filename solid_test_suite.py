import signal
import datetime
import time
import unittest
import traceback
import logging
import sys
from StringIO import StringIO
import solid_test_report
import random

log = logging.getLogger()

SIGINT_TRIGGER = False


def exit_signal_handler(sig, frame):
    log.warn(
        u'Manual test stop (ctrl-c)!\nCurrent run will stop after the test!\n(subsequent interrupts will force stop)')
    global SIGINT_TRIGGER
    SIGINT_TRIGGER = True
    signal.signal(signal.SIGINT, signal.default_int_handler)
signal.signal(signal.SIGINT, exit_signal_handler)


def get_iso_date_string(unix_timestamp=None, sep=' '):
    if unix_timestamp is not None:
        return datetime.datetime.fromtimestamp(unix_timestamp).isoformat(sep)
    else:
        return datetime.datetime.now().isoformat(sep)


def exception_to_string(sys_exc_tuple, timestamped=True, additional_sections=()):
    out = []
    if timestamped:
        out.append(get_iso_date_string())
    out.append('\n'.join(traceback.format_exception(*sys_exc_tuple)))
    out.extend('\n'.join(additional_sections))
    return '\n'.join(out)


class SolidTestSkipTestException(Exception):
    pass


class SolidTestSkipRunException(Exception):
    pass


class SolidTestSuite(object):
    def __init__(self, tests=()):
        self._tests = []
        self.add_tests(tests)
        self.pre_run_functions = self._get_func_list_by_prefix('pre_run')
        self.post_run_functions = self._get_func_list_by_prefix('post_run')
        self.pre_test_functions = self._get_func_list_by_prefix('pre_test')
        self.post_test_functions = self._get_func_list_by_prefix('post_test')
        self.stop_trigger = None

        self.total_test_run_cases_count = 0
        self.current_test_run_cases_ran = 0
        self.current_test_run_cases_passed = 0
        self.current_test_run_cases_failed = 0
        self.current_test = None
        self.last_test_case_outcome = None
        self.test_run_start_time = None
        self.test_case_start_time = None
        self.test_case_time = 0

        self.buffer_stdout = None
        self.buffer_stderr = None
        self.buffer_logger = None
        self.original_stdout = None
        self.original_stderr = None
        self.logger_output_capture_handler = None
        self.stdout_output = ''
        self.stderr_output = ''
        self.logger_output = ''

    def load_from_test_case_class(self, tc_class):
        self.add_tests(unittest.TestLoader().loadTestsFromTestCase(tc_class))

    def randomize_test_order(self):
        random.shuffle(self._tests)

    def multiply_tests(self, times):
        self._tests = self._tests * times

    def _get_func_list_by_prefix(self, prefix):
        names = [n for n in dir(self) if n.startswith(prefix)]
        names.sort()
        func_list = [getattr(self, f) for f in names if callable(getattr(self, f))]
        return func_list

    def pre_run(self):
        pass

    def post_run(self):
        pass

    def post_test(self):
        pass

    def pre_test(self):
        pass

    def __repr__(self):
        return u'<{} tests={}>'.format(self.__class__, list(self))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return list(self) == list(other)

    def __ne__(self, other):
        return not self == other

    # Can't guarantee hash invariant, so flag as unhashable
    __hash__ = None

    def __iter__(self):
        return iter(self._tests)

    def count_test_cases(self):
        cases = 0
        for test in self:
            cases += test.countTestCases()
        return cases

    countTestCases = count_test_cases

    def add_test(self, test):
        # sanity checks
        if not hasattr(test, '__call__'):
            raise TypeError("{} is not callable".format(repr(test)))
        if isinstance(test, type) and issubclass(test, (unittest.case.TestCase, unittest.TestSuite, self)):
            raise TypeError("TestCases and TestSuites must be instantiated before passing them to add_test()")
        self._tests.append(test)

    addTest = add_test

    def add_tests(self, tests):
        if isinstance(tests, basestring):
            raise TypeError("tests must be an iterable of tests, not a string")
        for test in tests:
            self.add_test(test)

    addTests = add_tests

    def __call__(self, *args, **kwds):
        return self.run(*args, **kwds)

    def run(self, result_json_path, stop_trigger, failfast=False):
        self.stop_trigger = stop_trigger
        self.total_test_run_cases_count = self.count_test_cases()

        for pre_run_function in self.pre_run_functions:
            try:
                pre_run_function()
            except SolidTestSkipRunException:
                stop_trigger = True
            except:
                log.exception(u'Encountered unhandled exception in {}, will ignore:'.format(pre_run_function))

        self.test_run_start_time = time.time()
        for i, test in enumerate(self):
            if stop_trigger or SIGINT_TRIGGER:
                break
            self.current_test = test

            result = SolidTestResult()
            self.test_case_start_time = time.time()

            for pre_test_function in self.pre_test_functions:
                try:
                    pre_test_function()
                except SolidTestSkipRunException:
                    break
                except SolidTestSkipTestException:
                    test = unittest.skip(exception_to_string(sys.exc_info()))
                except:
                    log.exception(u'Encountered unhandled exception in {}, will ignore:'.format(pre_test_function))
            #############################################
            try:
                test(result)
            except:
                result.add_error(test, sys.exc_info())
            finally:
                self.last_test_case_outcome = result.outcome
                self.current_test_run_cases_ran += 1
                if self.last_test_case_outcome != 'pass':
                    self.current_test_run_cases_passed += 1
                else:
                    self.current_test_run_cases_failed += 1
                self.test_case_time = time.time() - self.test_case_start_time
            #############################################
            for post_test_function in self.post_test_functions:
                try:
                    post_test_function()
                except SolidTestSkipRunException:
                    stop_trigger = True
                except:
                    log.exception(u'Encountered unhandled exception in {}, will ignore:'.format(post_test_function))

            test_case_report = {
                'name': test.get_name() or test.id().split('.')[-1],
                'class_name': test.get_class() or test.id().split('.')[-2],
                'suite': test.get_module() or test.id().split('.')[-3],
                'outcome': self.last_test_case_outcome,
                'time': self.test_case_time,
                'stdout': self.stdout_output,
                'stderr': self.stderr_output,
                'logger': self.logger_output,
                'exc': result.errors
            }

            solid_test_report.append_to_a_json_report(result_json_path, test_case_report)

            self.current_test = None
            if result.stop:
                stop_trigger = True
            if failfast and self.last_test_case_outcome != 'pass':
                log.info(u'Aborting test run due to "failfast" setting')
                break

        for post_run_function in self.post_run_functions:
            try:
                post_run_function()
            except:
                log.exception(u'Encountered unhandled exception in {}, will ignore:'.format(post_run_function))

    def start_capture(self):
        self.start_stdout_capture()
        self.start_stderr_capture()
        self.start_root_logger_capture()

    def stop_capture(self):
        self.stop_stdout_capture()
        self.stop_stderr_capture()
        self.stop_root_logger_capture()

    def start_root_logger_capture(self):
        self.logger_output = ''
        self.buffer_logger = StringIO()
        self.logger_output_capture_handler = logging.StreamHandler(self.buffer_logger)
        root_logger = logging.getLogger()
        root_logger.addHandler(self.logger_output_capture_handler)

    def stop_root_logger_capture(self):
        if self.buffer_logger is None:
            msg = u'Logger capture stop was called before starting it!'
            log.warn(msg)
            return msg
        else:
            self.buffer_logger.flush()
            self.logger_output_capture_handler.flush()
            output = self.buffer_logger.getvalue()
            root_logger = logging.getLogger()
            root_logger.removeHandler(self.logger_output_capture_handler)
            self.buffer_logger = None
            self.logger_output_capture_handler = None
            self.logger_output = output
            return output

    def start_stdout_capture(self, combine_with_stderr=False):
        self.original_stdout = sys.stdout
        self.stdout_output = ''
        self.buffer_stdout = StringIO()
        if combine_with_stderr:
            sys.stdout = sys.stderr = self.buffer_stdout
        else:
            sys.stdout = self.buffer_stdout

    def start_stderr_capture(self):
        self.original_stderr = sys.stderr
        self.stderr_output = ''
        self.buffer_stderr = StringIO()
        sys.stderr = self.buffer_stderr

    def stop_stdout_capture(self):
        if self.buffer_stdout is None:
            msg = u'Stdout capture stop was called before starting it!'
            log.warn(msg)
            return msg
        else:
            self.buffer_stdout.flush()
            output = self.buffer_stdout.getvalue()
            self.buffer_stdout = None
            sys.stdout = self.original_stdout
            self.stdout_output = output
            return output

    def stop_stderr_capture(self):
        if self.buffer_stderr is None:
            msg = u'Stderr capture stop was called before starting it!'
            log.warn(msg)
            return msg
        else:
            self.buffer_stderr.flush()
            output = self.buffer_stderr.getvalue()
            self.buffer_stderr = None
            sys.stderr = self.original_stderr
            self.stderr_output = output
            return output


class SolidTestResult(object):
    def __init__(self):
        self.outcome = None
        self.possible_outcomes = {
            'pass': 'passed',
            'fail': 'failed',
            'error': 'failed due to error',
            'skip': 'skipped',
            'expected_fail': 'failed as expected',
            'unexpected_pass': 'passed unexpectedly',
            None: 'unexpected termination'
        }
        self.errors = []
        self.skip_reason = ''
        self.stop = False

    def add_error(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        self.errors.append(exception_to_string(err))
        self.outcome = 'error'
    addError = add_error

    def add_failure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        self.errors.append(exception_to_string(err))
        self.outcome = 'fail'
    addFailure = add_failure

    def add_success(self, test):
        "Called when a test has completed successfully"
        self.outcome = 'pass'
    addSuccess = add_success

    def add_skip(self, test, reason):
        """Called when a test is skipped."""
        self.outcome = 'skip'
        self.skip_reason = reason
    addSkip = add_skip

    def add_expected_failure(self, test, err):
        """Called when an expected failure/error occured."""
        self.errors.append(exception_to_string(err))
        self.outcome = 'expected_fail'
    addExpectedFailure = add_expected_failure

    def add_unexpected_success(self, test):
        """Called when a test was expected to fail, but succeed."""
        self.outcome = 'unexpected_pass'
    addUnexpectedSuccess = add_unexpected_success

    def stop(self):
        "Indicates that the tests should be aborted"
        self.stop = True

