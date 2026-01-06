import pytest
from src.multi_agent_reviewer.models import Task


def test_task_model_fields():
    task = Task.Task(
        repo="test-repo", pr_number=1, owner="test-owner", payload={"foo": "bar"}
    )
    assert task.repo == "test-repo"
    assert task.pr_number == 1
    assert task.owner == "test-owner"
    assert task.payload == {"foo": "bar"}
    assert hasattr(task, "status")
    assert hasattr(task, "created_at")
    assert hasattr(task, "completed_at")


def test_task_model_types_and_status():
    task = Task.Task(
        repo="repo-x",
        pr_number=42,
        owner="owner-x",
        payload={"bar": 1},
        status=Task.TaskStatus.PENDING,
    )
    assert isinstance(task.repo, str)
    assert isinstance(task.pr_number, int)
    assert isinstance(task.owner, str)
    assert isinstance(task.payload, dict)
    assert task.status.name in ["PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"]


def test_task_model_edge_cases():
    # result and completed_at can be None
    task = Task.Task(
        repo="repo-y",
        pr_number=2,
        owner="owner-y",
        payload={},
        result=None,
        completed_at=None,
    )
    assert task.result is None
    assert task.completed_at is None
