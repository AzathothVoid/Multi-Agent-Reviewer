import pytest
from src.multi_agent_reviewer.services import llm_review_agent


def test_llm_review_agent_module_exists():
    assert llm_review_agent is not None


def test_extract_json_from_exception_handles_json():
    class DummyResp:
        def json(self):
            return {"error": {"failed_generation": '{"foo": 1}'}}

    class DummyExc(Exception):
        response = DummyResp()

    result = llm_review_agent._extract_json_from_exception(DummyExc())
    assert result == {"foo": 1}


def test_extract_json_from_exception_handles_str():
    class DummyExc(Exception):
        def __str__(self):
            return '..."failed_generation": {"bar": 2} ...'

    result = llm_review_agent._extract_json_from_exception(DummyExc())
    assert result == {"bar": 2}


def test_make_llm_returns_llm(monkeypatch):
    class DummyLLM:
        pass

    monkeypatch.setattr(llm_review_agent, "ChatGroq", lambda **kwargs: DummyLLM())
    llm = llm_review_agent._make_llm()
    assert isinstance(llm, DummyLLM)


def test_run_llm_review_success(monkeypatch):
    # Patch Job, Redis, LLM, metrics, and get_current_job
    class DummyJob:
        meta = {}

        def save_meta(self):
            pass

        result = "static-summary"

    class DummyLLM:
        def with_structured_output(self, _):
            # Return a callable (Runnable-like) object
            def chain(prompt_input):
                return llm_review_agent.LLMResponse(
                    suggestions=[
                        llm_review_agent.Suggestion(
                            id="1",
                            file="f.py",
                            start_line=1,
                            end_line=2,
                            patch="p",
                            confidence=1.0,
                            explain="e",
                        )
                    ]
                )

            return chain

    # Patch Job.fetch to accept connection kwarg
    def dummy_fetch(job_id, connection=None):
        return DummyJob()

    monkeypatch.setattr(
        llm_review_agent, "Job", type("Job", (), {"fetch": staticmethod(dummy_fetch)})
    )
    monkeypatch.setattr(llm_review_agent, "redis", None)
    monkeypatch.setattr(llm_review_agent, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(llm_review_agent, "_make_llm", lambda: DummyLLM())
    monkeypatch.setattr(
        llm_review_agent,
        "parser",
        type("Parser", (), {"get_format_instructions": staticmethod(lambda: "{}")})(),
    )

    def dummy_time():
        import contextlib

        @contextlib.contextmanager
        def cm():
            yield

        return cm()

    monkeypatch.setattr(
        llm_review_agent,
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
                                "time": staticmethod(dummy_time),
                            },
                        )()
                    )
                },
            )
            for k in [
                "MAR_JOBS_STARTED",
                "MAR_LLM_REQUESTS",
                "MAR_LLM_LATENCY",
                "MAR_JOBS_FAILED",
                "MAR_JOB_DURATION",
                "MAR_JOBS_SUCCEEDED",
            ]
        },
    )
    payload = {
        "owner": "o",
        "repo": "r",
        "pr": 1,
        "pr_title": "t",
        "changed_hunks": "h",
    }
    result = llm_review_agent.run_llm_review(payload, static_job_id="dummy")
    assert isinstance(result, list)
    assert result[0]["id"] == "1"
