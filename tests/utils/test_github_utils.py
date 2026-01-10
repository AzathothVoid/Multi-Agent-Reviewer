import pytest
from src.multi_agent_reviewer.utils import github_utils


def test_github_utils_module_exists():
    assert github_utils is not None


def test_github_utils_has_github_function():
    # Check for a function or class related to GitHub
    assert any(
        callable(getattr(github_utils, attr)) and "github" in attr.lower()
        for attr in dir(github_utils)
    ) or any("github" in attr.lower() for attr in dir(github_utils))
