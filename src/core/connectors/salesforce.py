"""
Utilities for connecting to the Salesforce API.

This module will use simple-salesforce and pull credentials
from the global settings object.
"""

import logging
from functools import lru_cache

from simple_salesforce import Salesforce

logger = logging.getLogger(__name__)


@lru_cache
def get_salesforce_client() -> Salesforce:
    """
    Creates and returns a simple-salesforce client instance.

    Pulls credentials (username, password, security token, domain)
    from the global settings object.

    Returns:
        A simple_salesforce.Salesforce client.
    """
    # This requires adding a 'SALESFORCE' model to config.py
    # e.g., settings.SALESFORCE.USERNAME, etc.

    # try:
    #     sf_client = Salesforce(
    #         username=settings.SALESFORCE.USERNAME,
    #         password=settings.SALESFORCE.PASSWORD.get_secret_value(),
    #         security_token=settings.SALESFORCE.TOKEN.get_secret_value(),
    #         domain=settings.SALESFORCE.DOMAIN
    #     )
    #     logger.info("Salesforce client created successfully.")
    #     return sf_client
    # except Exception as e:
    #     logger.critical(f"Failed to create Salesforce client: {e}")
    #     raise

    logger.warning("Salesforce connector not fully configured. Implement in config.py")
    raise NotImplementedError("Salesforce settings not found in config.py")
