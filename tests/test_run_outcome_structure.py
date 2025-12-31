from runner import RunOutcome, StageResult, RunResult


def test_run_outcome_shape():
    r = RunOutcome(
        overall=RunResult.OK,
        stages=[StageResult(name="Test", state=RunResult.OK, exit_code=0)],
    )

    assert r.overall == RunResult.OK
    assert len(r.stages) == 1
    assert r.stages[0].name == "Test"
