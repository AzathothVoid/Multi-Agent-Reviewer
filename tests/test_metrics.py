# import pytest
# from src.multi_agent_reviewer import metrics


# def test_metrics_module_exists():

import os
import tempfile
import pytest
from prometheus_client import CollectorRegistry
from src.multi_agent_reviewer.metrics import get_metrics
from src.multi_agent_reviewer import metrics


def test_metrics_module_exists():
    assert metrics is not None


def test_metrics_counters_exist():
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = tmpdir
        registry = CollectorRegistry()
        test_metrics = get_metrics(registry)
        for key in [
            "MAR_JOBS_STARTED",
            "MAR_JOBS_SUCCEEDED",
            "MAR_JOBS_FAILED",
            "MAR_JOB_DURATION",
            "MAR_CHECKS_RUN",
            "MAR_CHECKS_DURATION",
            "MAR_RQ_RECEIVED",
            "MAR_RQ_STARTED",
            "MAR_RQ_SUCCEEDED",
            "MAR_RQ_FAILED",
            "MAR_RQ_JOB_DURATION",
            "MAR_LLM_REQUESTS",
            "MAR_LLM_ERRORS",
            "MAR_LLM_LATENCY",
        ]:
            assert key in test_metrics


def test_metrics_increment_and_observe():
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = tmpdir
        registry = CollectorRegistry()
        test_metrics = get_metrics(registry)
        c = test_metrics["MAR_JOBS_STARTED"].labels("test_agent")
        c.inc()
        assert (
            registry.get_sample_value(
                "mar_jobs_started_total", labels={"agent": "test_agent"}
            )
            == 1.0
        )

        h = test_metrics["MAR_JOB_DURATION"].labels("test_agent")
        h.observe(2.5)
        # Histogram sum and count
        assert (
            registry.get_sample_value(
                "mar_job_duration_seconds_sum", labels={"agent": "test_agent"}
            )
            == 2.5
        )
        assert (
            registry.get_sample_value(
                "mar_job_duration_seconds_count", labels={"agent": "test_agent"}
            )
            == 1.0
        )


def test_metrics_response_returns_fastapi_response():
    import os
    import tempfile
    from fastapi import Response

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = tmpdir
        response = metrics.metrics_response()
        assert isinstance(response, Response)
        assert response.media_type == metrics.CONTENT_TYPE_LATEST


def test_ensure_multiproc_dir_creates_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "subdir")
        assert not os.path.exists(test_path)
        metrics.ensure_multiproc_dir(test_path)
        assert os.path.exists(test_path)


def test_ensure_multiproc_dir_empty_path():
    # Should not raise or create anything
    metrics.ensure_multiproc_dir("")


#     assert metrics is not None
