"""
Utilities for connecting to and interacting with a PostgreSQL database.

This module provides:
- A standardized function to create a SQLAlchemy engine.
- The `DBLog` class for writing to a pipeline log table.
- The `write_to_database` function for robust DataFrame insertion.
"""

import logging
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Optional

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.engine import Engine

# Import from our new library modules
from ..alerting import send_error_email
from ..config import settings

# Get a logger instance for this module
logger = logging.getLogger(__name__)


# --- Standardized Engine Creation ---


@lru_cache
def create_postgres_engine() -> Engine:
    """
    Creates and returns a SQLAlchemy engine using the global settings.

    This function is cached, so it will return the same engine
    instance on subsequent calls, efficient for connection pooling.

    Returns:
        A SQLAlchemy Engine instance.
    """
    try:
        engine = create_engine(
            settings.POSTGRES.dsn,
            pool_size=10,  # Example: Use Pydantic to set this
            max_overflow=20,  # Example: Use Pydantic to set this
        )
        logger.info(f"PostgreSQL engine created for {settings.POSTGRES.PG_HOST}")
        return engine
    except Exception as e:
        logger.critical(f"Failed to create PostgreSQL engine: {e}", exc_info=True)
        raise


# --- Database Logging Utilities ---


class LogType(Enum):
    """Enumeration for database log entry types."""

    INFO = 1
    EXCEPTION = 2
    OTHER = 3


class Result(Enum):
    """Enumeration for database log entry results."""

    SUCCESS = 1
    FAIL = 2
    OTHER = 3


class DBLog:
    """
    A helper class to standardize writing log entries to the database.

    Reads the log table name from the global POSTGRES settings.
    """

    def __init__(self, engine: Engine, datatablename: str, objectname: str):
        """
        Initializes the logger.

        Args:
            engine: The SQLAlchemy engine for the DB connection.
            datatablename: The name of the *data table* being modified.
            objectname: The logical *object name* being processed.
        """
        self.engine = engine
        self.data_table_name = datatablename
        self.object_name = objectname
        self._log_table = None
        self._log_table_name = settings.POSTGRES.PG_LOGTABLENAME

        # Pre-load the table metadata
        try:
            self._log_table = Table(
                self._log_table_name, MetaData(), autoload_with=self.engine
            )
        except Exception as e:
            logger.error(
                f"DBLog failed to autoload {self._log_table_name}. "
                f"Logs will not be written to DB. Error: {e}",
                exc_info=True,
            )

    def log_completion(
        self, start_time: datetime, end_time: datetime, record_count: int
    ) -> None:
        """Logs a completion message to the pipeline log table."""
        message = f"{self.data_table_name} Refresh Complete"
        log_update_message = f"{str(record_count)} Records Refreshed"
        self.add_log(
            eventtype=LogType.INFO,
            start_time=start_time,
            end_time=end_time,
            message=message,
            description=log_update_message,
            result=Result.SUCCESS,
        )

    def log_error(
        self,
        event_time: datetime,
        error_message: str,
        traceback: str,
        additional_information: str = "None Provided",
    ) -> None:
        """Logs an error message to the pipeline log table."""
        self.add_log(
            eventtype=LogType.EXCEPTION,
            start_time=event_time,
            end_time=event_time,
            message=error_message,
            description=traceback,
            result=Result.FAIL,
            sup_message=additional_information,
        )

    def add_log(
        self,
        eventtype: LogType,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        message: str = "None Provided",
        description: str = "None Provided",
        result: Result = Result.OTHER,
        sup_message: str = "None Provided",
    ) -> None:
        """The core method for inserting a log entry into the database."""
        if self._log_table is None:
            logger.warning(
                f"DBLog: Cannot write log, {self._log_table_name} table not loaded."
            )
            return

        log_dict = {
            "data_table": self.data_table_name,
            "end_timestamp": end_time or datetime.now(),
            "start_timestamp": start_time,
            "log_type": eventtype.name,
            "object": self.object_name,
            "message": message,
            "sub_message": description,
            "sup_message": sup_message,
            "result": result.name,
        }

        try:
            insert_statement = self._log_table.insert().values(**log_dict)
            with self.engine.connect() as conn:
                conn.execute(insert_statement)
                conn.commit()  # Ensure the log is committed
        except Exception as e:
            logger.error(
                f"CRITICAL: Failed to write to log table {self._log_table_name}."
                f" Log entry was: {log_dict}. Error: {e}",
                exc_info=True,
            )


# --- Standardized Data Writing ---


def write_to_database(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    schema: str = "public",
    if_exists: str = "append",
) -> None:
    """
    Writes a pandas DataFrame to a PostgreSQL table with error handling.

    On failure, it logs the error and sends an email notification.

    Args:
        df: The pandas DataFrame to write.
        table_name: The name of the target database table.
        engine: The SQLAlchemy engine to use for the connection.
        schema: The database schema (e.g., 'public').
        if_exists: How to behave if the table exists
            ('append', 'replace', 'fail').
    """
    try:
        # Use a connection from the engine
        with engine.connect() as conn:
            df.to_sql(
                name=table_name,
                con=conn,  # <-- Pass the connection, not the engine
                schema=schema,
                if_exists=if_exists,
                index=False,
            )
    except Exception as e:
        logger.error(
            f"Database insert failed for {schema}.{table_name}: {e}", exc_info=True
        )
        # Send an email alert, importing from our new module
        send_error_email(e, f"Write to database {schema}.{table_name}")
        # Re-raise the exception to fail the calling task
        raise
