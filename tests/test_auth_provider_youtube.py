import json


def test_quota_exceeded_detection():
    from auth.providers.youtube import _is_quota_exceeded_error

    class FakeResp:
        status = 403

    class FakeHttpError(Exception):
        resp = FakeResp()
        content = json.dumps({
            "error": {
                "errors": [
                    {"reason": "quotaExceeded"}
                ]
            }
        }).encode("utf-8")

    assert _is_quota_exceeded_error(FakeHttpError())
