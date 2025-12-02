import importlib
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest
from pytest import MonkeyPatch

import core.monitoring


@pytest.fixture
def mock_monitoring_deps(monkeypatch: MonkeyPatch, reload_settings: Any) -> Any:
    # 1. SETUP: Reset settings
    reload_settings({"EDP_ENVIRONMENT": "Development"})

    # 2. CREATE MOCKS
    mock_send = MagicMock()
    mock_write_db = MagicMock()

    # --- Mock the SQLAlchemy Engine & Connection ---
    # This is critical. The code calls create_postgres_engine(), gets an engine,
    # and calls engine.connect(). We must mock this entire chain
    # to prevent real network calls.
    mock_engine = MagicMock()
    mock_connection = MagicMock()
    # Support "with engine.connect() as conn:"
    mock_engine.connect.return_value.__enter__.return_value = mock_connection

    mock_create_engine_func = MagicMock(return_value=mock_engine)

    # 3. PATCH SOURCES (BEFORE RELOAD)
    # We patch the definitions in core.connectors.postgres.
    # When we reload monitoring next, it will import these Mocks.
    monkeypatch.setattr(
        "core.connectors.postgres.create_postgres_engine", mock_create_engine_func
    )
    monkeypatch.setattr("core.connectors.postgres.write_to_database", mock_write_db)

    # Patch SMTP
    mock_smtp_instance = MagicMock()
    monkeypatch.setattr("smtplib.SMTP", MagicMock(return_value=mock_smtp_instance))

    # 4. RELOAD core.monitoring
    # This forces monitoring to re-execute its imports, grabbing our Mocks.
    importlib.reload(core.monitoring)

    # 5. PATCH INTERNALS (AFTER RELOAD)
    # These items are defined inside monitoring.py
    # or need special handling (like settings).

    # Force "Development" settings using SimpleNamespace (so == works)
    mock_settings = SimpleNamespace(
        EDP_ENVIRONMENT="Development",
        POSTGRES=SimpleNamespace(
            DB_TYPE="postgresql"
        ),  # Nested structure for DB_TYPE check
    )
    monkeypatch.setattr("core.monitoring.settings", mock_settings)

    # Patch items defined inside monitoring.py that got reset by reload
    monkeypatch.setattr("core.monitoring.send_error_email", mock_send)

    mock_monitor_script_class = MagicMock()
    mock_monitor_script_instance = MagicMock()
    mock_monitor_script_class.return_value.__enter__.return_value = (
        mock_monitor_script_instance
    )
    mock_monitor_script_instance.get_summary_df.return_value = pd.DataFrame(
        {"records_updated": [10]}
    )
    monkeypatch.setattr("core.monitoring.MonitorScript", mock_monitor_script_class)

    return mock_send, mock_write_db, mock_monitor_script_instance


def test_monitor_script_success(mock_monitoring_deps: Any) -> None:
    mock_send, _, _ = mock_monitoring_deps

    @core.monitoring.monitor_script(main_function_name="test_success")
    def successful_func() -> str:
        return "Total Records Updated: 10"

    result = successful_func()

    assert result == "Total Records Updated: 10"
    assert not mock_send.called
    # Note: We assert the DB write happened implicitly via no exception,
    # or you can assert mock_engine.connect.called if you wish.


def test_monitor_script_failure(mock_monitoring_deps: Any) -> None:
    mock_send, _, mock_instance = mock_monitoring_deps
    mock_instance.get_summary_df.return_value = pd.DataFrame({"records_updated": [0]})

    @core.monitoring.monitor_script(main_function_name="test_fail")
    def failing_func() -> None:
        raise ValueError("Something broke")

    with pytest.raises(ValueError, match="Something broke"):
        failing_func()

    assert mock_send.called
