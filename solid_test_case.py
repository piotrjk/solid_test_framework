import sys
import os
import unittest
from solid_test_suite import SolidTestResult


class SolidTestCase(unittest.TestCase):
    def get_name(self):
        return self._testMethodName

    def get_class(self, full=False):
        if full:
            return self.__class__.__name__
        return self.__class__.__name__.split('.')[-1]

    def get_module(self):
        return os.path.dirname(os.path.abspath(__file__)).split(os.sep)[-1]

    def run(self, result=None):
        if not isinstance(result, SolidTestResult):
            super(SolidTestCase, self).run(result)
        else:
            if result is None:
                raise Exception('No valid test result passed in a argument')
            test_method = getattr(self, self._testMethodName)
            if (getattr(self.__class__, "__unittest_skip__", False) or
                    getattr(test_method, "__unittest_skip__", False)):
                # If the class or method was skipped.
                try:
                    skip_why = (getattr(self.__class__, '__unittest_skip_why__', '')
                                or getattr(test_method, '__unittest_skip_why__', ''))
                    result.add_skip(self, skip_why)
                finally:
                    return

            success = False
            try:
                self.setUp()
            except unittest.SkipTest as e:
                result.add_skip(self, unicode(e))
            except KeyboardInterrupt:
                raise
            except:
                result.add_error(self, sys.exc_info())
            else:
                try:
                    test_method()
                except KeyboardInterrupt:
                    raise
                except self.failureException:
                    result.add_failure(self, sys.exc_info())
                except unittest.case._ExpectedFailure as e:
                    addExpectedFailure = getattr(result, 'addExpectedFailure', None)
                    if addExpectedFailure is not None:
                        addExpectedFailure(self, e.exc_info)
                    else:
                        result.addSuccess(self)
                except unittest.case._UnexpectedSuccess:
                    addUnexpectedSuccess = getattr(result, 'addUnexpectedSuccess', None)
                    if addUnexpectedSuccess is not None:
                        addUnexpectedSuccess(self)
                    else:
                        result.addFailure(self, sys.exc_info())
                except unittest.SkipTest as e:
                    result.add_skip(self, unicode(e))
                except:
                    result.addError(self, sys.exc_info())
                else:
                    success = True

                try:
                    self.tearDown()
                except KeyboardInterrupt:
                    raise
                except:
                    result.add_error(self, sys.exc_info())
                    success = False
            try:
                clean_up_success = self.doCleanups()
            except:
                clean_up_success = False
            success = success and clean_up_success
            if success:
                result.add_success(self)
