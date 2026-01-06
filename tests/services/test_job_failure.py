import pytest
from src.multi_agent_reviewer.services import job_failure


def test_job_failure_module_exists():
    assert job_failure is not None


def test_unlock_pr(monkeypatch):
    called = {}

    class DummyRedis:
        def delete(self, key):
            called["key"] = key

    monkeypatch.setattr(job_failure, "redis", DummyRedis())
    job_failure._unlock_pr("o", "r", 42)
    assert called["key"] == "lock:pr:o:r:42"


def test_on_job_failure_task_found(monkeypatch):
    # Patch session, Task, redis, logger
    class DummyTask:
        status = None
        result = None
        completed_at = None
        owner = "o"
        repo = "r"
        pr_number = 1

    class DummySession:
        def query(self, cls):
            class Q:
                def filter(self, cond):
                    class F:
                        def first(self):
                            return DummyTask()

                    return F()

            return Q()

        def commit(self):
            pass

        def close(self):
            pass

    class DummyRedis:
        def delete(self, key):
            self.key = key

    class DummyLogger:
        def info(self, *a, **kw):
            self.info_called = True

        def warning(self, *a, **kw):
            self.warning_called = True

        def exception(self, *a, **kw):
            self.exception_called = True

    monkeypatch.setattr(job_failure, "session", DummySession())
    monkeypatch.setattr(job_failure, "redis", DummyRedis())
    monkeypatch.setattr(job_failure, "logger", DummyLogger())

    class DummyJob:
        id = "jid"
        args = [{"task_id": 1}]
        kwargs = {}

    job_failure.on_job_failure(DummyJob(), None, Exception, Exception("fail"), None)


def test_on_job_failure_task_not_found(monkeypatch):
    class DummySession:
        def query(self, cls):
            class Q:
                def filter(self, cond):
                    class F:
                        def first(self):
                            return None

                    return F()

            return Q()

        def commit(self):
            pass

        def close(self):
            pass

    class DummyRedis:
        def delete(self, key):
            self.key = key

    class DummyLogger:
        def info(self, *a, **kw):
            self.info_called = True

        def warning(self, *a, **kw):
            self.warning_called = True

        def exception(self, *a, **kw):
            self.exception_called = True

    monkeypatch.setattr(job_failure, "session", DummySession())
    monkeypatch.setattr(job_failure, "redis", DummyRedis())
    monkeypatch.setattr(job_failure, "logger", DummyLogger())

    class DummyJob:
        id = "jid"
        args = [{"task_id": 1}]
        kwargs = {}

    job_failure.on_job_failure(DummyJob(), None, Exception, Exception("fail"), None)


def test_on_job_failure_no_task_id(monkeypatch):
    class DummySession:
        def close(self):
            pass

    class DummyRedis:
        def delete(self, key):
            self.key = key

    class DummyLogger:
        def info(self, *a, **kw):
            self.info_called = True

        def warning(self, *a, **kw):
            self.warning_called = True

        def exception(self, *a, **kw):
            self.exception_called = True

    monkeypatch.setattr(job_failure, "session", DummySession())
    monkeypatch.setattr(job_failure, "redis", DummyRedis())
    monkeypatch.setattr(job_failure, "logger", DummyLogger())

    class DummyJob:
        id = "jid"
        args = [{"not_task_id": 1}]
        kwargs = {}

    job_failure.on_job_failure(DummyJob(), None, Exception, Exception("fail"), None)
