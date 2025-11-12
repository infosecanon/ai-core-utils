"""
Utilities for connecting to and interacting with a SQLite database.
"""

import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@lru_cache
def create_sqlite_engine(db_path: str = "app.db") -> Engine:
    """
    Creates and returns a SQLAlchemy engine for a SQLite database.

    Args:
        db_path: The file path to the SQLite database.

    Returns:
        A SQLAlchemy Engine instance.
    """
    try:
        db_path_obj = Path(db_path)
        # Ensure the parent directory exists
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(f"sqlite:///{db_path}")
        logger.info(f"SQLite engine created for {db_path}")
        return engine
    except Exception as e:
        logger.critical(f"Failed to create SQLite engine: {e}", exc_info=True)
        raise
