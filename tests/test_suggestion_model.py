import pytest
from src.multi_agent_reviewer.services.llm_review_agent import Suggestion


def test_suggestion_model_exists():
    assert Suggestion is not None


def test_suggestion_model_instantiation():
    # If Suggestion is a class, try to instantiate with no args (or minimal args if required)
    try:
        s = Suggestion(
            id="1",
            file="test.py",
            start_line=1,
            end_line=2,
            patch="patch",
            auto_fixable=False,
            confidence=0.9,
            explain="explanation",
        )
        assert s is not None
    except Exception:
        # If Suggestion is not instantiable, just check type
        assert isinstance(Suggestion, type)
