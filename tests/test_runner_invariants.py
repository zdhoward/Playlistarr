from runner import RunOutcome, StageResult, RunResult


def test_run_outcome_requires_stages():
    outcome = RunOutcome(
        overall=RunResult.OK,
        stages=[],
    )
    assert isinstance(outcome.stages, list)


def test_stage_result_shape():
    r = StageResult(
        name="Discovery",
        state=RunResult.OK,
        exit_code=0,
    )
    assert r.name == "Discovery"
    assert r.state == RunResult.OK
    assert r.exit_code == 0
