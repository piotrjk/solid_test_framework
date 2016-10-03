import solid_test_suite
import solid_test_case
import solid_test_report
import random
import logging
import sys
import unittest
import unicodedata

logging.getLogger().addHandler(logging.StreamHandler())
log = logging.getLogger()
log.setLevel('INFO')


def get_random_unicode_string(length, ascii_ratio=0.9):
    unsafe = [u"\u2028"]
    text = []
    for i in xrange(length):
        if random.random() < ascii_ratio:
            text.append(chr(random.randint(32, 126)))
        else:
            while True:
                try:
                    c = unichr(random.randint(0, sys.maxunicode))
                except:
                    continue
                else:
                    if unicodedata.category(c) == 'Cc' or c in unsafe:
                        continue
                    else:
                        text.append(c)
                        break
    return ''.join(text)


def randbool():
    return bool(random.randint(0, 1))


def random_expected_failure_decorator(tfunc):
    if random.randint(1, 6) == 6:
        return unittest.expectedFailure(tfunc)
    else:
        return tfunc


def random_expected_skip_decorator(tfunc):
    if random.randint(1, 6) == 6:
        return unittest.skip(tfunc)
    else:
        return tfunc


class ItsOnlyATestSuite(solid_test_suite.SolidTestSuite):

    def pre_run_1_info(self):
        log.info(u'\n\nPRERUN INFO 1: {}\n\n'.format(get_random_unicode_string(30)))

    def pre_run_2_info(self):
        log.info(u'\n\nPRERUN INFO 2: {}\n\n'.format(get_random_unicode_string(30)))

    def post_run_1_info(self):
        log.info(u'\n\nPOSTRUN INFO 1: {}\n\n'.format(get_random_unicode_string(30)))

    def post_run_2_info(self):
        log.info(u'\n\nPOSTRUN INFO 2: {}\n\n'.format(get_random_unicode_string(30)))

    def pre_test_log_capture(self):
        log.info(u'Starting log capture')
        self.start_capture()

    def pre_test_1_info(self):
        log.info(u'\n\nPre test info: {}\n\n'.format(get_random_unicode_string(30)))

    def post_test_log_capture(self):
        log.info(u'Stopping log capture')
        self.stop_capture()

    def post_test_1_info(self):
        log.info(u'\n\nPost test info\n\n')

    def post_test_2_stats(self):
        log.info(u'\n\ntc_name: {name}\ntest_outcome: {outcome}\ntc_time: {tc_time}\ntotal_tc: {total_tc}\ntc_ran:{tc_ran}\ntc_passed: {tc_passed}\ntc_failed: {tc_failed}\n'.format(
            name=self.current_test.get_name(),
            outcome=self.last_test_case_outcome,
            tc_time=self.test_case_time,
            total_tc=self.total_test_run_cases_count,
            tc_ran=self.current_test_run_cases_ran,
            tc_passed=self.current_test_run_cases_passed,
            tc_failed=self.current_test_run_cases_failed
        ))



class ItsOnlyATestCase(solid_test_case.SolidTestCase):

    @random_expected_skip_decorator
    @random_expected_failure_decorator
    def test_test(self):
        log.info(get_random_unicode_string(random.randint(1, 100)))
        for _ in xrange(0, random.randint(1, 100)):
            if randbool():
                sys.stderr.write(get_random_unicode_string(random.randint(1, 100)))
            else:
                sys.stdout.write(get_random_unicode_string(random.randint(1, 100)))
            log.info(get_random_unicode_string(random.randint(1, 100)))

        outcome = random.randint(0, 3)
        if outcome == 0:
            log.info(u'pass')
        elif outcome == 1:
            if randbool():
                log.warn(u'fail')
                self.fail(get_random_unicode_string(random.randint(1, 100)))
            else:
                log.warn(u'fail assert')
                self.assertTrue(False, get_random_unicode_string(random.randint(1, 100)))
        elif outcome == 2:
            log.warn(u'error')
            raise Exception(get_random_unicode_string(random.randint(1, 100)))
        elif outcome == 3:
            log.info(u'skip')
            self.skipTest(get_random_unicode_string(random.randint(1, 100)))


if __name__ == '__main__':

    sts = ItsOnlyATestSuite()
    sts.load_from_test_case_class(ItsOnlyATestCase)
    sts.multiply_tests(100)

    json_report_path = 'results_json.txt'
    xml_report_path = 'results_junit.xml'
    sts.run(json_report_path, stop_trigger=False)
    solid_test_report.create_junit_report_from_json_report(json_report_path, xml_report_path)
