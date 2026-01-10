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

    def get_or_create(metric_cls, name, documentation, labelnames, **kwargs):
        for collector in getattr(registry, "_names_to_collectors", {}).values():
            if hasattr(collector, "name") and collector.name == name:
                return collector
        return metric_cls(name, documentation, labelnames, registry=registry, **kwargs)

    metrics["MAR_JOBS_STARTED"] = get_or_create(
        Counter, "mar_jobs_started_total", "Jobs started", ["agent"]
    )
    metrics["MAR_JOBS_SUCCEEDED"] = get_or_create(
        Counter, "mar_jobs_succeeded_total", "Jobs succeeded", ["agent"]
    )
    metrics["MAR_JOBS_FAILED"] = get_or_create(
        Counter, "mar_jobs_failed_total", "Jobs failed", ["agent", "error_type"]
    )
    metrics["MAR_JOB_DURATION"] = get_or_create(
        Histogram,
        "mar_job_duration_seconds",
        "Job duration seconds",
        ["agent"],
        buckets=(0.01, 0.05, 0.2, 1, 3, 10, 30, 60),
    )
    metrics["MAR_CHECKS_RUN"] = get_or_create(
        Counter,
        "mar_checks_run_total",
        "Static checks run",
        ["agent", "check_name", "result"],
    )
    metrics["MAR_CHECKS_DURATION"] = get_or_create(
        Histogram,
        "mar_checks_duration_seconds",
        "Static check duration",
        ["agent", "check_name"],
        buckets=(0.01, 0.05, 0.2, 1, 3, 10),
    )
    metrics["MAR_RQ_RECEIVED"] = get_or_create(
        Counter, "mar_rq_jobs_received_total", "RQ jobs received", ["agent", "queue"]
    )
    metrics["MAR_RQ_STARTED"] = get_or_create(
        Counter, "mar_rq_jobs_started_total", "RQ jobs started", ["agent", "queue"]
    )
    metrics["MAR_RQ_SUCCEEDED"] = get_or_create(
        Counter, "mar_rq_jobs_succeeded_total", "RQ jobs succeeded", ["agent", "queue"]
    )
    metrics["MAR_RQ_FAILED"] = get_or_create(
        Counter,
        "mar_rq_jobs_failed_total",
        "RQ jobs failed",
        ["agent", "queue", "error_type"],
    )
    metrics["MAR_RQ_JOB_DURATION"] = get_or_create(
        Histogram,
        "mar_rq_job_duration_seconds",
        "RQ job duration",
        ["agent", "queue"],
        buckets=(0.01, 0.05, 0.2, 1, 3, 10, 30, 60),
    )
    metrics["MAR_LLM_REQUESTS"] = get_or_create(
        Counter, "mar_llm_requests_total", "LLM requests", ["agent", "model", "purpose"]
    )
    metrics["MAR_LLM_ERRORS"] = get_or_create(
        Counter,
        "mar_llm_request_errors_total",
        "LLM request errors",
        ["agent", "model", "error_type"],
    )
    metrics["MAR_LLM_LATENCY"] = get_or_create(
        Histogram,
        "mar_llm_latency_seconds",
        "LLM latency seconds",
        ["agent", "model"],
        buckets=(0.05, 0.2, 0.5, 1, 2, 5, 10, 30),
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
