import logging
import time


def _compare(expected_result, param, negate):
    if type(expected_result) is list:
        if negate:
            return param in expected_result
        else:
            return param not in expected_result

    if negate:
        return expected_result == param
    else:
        return expected_result != param


def waitfor(function_pointer, expected_result, interval_seconds, max_attempts, negate=False, args=None,exception=True):
    if args is None:
        args = {}
    attempt = 1
    latest = function_pointer(**args)
    while attempt < max_attempts and _compare(expected_result, latest, negate):
        logging.info("Waiting for another attempt - {attempt}".format(attempt=attempt))
        time.sleep(interval_seconds)
        latest = function_pointer(**args)
        attempt += 1
    if attempt >= max_attempts:
        # we failed
        if exception: raise Exception("Wait condition failed: {func}".format(func=function_pointer))
        return None
    else:
        return latest
