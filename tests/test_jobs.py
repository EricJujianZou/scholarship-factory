import time

import pytest

from scholarship_factory.jobs import ACTIONS, JobBusy, JobRunner, JobState


def _wait(runner: JobRunner, timeout: float = 30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = runner.current()
        if job and job.state != JobState.RUNNING:
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_a_job_runs_the_cli_and_captures_its_output(tmp_path):
    runner = JobRunner(str(tmp_path / "t.db"))
    runner.start("list", "List", ["list"])

    job = _wait(runner)
    assert job.state == JobState.SUCCEEDED
    assert job.exit_code == 0


def test_a_failing_command_is_reported_not_raised(tmp_path):
    runner = JobRunner(str(tmp_path / "t.db"))
    runner.start("show", "Show", ["show", "does-not-exist"])

    job = _wait(runner)
    assert job.state == JobState.FAILED
    assert job.exit_code != 0
    assert any("not found" in line for line in job.lines)


def test_the_job_runs_against_the_runners_database(tmp_path):
    """SF_DB_PATH is how the child is told which store to touch."""
    from scholarship_factory.models import Opportunity
    from scholarship_factory.store import OpportunityStore

    db_path = str(tmp_path / "t.db")
    OpportunityStore(db_path).insert(
        Opportunity(
            title="Findable Grant",
            apply_url="https://example.com/g",
            source_url="https://example.com/g",
        )
    )

    runner = JobRunner(db_path)
    runner.start("list", "List", ["list"])

    job = _wait(runner)
    assert any("Findable Grant" in line for line in job.lines)


def test_a_second_job_is_refused_while_one_runs(tmp_path):
    runner = JobRunner(str(tmp_path / "t.db"))
    runner.start("list", "List", ["list"])
    try:
        with pytest.raises(JobBusy):
            runner.start("list", "List again", ["list"])
    finally:
        _wait(runner)


def test_a_new_job_may_start_once_the_last_one_finished(tmp_path):
    runner = JobRunner(str(tmp_path / "t.db"))
    runner.start("list", "List", ["list"])
    _wait(runner)

    runner.start("list", "List again", ["list"])
    assert _wait(runner).state == JobState.SUCCEEDED


def test_every_action_states_what_it_costs():
    """The button copy is the only warning before an expensive run."""
    for action in ACTIONS:
        assert action.description.strip()
        assert action.cost.strip()
        assert action.args
