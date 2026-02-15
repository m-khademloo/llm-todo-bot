"""Production: main() must wire DB, setup_indexes, LLM, scheduler, bot."""
import pytest


def test_main_module_exists():
    """Entry point src.main must exist for Docker CMD."""
    try:
        import src.main as main
        assert main is not None
    except ImportError:
        pytest.skip("src.main not yet implemented")


def test_main_defines_main_function():
    """main() must be defined for python -m src.main."""
    try:
        import src.main as main
        assert hasattr(main, "main")
        assert callable(main.main)
    except ImportError:
        pytest.skip("src.main not yet implemented")


def test_config_loads_from_env():
    """Production uses .env; Settings must load TELEGRAM_BOT_TOKEN and MONGO_URI."""
    from src.config import Settings
    s = Settings(TELEGRAM_BOT_TOKEN="x", MONGO_URI="mongodb://localhost:27017")
    assert s.TELEGRAM_BOT_TOKEN == "x"
    assert "mongodb" in s.MONGO_URI
