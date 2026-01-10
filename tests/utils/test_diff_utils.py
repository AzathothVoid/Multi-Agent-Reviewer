import pytest
from src.multi_agent_reviewer.utils import diff_utils


def test_diff_utils_module_exists():
    assert diff_utils is not None


def test_diff_utils_has_diff_function():
    # Check for a function that computes diffs
    assert any(
        callable(getattr(diff_utils, attr)) and "diff" in attr
        for attr in dir(diff_utils)
    )
