import pytest
from src.multi_agent_reviewer import db


def test_db_base_class():
    assert hasattr(db, "Base")
    assert hasattr(db, "engine")
    assert hasattr(db, "Session")
    assert hasattr(db, "session")


def test_db_session_usable():
    # Should be able to create a session and access Base metadata
    s = db.Session()
    assert s is not None
    assert hasattr(db.Base, "metadata")
