from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest
from pytest import MonkeyPatch

from core.monitoring import monitor_script


@pytest.fixture
def mock_monitoring_deps(monkeypatch: MonkeyPatch, reload_settings: Any) -> Any:
    """
    Mocks all external services that @monitor_script talks to:
    - send_error_email
    - create_postgres_engine
    - write_monitoring_db
    - MonitorScript (to prevent threading)
    """
    # Call reload FIRST, INSIDE the fixture
    reload_settings({})

    # Apply patches
    mock_send = MagicMock()
    mock_create_engine = MagicMock()
    mock_write_db = MagicMock()

    mock_monitor_script_class = MagicMock()
    mock_monitor_script_instance = MagicMock()
    mock_monitor_script_instance.get_summary_df.return_value = MagicMock()
    mock_monitor_script_class.return_value.__enter__.return_value = (
        mock_monitor_script_instance
    )

    mock_summary_df = pd.DataFrame({"records_updated": [10]})
    mock_monitor_script_instance.get_summary_df.return_value = mock_summary_df

    monkeypatch.setattr("core.monitoring.send_error_email", mock_send)
    monkeypatch.setattr("core.monitoring.create_postgres_engine", mock_create_engine)
    monkeypatch.setattr("core.monitoring.write_monitoring_db", mock_write_db)
    monkeypatch.setattr("core.monitoring.MonitorScript", mock_monitor_script_class)

    return mock_send, mock_write_db, mock_monitor_script_instance


def test_monitor_script_success(mock_monitoring_deps: Any) -> None:
    """
    Tests that the decorator calls the function, logs to DB,
    and does NOT send an email on success.
    """
    mock_send, mock_write_db, _ = mock_monitoring_deps

    @monitor_script(main_function_name="test_success")
    def successful_func() -> str:
        return "Total Records Updated: 10"

    result = successful_func()

    assert result == "Total Records Updated: 10"
    assert not mock_send.called
    assert mock_write_db.called


def test_monitor_script_failure(mock_monitoring_deps: Any) -> None:
    """
    Tests that the decorator catches an error, sends an email,
    logs to DB, and re-raises the error.
    """

    mock_send, mock_write_db, mock_instance = mock_monitoring_deps

    mock_summary_df_fail = pd.DataFrame({"records_updated": [0]})
    mock_instance.get_summary_df.return_value = mock_summary_df_fail

    @monitor_script(main_function_name="test_fail")
    def failing_func() -> None:
        raise ValueError("Something broke")

    with pytest.raises(ValueError, match="Something broke"):
        failing_func()

    assert mock_send.called
    assert mock_write_db.called
