import pytest
from src.multi_agent_reviewer.models import Repo


def test_repo_model_fields():
    repo = Repo.Repo(
        repo_name="test-repo",
        webhook_secret="secret",
        installation_id=123,
        owner="test-owner",
    )
    assert repo.repo_name == "test-repo"
    assert repo.webhook_secret == "secret"
    assert repo.installation_id == 123
    assert repo.owner == "test-owner"
    assert hasattr(repo, "created_at")


def test_repo_model_types():
    repo = Repo.Repo(
        repo_name="repo-x", webhook_secret=None, installation_id=1, owner="owner-x"
    )
    assert isinstance(repo.repo_name, str)
    assert repo.webhook_secret is None or isinstance(repo.webhook_secret, str)
    assert isinstance(repo.installation_id, int)
    assert isinstance(repo.owner, str)


def test_repo_model_edge_cases():
    # webhook_secret can be None
    repo = Repo.Repo(
        repo_name="repo-y", webhook_secret=None, installation_id=2, owner="owner-y"
    )
    assert repo.webhook_secret is None
