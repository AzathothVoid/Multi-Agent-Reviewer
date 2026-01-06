import pytest
from src.multi_agent_reviewer.utils import utils


def test_utils_module_exists():
    assert utils is not None


def test_utils_has_utility_function():
    # Check for at least one callable utility function
    assert any(
        callable(getattr(utils, attr))
        for attr in dir(utils)
        if not attr.startswith("__")
    )
