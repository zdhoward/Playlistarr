from runner import _infer_state, RunResult


def test_infer_ok():
    assert _infer_state(0, "") == RunResult.OK


def test_infer_quota_exit_code():
    assert _infer_state(10, "") == RunResult.QUOTA_EXHAUSTED


def test_infer_auth_exit_code():
    assert _infer_state(12, "") == RunResult.AUTH_INVALID


def test_infer_quota_text():
    assert _infer_state(1, "quota exceeded") == RunResult.QUOTA_EXHAUSTED


def test_infer_auth_text():
    assert _infer_state(1, "auth_invalid") == RunResult.AUTH_INVALID


def test_infer_failed_fallback():
    assert _infer_state(1, "some error") == RunResult.FAILED
