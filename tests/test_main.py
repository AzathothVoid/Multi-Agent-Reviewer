import importlib

main_module = importlib.import_module("src.multi_agent_reviewer.main")


def test_main_module_exists():
    assert main_module is not None


def test_main_has_main_or_app():
    # Check for a main function or FastAPI app
    if not (hasattr(main_module, "main") or hasattr(main_module, "app")):
        print("Attributes in main module:", dir(main_module))
        import pytest

        pytest.fail(
            "Neither 'main' nor 'app' found in main module. Attributes: {}".format(
                dir(main_module)
            )
        )
    assert hasattr(main_module, "main") or hasattr(main_module, "app")
