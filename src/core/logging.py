"""
This module provides a centralized function for setting up
logging for the application, based on the environment.

It features:
-   Configures the root logger.
-   Adds a colorful, formatted handler (`colorlog`) for console output (STDOUT).
-   Adds a standard, non-colored, timestamped file handler for persistent logs.
-   Sets log level based on 'EDP_ENVIRONMENT' setting (from config.py).
-   Suppresses overly "noisy" loggers from third-party libraries.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from colorlog import ColoredFormatter  # For colorful console output

# Import the settings singleton from our config module
from .config import settings


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    This is a simple wrapper around `logging.getLogger(name)` to ensure
    all modules get loggers from the same pre-configured hierarchy.

    Args:
        name (str): The name for the logger (usually `__name__` of the
            calling module).

    Returns:
        logging.Logger: A logger instance.
    """
    return logging.getLogger(name)


def setup_logging(
    script_name: str = "app",
    log_dir: Union[str, Path] = "logs/",
    log_level_override: Optional[str] = None,
) -> Path:
    """
    Set up the root logging configuration for the application.

    This function should be called once at the start of the main script.
    It configures two handlers:
    1.  A console handler (StreamHandler) with colored output.
    2.  A file handler (FileHandler) that logs to a timestamped file in
        the specified `log_dir`.

    Args:
        script_name (str, optional): The base name of the script being run
            (e.g., 'train', 'predict'). Used for naming the log file.
            Defaults to "app".
        log_dir (Union[str, Path], optional): The directory to save log
            files. Defaults to 'logs/'.
        log_level_override (Optional[str], optional): If provided,
            overrides the log level (e.g., "DEBUG", "INFO").

    Returns:
        Path: The `pathlib.Path` object pointing to the newly created log file.
    """

    # Determine Log Level
    # We now check for an override, then the environment setting, then default.
    if log_level_override:
        level = getattr(logging, log_level_override.upper(), logging.INFO)
    elif settings.EDP_ENVIRONMENT.lower() == "development":
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)  # Set the *lowest* level

    # Clear any existing handlers (e.g., from previous runs in a notebook)
    root_logger.handlers.clear()

    # CONSOLE HANDLER (with color)
    console_log_format = (
        "%(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s"
    )
    console_formatter = ColoredFormatter(
        console_log_format,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)  # Console level matches root
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # FILE HANDLER (without color)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create logs directory if it doesn't exist
    log_path_obj = Path(log_dir)
    try:
        log_path_obj.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        root_logger.warning(f"Could not create log directory {log_dir}. {e}. Using '.'")
        log_path_obj = Path(".")  # Fall back to current directory

    # Determine log file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{script_name}_{timestamp}.log"
    log_file_path = log_path_obj / log_filename

    # Create the file handler
    try:
        file_handler = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
        # The file log is *always* set to DEBUG to capture maximum detail
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        root_logger.warning(f"Could not create file handler {log_file_path}. {e}")

    # SUPPRESS NOISY LOGGERS
    all_noisy_loggers = ["sqlalchemy", "boto3", "botocore", "azure"]

    for logger_name in all_noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Log the successful setup
    root_logger.info(
        f"Logging initialized. Console level: {logging.getLevelName(level)}"
    )
    root_logger.info(f"Environment: {settings.EDP_ENVIRONMENT}")
    root_logger.info(f"Log file: {log_file_path}")

    return log_file_path
