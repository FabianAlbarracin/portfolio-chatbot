import threading
import time
import os
import json

from src.rate_limiter import check_and_update


TEST_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "usage_logs.json")


def _reset_log():
    if os.path.exists(TEST_LOG_FILE):
        os.remove(TEST_LOG_FILE)


def test_single_request_allowed():
    _reset_log()
    assert check_and_update("192.168.1.100", daily_limit=5)


def test_daily_limit_reached():
    _reset_log()
    ip = "10.0.0.50"
    for _ in range(5):
        assert check_and_update(ip, daily_limit=5)
    assert not check_and_update(ip, daily_limit=5)


def test_different_ips_independent():
    _reset_log()
    assert check_and_update("10.0.0.1", daily_limit=1)
    assert check_and_update("10.0.0.2", daily_limit=1)


def test_concurrent_access_atomic():
    _reset_log()
    ip = "172.16.0.99"
    results = []

    def make_request():
        results.append(check_and_update(ip, daily_limit=5))

    threads = [threading.Thread(target=make_request) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    passed = sum(results)
    assert passed == 5, f"Expected exactly 5 passes, got {passed}"
