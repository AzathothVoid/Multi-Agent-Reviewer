import os
from prometheus_client import (
    Counter,
    Histogram,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    multiprocess,
)
from fastapi import Response


def get_metrics(registry):
    metrics = {}
    metrics["MAR_JOBS_STARTED"] = Counter(
        "mar_jobs_started_total", "Jobs started", ["agent"], registry=registry
    )
    metrics["MAR_JOBS_SUCCEEDED"] = Counter(
        "mar_jobs_succeeded_total", "Jobs succeeded", ["agent"], registry=registry
    )
    metrics["MAR_JOBS_FAILED"] = Counter(
        "mar_jobs_failed_total",
        "Jobs failed",
        ["agent", "error_type"],
        registry=registry,
    )
    metrics["MAR_JOB_DURATION"] = Histogram(
        "mar_job_duration_seconds",
        "Job duration seconds",
        ["agent"],
        buckets=(0.01, 0.05, 0.2, 1, 3, 10, 30, 60),
        registry=registry,
    )
    metrics["MAR_CHECKS_RUN"] = Counter(
        "mar_checks_run_total",
        "Static checks run",
        ["agent", "check_name", "result"],
        registry=registry,
    )
    metrics["MAR_CHECKS_DURATION"] = Histogram(
        "mar_checks_duration_seconds",
        "Static check duration",
        ["agent", "check_name"],
        buckets=(0.01, 0.05, 0.2, 1, 3, 10),
        registry=registry,
    )
    metrics["MAR_RQ_RECEIVED"] = Counter(
        "mar_rq_jobs_received_total",
        "RQ jobs received",
        ["agent", "queue"],
        registry=registry,
    )
    metrics["MAR_RQ_STARTED"] = Counter(
        "mar_rq_jobs_started_total",
        "RQ jobs started",
        ["agent", "queue"],
        registry=registry,
    )
    metrics["MAR_RQ_SUCCEEDED"] = Counter(
        "mar_rq_jobs_succeeded_total",
        "RQ jobs succeeded",
        ["agent", "queue"],
        registry=registry,
    )
    metrics["MAR_RQ_FAILED"] = Counter(
        "mar_rq_jobs_failed_total",
        "RQ jobs failed",
        ["agent", "queue", "error_type"],
        registry=registry,
    )
    metrics["MAR_RQ_JOB_DURATION"] = Histogram(
        "mar_rq_job_duration_seconds",
        "RQ job duration",
        ["agent", "queue"],
        buckets=(0.01, 0.05, 0.2, 1, 3, 10, 30, 60),
        registry=registry,
    )
    metrics["MAR_LLM_REQUESTS"] = Counter(
        "mar_llm_requests_total",
        "LLM requests",
        ["agent", "model", "purpose"],
        registry=registry,
    )
    metrics["MAR_LLM_ERRORS"] = Counter(
        "mar_llm_request_errors_total",
        "LLM request errors",
        ["agent", "model", "error_type"],
        registry=registry,
    )
    metrics["MAR_LLM_LATENCY"] = Histogram(
        "mar_llm_latency_seconds",
        "LLM latency seconds",
        ["agent", "model"],
        buckets=(0.05, 0.2, 0.5, 1, 2, 5, 10, 30),
        registry=registry,
    )
    return metrics


def metrics_response() -> Response:
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def ensure_multiproc_dir(path: str):
    if not path:
        return
    os.makedirs(path, exist_ok=True)
