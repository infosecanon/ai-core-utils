from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus

import pandas as pd
import pytest
from sqlalchemy.engine import Engine

from core.connectors.postgres import (
    DBLog,
    create_postgres_engine,
    write_to_database,
)

# Mock for the 'Table' object
mock_table = MagicMock()
mock_table.insert.return_value = MagicMock()

# Mock for the SQLAlchemy engine
mock_engine = MagicMock(spec=Engine)
mock_connection = MagicMock()
# This line makes `with mock_engine.connect() as conn:` work
mock_engine.connect.return_value.__enter__.return_value = mock_connection


def test_create_postgres_engine(reload_settings: Any) -> None:
    """
    Tests that create_postgres_engine calls sqlalchemy.create_engine
    with the DSN from the settings.
    """
    # Call reload first
    reload_settings(
        {
            "POSTGRES__PG_HOST": "test.host",
            "POSTGRES__PG_PORT": "1234",
            "POSTGRES__PG_USER": "test_user",
            "POSTGRES__PG_PASSWORD": "test_pass",
            "POSTGRES__PG_DATABASE": "test_db",
        }
    )

    user = quote_plus("test_user")
    pw = quote_plus("test_pass")
    expected_dsn = f"postgresql+psycopg2://{user}:{pw}@test.host:1234/test_db"

    create_postgres_engine.cache_clear()

    with patch("core.connectors.postgres.create_engine") as mock_create_engine:
        create_postgres_engine()
        mock_create_engine.assert_called_with(
            expected_dsn, pool_size=10, max_overflow=20
        )


def test_dblog_log_completion(reload_settings: Any) -> None:
    """
    Tests that DBLog.log_completion constructs and executes
    the correct insert statement.
    """
    # Call reload first
    reload_settings({"POSTGRES__PG_LOGTABLENAME": "test_log_table"})

    from unittest.mock import ANY

    # Apply patch *AFTER* reload
    with patch(
        "core.connectors.postgres.Table", return_value=mock_table
    ) as mock_Table_class:
        # Reset mock_engine's calls for this test
        mock_engine.reset_mock()
        mock_connection.reset_mock()

        db_logger = DBLog(
            engine=mock_engine, datatablename="staging_table", objectname="MyObject"
        )

        db_logger.log_completion(
            start_time=MagicMock(), end_time=MagicMock(), record_count=123
        )

        # Asserts are now inside the 'with' block
        mock_Table_class.assert_called_with(
            "test_log_table",
            ANY,
            autoload_with=mock_engine,
        )

        mock_engine.connect.assert_called_once()
        assert mock_connection.execute.called

        # insert_values = mock_table.insert().values.call_args[1]
        # OR, more readably:
        insert_values = mock_table.insert().values.call_args.kwargs

        assert insert_values["object"] == "MyObject"
        assert insert_values["data_table"] == "staging_table"


def test_write_to_database_failure(reload_settings: Any) -> None:
    """
    Tests that write_to_database calls send_error_email
    and re-raises the exception on failure.
    """
    # RELOAD isn't strictly needed here, but it's good practice
    # to be aware of the ordering

    # Apply patch *AFTER* reload
    with patch("core.connectors.postgres.send_error_email") as mock_send_error_email:
        mock_df = MagicMock(spec=pd.DataFrame)
        mock_df.to_sql.side_effect = ValueError("Test DB Error")

        with pytest.raises(ValueError, match="Test DB Error"):
            write_to_database(df=mock_df, table_name="my_table", engine=mock_engine)

        assert mock_send_error_email.called
        call_args = mock_send_error_email.call_args[0]
        assert isinstance(call_args[0], ValueError)
        assert call_args[1] == "Write to database public.my_table"
