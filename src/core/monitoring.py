"""
Provides a decorator and context manager for monitoring
script execution time, resource usage, and status.

Ties together the config, alerting, and database connector modules.
"""

import datetime
import logging
import re
import threading
import time
import traceback
from functools import wraps
from types import TracebackType
from typing import Any, Callable, Literal, Optional, ParamSpec, TypeVar

import pandas as pd
import psutil
from typing_extensions import Self

from core.alerting import send_error_email

# Import from library modules
from core.config import settings
from core.connectors.postgres import create_postgres_engine

# Create a ParamSpec to capture the arguments
P = ParamSpec("P")

# Create a TypeVar to capture the return type
R = TypeVar("R")

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# Regex to find "Total Records Updated: 123" in a return string
_RECORDS_REGEX = re.compile(r"Total\s+Records\sUpdated:\s*(\d+)", re.IGNORECASE)


def _extract_records_updated_from_text(text: Any) -> int:
    """
    Parses a string to find 'Total Records Updated: 123'.
    Returns 0 if not found or input is not a string.
    """
    if not isinstance(text, str):
        return 0
    m = _RECORDS_REGEX.search(text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 0
    return 0


class MonitorScript:
    """
    A context manager to monitor the execution time,
    resource usage (CPU, memory), and status of a block of code.
    """

    def __init__(self, main_function_name: str):
        self.main_function_name = main_function_name
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.execution_datetime: Optional[datetime.datetime] = None
        self.cpu_samples: list[float] = []
        self.mem_samples: list[float] = []
        self.status: str = "Success"
        self.error_message: Optional[str] = None
        self._running: bool = False
        self._sampling_thread: Optional[threading.Thread] = None
        self._process = psutil.Process()

    def __enter__(self) -> Self:
        """Starts the monitoring process."""
        self.start_time = time.time()
        self.execution_datetime = datetime.datetime.now()
        self._running = True
        self._sampling_thread = threading.Thread(target=self._sample_resources)
        self._sampling_thread.start()
        logger.info(f"Monitoring started for '{self.main_function_name}'")
        return self

    def _sample_resources(self) -> None:
        """Internal method run by the background thread to sample resources."""
        while self._running:
            try:
                # Get CPU percent (non-blocking)
                self.cpu_samples.append(self._process.cpu_percent(interval=None))
                # Get Resident Set Size (RSS) memory in Megabytes (MB)
                self.mem_samples.append(self._process.memory_info().rss / (1024 * 1024))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._running = False  # Stop sampling if process is gone

            # Sleep to avoid busy-waiting
            time.sleep(0.5)  # Sample every 500ms

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> Literal[False]:
        """Stops the monitoring process."""
        # Signal the sampling thread to stop
        self._running = False
        self.end_time = time.time()

        if self._sampling_thread:
            self._sampling_thread.join()

        if exc_type:
            self.status = "Fail"
            self.error_message = "".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            )
            logger.error(
                f"Monitoring recorded FAILED execution for '{self.main_function_name}'"
            )
        else:
            logger.info(
                f"Monitoring recorded SUCCESSFUL execution for "
                f"'{self.main_function_name}'"
            )

        # Return False to propagate exceptions (if any)
        return False

    def get_summary_df(self) -> pd.DataFrame:
        """Calculates monitoring statistics and returns a DataFrame."""
        if not self.cpu_samples:
            avg_cpu = peak_cpu = 0.0
        else:
            # First sample is often 0.0, so we average non-zero
            valid_cpu = [s for s in self.cpu_samples if s > 0.0]
            avg_cpu = sum(valid_cpu) / len(valid_cpu) if valid_cpu else 0.0
            peak_cpu = max(self.cpu_samples)

        if not self.mem_samples:
            avg_mem = peak_mem = 0.0
        else:
            avg_mem = sum(self.mem_samples) / len(self.mem_samples)
            peak_mem = max(self.mem_samples)

        duration = self.end_time - self.start_time
        exec_dt = self.execution_datetime or datetime.datetime.now()

        monitoring_data = {
            "execution_datetime": [exec_dt.strftime("%Y-%m-%d %H:%M:%S")],
            "main_function": [self.main_function_name],
            "status": [self.status],
            "error_message": [self.error_message or ""],
            "execution_time_sec": [round(duration, 2)],
            "avg_cpu_percentage": [round(avg_cpu, 2)],
            "peak_cpu_percentage": [round(peak_cpu, 2)],
            "avg_mem_mb": [round(avg_mem, 2)],
            "peak_mem_mb": [round(peak_mem, 2)],
        }
        return pd.DataFrame(monitoring_data)


def monitor_script(
    main_function_name: str,
    monitoring_schema: str = "public",
    monitoring_table: str = "edp_monitoring",
) -> Callable[..., Any]:
    """
    A decorator factory for monitoring a function's execution.

    This decorator wraps a function to:
    1. Monitor its execution time, CPU, and memory using `MonitorScript`.
    2. Send an email alert if the function raises an exception.
    3. Write the monitoring summary to a database.
    4. Extract the 'records_updated' count from the function's return value.

    Args:
        main_function_name: The name to log for this monitored function.
        monitoring_schema: The schema for the monitoring summary table.
        monitoring_table: The name of the monitoring summary table.

    Returns:
        A decorator.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            monitor: Optional[MonitorScript] = None
            result: Any = None
            try:
                with MonitorScript(main_function_name=main_function_name) as m:
                    monitor = m
                    result = func(*args, **kwargs)

            except Exception as e:
                # If __exit__ ran, monitor object exists.
                # Send email alert using our new module
                send_error_email(e, main_function_name)
                # Re-raise the exception to stop execution
                raise

            finally:
                if monitor:
                    summary_row = monitor.get_summary_df()

                    # Try to parse records_updated from result
                    summary_row["records_updated"] = _extract_records_updated_from_text(
                        result
                    )

                    # --- 2. ADD THIS IF/ELSE BLOCK ---
                    # Check the DB_TYPE from settings *before* trying to write
                    if settings.POSTGRES.DB_TYPE == "postgresql":
                        try:
                            # Use our new, standardized connectors
                            engine = create_postgres_engine()
                            # Assuming this is a local alias for write_to_database
                            write_monitoring_db(
                                summary_row,
                                monitoring_table,
                                engine,
                                monitoring_schema,
                                "append",
                            )
                        except Exception as db_e:
                            # If logging to DB fails, print and send email
                            logger.critical(
                                f"CRITICAL: Failed to write monitoring data "
                                f"for {main_function_name}. Error: {db_e}",
                                exc_info=True,
                            )
                            send_error_email(
                                db_e,
                                f"MONITORING_DB_WRITE_FAILURE ({main_function_name})",
                            )
                    else:
                        # If not postgres, just log to console and skip DB write
                        logger.info(
                            f"Skipping Postgres monitoring log\n \
                            (DB_TYPE is '{settings.POSTGRES.DB_TYPE}')."
                        )
                    # --- END OF FIX ---

            return result

        return wrapper

    return decorator


# Need to rename this function to match what the decorator is calling
def write_monitoring_db(
    df: pd.DataFrame,
    table_name: str,
    engine: Any,  # Use Engine when imported
    schema: str,
    if_exists: str,
) -> None:
    """Helper function to write monitoring df"""
    # Use a connection from the engine
    try:
        with engine.connect() as conn:
            df.to_sql(
                name=table_name,
                con=conn,
                schema=schema,
                if_exists=if_exists,
                index=False,
            )
    except Exception as e:
        logger.error(f"Database insert failed for {schema}.{table_name}: {e}")
        # Send an email alert. No need to pass config!
        send_error_email(e, f"Write to database {schema}.{table_name}")
        # Re-raise the exception to fail the calling task
        raise
