import pytest
from src.multi_agent_reviewer import cli


def test_cli_module_exists():
    assert cli is not None


def test_cli_has_main_or_app():
    # Check for a main function or click/typer app
    assert hasattr(cli, "main") or hasattr(cli, "app")
