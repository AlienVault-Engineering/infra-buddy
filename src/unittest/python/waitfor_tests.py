import os
import unittest

from infra_buddy.utility.waitfor import waitfor

FAIL = "FAIL"

SUCCESS = "SUCCESS"

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class TestWaitFor(object):
    def __init__(self, success_count):
        super(TestWaitFor, self).__init__()
        self.attempts = 0
        self.success_count = success_count

    def res_func(self):
        if self.attempts == self.success_count:
            return SUCCESS
        self.attempts += 1
        return FAIL

    def res_func_args(self, foo, bar):
        if foo is None or bar is None:
            raise Exception("Did not get args")
        return self.res_func()


class WaitforTestCase(unittest.TestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(WaitforTestCase, cls).setUpClass()
        cls.iterations = 3

    def test_waitfor_success(self):
        test_class = TestWaitFor(self.iterations)
        res = waitfor(test_class.res_func, expected_result=SUCCESS, interval_seconds=1, max_attempts=10)
        self.assertEqual(res, SUCCESS, "Failed to return success message")
        self.assertEqual(test_class.attempts, self.iterations, "Failed to iterate to expected number")

    def test_waitfor_list(self):
        test_class = TestWaitFor(self.iterations)
        res = waitfor(test_class.res_func, expected_result=[SUCCESS,"BAZ"], interval_seconds=1, max_attempts=10)
        self.assertEqual(res, SUCCESS, "Failed to return success message")
        self.assertEqual(test_class.attempts, self.iterations, "Failed to iterate to expected number")

    def test_waitfor_fail_attempts(self):
        test_class = TestWaitFor(self.iterations*10)
        try:
            res = waitfor(test_class.res_func, expected_result=[SUCCESS,"BAZ"], interval_seconds=1, max_attempts=2)
            self.fail("Did not throw exception on timeout")
        except:
            pass

    def test_waitfor_negate(self):
        test_class = TestWaitFor(self.iterations)
        res = waitfor(test_class.res_func, expected_result=FAIL, interval_seconds=1, max_attempts=10, negate=True)
        self.assertEqual(res, SUCCESS, "Failed to return success message")
        self.assertEqual(test_class.attempts, self.iterations, "Failed to iterate to expected number")

    def test_waitfor_with_args(self):
        test_class = TestWaitFor(self.iterations)
        res = waitfor(test_class.res_func_args, expected_result=SUCCESS, interval_seconds=1, max_attempts=10,
                      args={"foo": "foo", "bar": "bar"})
        self.assertEqual(res, SUCCESS, "Failed to return success message")
        self.assertEqual(test_class.attempts, self.iterations, "Failed to iterate to expected number")
