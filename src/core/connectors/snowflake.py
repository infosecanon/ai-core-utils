"""
Utilities for connecting to and interacting with Snowflake.
"""

import logging
from functools import lru_cache

from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@lru_cache
def create_snowflake_engine() -> Engine:
    """
    Creates and returns a SQLAlchemy engine for Snowflake.

    Pulls credentials from the global settings object.

    Returns:
        A SQLAlchemy Engine instance for Snowflake.
    """
    # This requires adding a 'SNOWFLAKE' model to config.py
    # e.g., settings.SNOWFLAKE.USER, etc.

    # try:
    #     engine = create_engine(
    #         f"snowflake://{settings.SNOWFLAKE.USER}:"
    #         f"{settings.SNOWFLAKE.PASSWORD.get_secret_value()}@"
    #         f"{settings.SNOWFLAKE.ACCOUNT}/"
    #         f"{settings.SNOWFLAKE.DATABASE}/"
    #         f"{settings.SNOWFLAKE.SCHEMA}?"
    #         f"warehouse={settings.SNOWFLAKE.WAREHOUSE}&role={settings.SNOWFLAKE.ROLE}"
    #     )
    #     logger.info(f"Snowflake engine created for {settings.SNOWFLAKE.ACCOUNT}")
    #     return engine
    # except Exception as e:
    #     logger.critical(f"Failed to create Snowflake engine: {e}")
    #     raise

    logger.warning("Snowflake connector not fully configured. Implement in config.py")
    raise NotImplementedError("Snowflake settings not found in config.py")
