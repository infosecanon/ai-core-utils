"""
This module provides a centralized function for setting up
logging for the application, based on the environment.
"""

import logging
import os
from datetime import datetime
from typing import Optional

# Import the settings singleton from our new config module
from .config import settings


def setup_logging(
    log_dir: str = "logs", log_level_str: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration for the application.

    This configures logging to write to both a timestamped log file
    and to the console (stdout). It automatically sets the log level
    based on the 'EDP_ENVIRONMENT' setting ('DEBUG' for Development,
    'INFO' otherwise).

    It also sets the logging level for noisy third-party libraries
    like 'urllib3' and 'sqlalchemy' to WARNING to reduce clutter.

    Args:
        log_dir: The directory to store log files.
        log_level_str: Optionally override the log level
                         (e.g., "DEBUG", "INFO", "WARNING").

    Returns:
        The root logger instance for the application.
    """
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            # Handle race condition or permission errors
            print(f"Warning: Could not create log directory {log_dir}. {e}")
            log_dir = "."  # Fall back to current directory

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"app_{timestamp}.log")

    # --- Determine Log Level ---
    if log_level_str:
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    elif settings.EDP_ENVIRONMENT.lower() == "development":
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # --- Configure Handlers ---
    # handlers = [logging.StreamHandler(sys.stdout)]  # Always log to stdout

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    handlers.append(logging.FileHandler(log_file))

    try:
        # Add file handler if permissions allow
        handlers.append(logging.FileHandler(log_file))
    except Exception as e:
        print(f"Warning: Could not create file handler {log_file}. {e}")

    # --- Apply Basic Configuration ---
    # We get the root logger and configure it
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    # --- Reduce Noise from 3rd-Party Libraries ---
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)

    # Get the root logger
    root_logger = logging.getLogger()

    # Log the startup
    root_logger.info(f"Logging initialized (Level: {logging.getLevelName(log_level)})")
    root_logger.info(f"Environment: {settings.EDP_ENVIRONMENT}")

    return root_logger
