"""
Utilities for interacting with AWS services (e.g., S3, Secrets Manager).
"""

import logging
from functools import lru_cache

import boto3
from botocore.client import BaseClient

logger = logging.getLogger(__name__)


@lru_cache
def get_boto3_session() -> boto3.Session:
    """
    Creates and returns a Boto3 Session.

    It can be configured to use a specific region or role
    from the global settings.

    Returns:
        A boto3.Session instance.
    """
    # This requires adding an 'AWS' model to config.py
    # e.g., settings.AWS.REGION

    # try:
    #     session = boto3.Session(
    #         region_name=settings.AWS.REGION
    #     )
    #     logger.info(f"Boto3 session created for region {settings.AWS.REGION}")
    #     return session
    # except Exception as e:
    #     logger.critical(f"Failed to create Boto3 session: {e}")
    #     raise

    logger.warning("AWS connector not fully configured. Implement in config.py")
    raise NotImplementedError("AWS settings not found in config.py")


def get_s3_client() -> BaseClient:
    """Helper function to get an S3 client."""
    session = get_boto3_session()
    return session.client("s3")


def get_secretsmanager_client() -> BaseClient:
    """Helper function to get a Secrets Manager client."""
    session = get_boto3_session()
    return session.client("secretsmanager")
