import pytest
from src.multi_agent_reviewer.workers import rq_worker


def test_rq_worker_module_exists():
    assert rq_worker is not None
