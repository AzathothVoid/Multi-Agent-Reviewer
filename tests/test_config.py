import pytest
from src.multi_agent_reviewer import config


def test_config_module_exists():
    assert config is not None


def test_config_has_database_url():
    assert hasattr(config.settings, "database_url")
    assert isinstance(config.settings.database_url, str)
