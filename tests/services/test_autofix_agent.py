import pytest
from src.multi_agent_reviewer.services import autofix_agent


def test_autofix_agent_module_exists():
    assert autofix_agent is not None
