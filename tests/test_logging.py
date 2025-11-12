import logging
from collections.abc import Iterator
from typing import Any

import pytest
from core.logging import setup_logging


@pytest.fixture(autouse=True)
def reset_logging() -> Iterator[None]:
    """Reset logging configuration before each test."""
    # Store original handlers and level
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    yield

    # Clean up after test
    root.handlers = original_handlers
    root.setLevel(original_level)


def test_logging_level_production(reload_settings: Any, reset_logging: Any) -> None:
    """
    Tests that the default log level is INFO
    when EDP_ENVIRONMENT is not 'development'.
    """
    # Mock settings.EDP_ENVIRONMENT
    reload_settings({"EDP_ENVIRONMENT": "Production"})

    # Clear any existing handlers before setup
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    setup_logging()

    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO


def test_logging_level_development(reload_settings: Any, reset_logging: Any) -> None:
    """
    Tests that the log level is DEBUG
    when EDP_ENVIRONMENT is 'development'.
    """
    # Mock settings.EDP_ENVIRONMENT
    reload_settings({"EDP_ENVIRONMENT": "development"})

    # Clear any existing handlers before setup
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    setup_logging()

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_logging_level_override() -> None:
    """
    Tests that passing a log level string overrides the environment.
    """
    setup_logging(log_level_str="WARNING")

    root_logger = logging.getLogger()
    assert root_logger.level == logging.WARNING
