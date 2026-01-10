import pytest
from src.multi_agent_reviewer.services import static_check_agent


def test_static_check_agent_module_exists():
    assert static_check_agent is not None


def test_run_static_checks_success(monkeypatch):
    # Patch get_current_job, metrics, clone_github_repo, run_command
    class DummyJob:
        meta = {}

        def save_meta(self):
            pass

    monkeypatch.setattr(static_check_agent, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(
        static_check_agent,
        "get_metrics",
        lambda reg: {
            k: type(
                "M",
                (),
                {
                    "labels": staticmethod(
                        lambda *a, **kw: type(
                            "C",
                            (),
                            {
                                "inc": staticmethod(lambda: None),
                                "observe": staticmethod(lambda v: None),
                            },
                        )()
                    )
                },
            )
            for k in [
                "MAR_JOBS_STARTED",
                "MAR_CHECKS_RUN",
                "MAR_CHECKS_DURATION",
                "MAR_JOBS_SUCCEEDED",
                "MAR_JOBS_FAILED",
                "MAR_JOB_DURATION",
            ]
        },
    )
    monkeypatch.setattr(
        static_check_agent, "clone_github_repo", lambda *a, **kw: ("/tmp", "/tmp/repo")
    )
    monkeypatch.setattr(
        static_check_agent,
        "run_command",
        lambda cmd, cwd=None: {"returncode": 0, "duration": 1.0, "stdout": ""},
    )
    payload = {
        "owner": "o",
        "repo": "r",
        "pr": 1,
        "installation_id": 1,
        "head_sha": "abc",
    }
    result = static_check_agent.run_static_checks(payload)
    assert result["status"] == "ok"
    assert "artifacts" in result


def test_run_static_checks_linter_fail(monkeypatch):
    class DummyJob:
        meta = {}

        def save_meta(self):
            pass

    monkeypatch.setattr(static_check_agent, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(
        static_check_agent,
        "get_metrics",
        lambda reg: {
            k: type(
                "M",
                (),
                {
                    "labels": staticmethod(
                        lambda *a, **kw: type(
                            "C",
                            (),
                            {
                                "inc": staticmethod(lambda: None),
                                "observe": staticmethod(lambda v: None),
                            },
                        )()
                    )
                },
            )
            for k in [
                "MAR_JOBS_STARTED",
                "MAR_CHECKS_RUN",
                "MAR_CHECKS_DURATION",
                "MAR_JOBS_SUCCEEDED",
                "MAR_JOBS_FAILED",
                "MAR_JOB_DURATION",
            ]
        },
    )
    monkeypatch.setattr(
        static_check_agent, "clone_github_repo", lambda *a, **kw: ("/tmp", "/tmp/repo")
    )

    # Black passes, flake8 fails
    def fake_run_command(cmd, cwd=None):
        # cmd is a list, so check for 'flake8' as an element
        if any("flake8" == str(x) for x in cmd):
            return {"returncode": 1, "duration": 1.0, "stdout": "err"}
        return {"returncode": 0, "duration": 1.0, "stdout": ""}

    monkeypatch.setattr(static_check_agent, "run_command", fake_run_command)
    payload = {
        "owner": "o",
        "repo": "r",
        "pr": 1,
        "installation_id": 1,
        "head_sha": "abc",
    }
    result = static_check_agent.run_static_checks(payload)
    # Accept 'ok' status but ensure linter error is present in artifacts
    assert result["status"] == "ok"
    assert "artifacts" in result
    assert any(
        "flake8" in k and v["returncode"] == 1 for k, v in result["artifacts"].items()
    )


def test_run_static_checks_clone_error(monkeypatch):
    class DummyJob:
        meta = {}

        def save_meta(self):
            pass

    monkeypatch.setattr(static_check_agent, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(
        static_check_agent,
        "get_metrics",
        lambda reg: {
            k: type(
                "M",
                (),
                {
                    "labels": staticmethod(
                        lambda *a, **kw: type(
                            "C",
                            (),
                            {
                                "inc": staticmethod(lambda: None),
                                "observe": staticmethod(lambda v: None),
                            },
                        )()
                    )
                },
            )
            for k in [
                "MAR_JOBS_STARTED",
                "MAR_CHECKS_RUN",
                "MAR_CHECKS_DURATION",
                "MAR_JOBS_SUCCEEDED",
                "MAR_JOBS_FAILED",
                "MAR_JOB_DURATION",
            ]
        },
    )
    monkeypatch.setattr(
        static_check_agent,
        "clone_github_repo",
        lambda *a, **kw: (_ for _ in ()).throw(Exception("clone error")),
    )
    payload = {
        "owner": "o",
        "repo": "r",
        "pr": 1,
        "installation_id": 1,
        "head_sha": "abc",
    }
    with pytest.raises(Exception):
        static_check_agent.run_static_checks(payload)
