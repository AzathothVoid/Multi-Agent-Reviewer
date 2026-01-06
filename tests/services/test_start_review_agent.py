import pytest
from src.multi_agent_reviewer.services import start_review_agent


def test_start_review_agent_module_exists():
    assert start_review_agent is not None


def test_lock_key():
    key = start_review_agent._lock_key("o", "r", 42)
    assert key == "lock:pr:o:r:42"


def test_start_review_agent_skipped(monkeypatch):
    # Simulate lock already acquired
    monkeypatch.setattr(
        start_review_agent,
        "redis",
        type("R", (), {"set": staticmethod(lambda *a, **kw: False)})(),
    )
    monkeypatch.setattr(
        start_review_agent,
        "get_current_job",
        lambda: type("J", (), {"get_id": lambda self: "jid"})(),
    )
    monkeypatch.setattr(
        start_review_agent,
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
    payload = {"owner": "o", "repo": "r", "pr": 1}
    result = start_review_agent.start_revew_agent(payload)
    assert result["status"] == "skipped"
    assert result["reason"] == "already_running"


def test_start_review_agent_success(monkeypatch):
    # Patch redis, session, queue, get_changed_hunks, get_metrics
    class DummyJob:
        def get_id(self):
            return "jid"

    class DummyTask:
        id = 123
        status = None
        completed_at = None
        result = None

    class DummySession:
        def add(self, t):
            pass

        def commit(self):
            pass

        def refresh(self, t):
            t.id = 123

        def close(self):
            pass

    class DummyQueue:
        def enqueue(self, *a, **kw):
            class DummyEnq:
                def get_id(self):
                    return "jobid"

            return DummyEnq()

    monkeypatch.setattr(
        start_review_agent,
        "redis",
        type(
            "R",
            (),
            {
                "set": staticmethod(lambda *a, **kw: True),
                "delete": staticmethod(lambda *a, **kw: None),
            },
        )(),
    )
    monkeypatch.setattr(start_review_agent, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(start_review_agent, "session", DummySession())
    monkeypatch.setattr(start_review_agent, "queue", DummyQueue())
    monkeypatch.setattr(
        start_review_agent, "get_changed_hunks", lambda *a, **kw: {"f.py": ["hunk"]}
    )
    monkeypatch.setattr(
        start_review_agent,
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
    payload = {"owner": "o", "repo": "r", "pr": 1, "installation_id": 2}
    result = start_review_agent.start_revew_agent(payload)
    assert result["status"] == "started"
    assert result["task_id"] == 123


def test_start_review_agent_exception(monkeypatch):
    # Patch get_changed_hunks to raise, check metrics and lock cleanup
    class DummyJob:
        def get_id(self):
            return "jid"

    class DummyTask:
        id = 123
        status = None
        completed_at = None
        result = None

    class DummySession:
        def add(self, t):
            pass

        def commit(self):
            pass

        def refresh(self, t):
            t.id = 123

        def close(self):
            pass

    class DummyQueue:
        def enqueue(self, *a, **kw):
            class DummyEnq:
                def get_id(self):
                    return "jobid"

            return DummyEnq()

    class DummyMetrics:
        def __init__(self):
            self.failed = False

        def labels(self, *a, **kw):
            class C:
                def inc(inner_self):
                    self.failed = True

                def observe(inner_self, v):
                    pass

            return C()

    failed_metrics = {
        "MAR_JOBS_STARTED": DummyMetrics(),
        "MAR_JOBS_SUCCEEDED": DummyMetrics(),
        "MAR_JOBS_FAILED": DummyMetrics(),
        "MAR_JOB_DURATION": DummyMetrics(),
    }
    monkeypatch.setattr(
        start_review_agent,
        "redis",
        type(
            "R",
            (),
            {
                "set": staticmethod(lambda *a, **kw: True),
                "delete": staticmethod(lambda *a, **kw: None),
            },
        )(),
    )
    monkeypatch.setattr(start_review_agent, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(start_review_agent, "session", DummySession())
    monkeypatch.setattr(start_review_agent, "queue", DummyQueue())
    monkeypatch.setattr(
        start_review_agent,
        "get_changed_hunks",
        lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")),
    )
    monkeypatch.setattr(start_review_agent, "get_metrics", lambda reg: failed_metrics)
    payload = {"owner": "o", "repo": "r", "pr": 1, "installation_id": 2}
    with pytest.raises(Exception):
        start_review_agent.start_revew_agent(payload)
    # Should have called metrics failed
    assert failed_metrics["MAR_JOBS_FAILED"].failed is True
