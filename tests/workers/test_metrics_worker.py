import pytest
from prometheus_client import CollectorRegistry
from src.multi_agent_reviewer.metrics import get_metrics
from src.multi_agent_reviewer.workers import metrics_worker


def test_metrics_worker_module_exists():
    assert metrics_worker is not None
