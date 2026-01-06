import pytest
from src.multi_agent_reviewer.services import finalizer_agent


def test_finalizer_agent_module_exists():
    assert finalizer_agent is not None


def test_finalize_review_success(monkeypatch):
    # Patch session, Job, get_current_job, get_metrics, _unlock_pr
    class DummyTask:
        status = None
        completed_at = None
        result = None
        owner = "o"
        repo = "r"
        pr_number = 1

    class DummySession:
        def get(self, cls, id):
            return DummyTask()

        def commit(self):
            pass

        def close(self):
            pass

    class DummyJob:
        id = 1
        result = "result"

        @staticmethod
        def fetch(job_id, connection=None):
            return DummyJob()

    monkeypatch.setattr(finalizer_agent, "session", DummySession())
    monkeypatch.setattr(finalizer_agent, "Job", DummyJob)
    monkeypatch.setattr(finalizer_agent, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(
        finalizer_agent,
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
                "MAR_JOBS_SUCCEEDED",
                "MAR_JOBS_FAILED",
                "MAR_JOB_DURATION",
            ]
        },
    )
    monkeypatch.setattr(finalizer_agent, "_unlock_pr", lambda *a, **kw: None)
    finalizer_agent.finalize_review(1, "llm", "static")


def test_finalize_review_missing_task(monkeypatch):
    class DummySession:
        def get(self, cls, id):
            return None

        def commit(self):
            pass

        def close(self):
            pass

    class DummyJob:
        id = 1
        result = "result"

        @staticmethod
        def fetch(job_id, connection=None):
            return DummyJob()

    monkeypatch.setattr(finalizer_agent, "session", DummySession())
    monkeypatch.setattr(finalizer_agent, "Job", DummyJob)
    monkeypatch.setattr(finalizer_agent, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(
        finalizer_agent,
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
                "MAR_JOBS_SUCCEEDED",
                "MAR_JOBS_FAILED",
                "MAR_JOB_DURATION",
            ]
        },
    )
    monkeypatch.setattr(finalizer_agent, "_unlock_pr", lambda *a, **kw: None)
    # Should not raise
    finalizer_agent.finalize_review(1, "llm", "static")
