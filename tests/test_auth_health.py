def test_quota_exceeded_is_ok():
    from auth.providers.youtube import _is_quota_exceeded_error

    # fabricate HttpError-like object


from auth.base import AuthHealthStatus


def test_health_result_shapes():
    from auth.base import AuthHealthResult

    r = AuthHealthResult(
        provider="youtube",
        status=AuthHealthStatus.OK,
        message="ok",
    )

    assert r.provider == "youtube"
    assert r.status == AuthHealthStatus.OK
