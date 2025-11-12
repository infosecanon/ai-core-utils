"""
Utilities for interacting with Azure services
(e.g., Blob Storage, Key Vault).
"""

import logging
from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


@lru_cache
def get_azure_credential() -> DefaultAzureCredential:
    """
    Returns a DefaultAzureCredential instance.
    This will use env vars, managed identity, etc.
    """
    return DefaultAzureCredential()


def get_blob_service_client() -> BlobServiceClient:
    """
    Returns an Azure Blob Storage client.

    Requires AZURE_STORAGE_ACCOUNT_URL in settings/env.
    """
    # This requires adding an 'AZURE' model to config.py
    # e.g., settings.AZURE.STORAGE_ACCOUNT_URL

    # try:
    #     account_url = settings.AZURE.STORAGE_ACCOUNT_URL
    #     credential = get_azure_credential()
    #     client = BlobServiceClient(account_url=account_url, credential=credential)
    #     logger.info(f"BlobServiceClient created for {account_url}")
    #     return client
    # except Exception as e:
    #     logger.critical(f"Failed to create BlobServiceClient: {e}")
    #     raise

    logger.warning("Azure connector not fully configured. Implement in config.py")
    raise NotImplementedError("Azure settings not found in config.py")


def get_key_vault_client() -> SecretClient:
    """
    Returns an Azure Key Vault client.

    Requires AZURE_KEY_VAULT_URL in settings/env.
    """
    # This requires adding an 'AZURE' model to config.py
    # e.g., settings.AZURE.KEY_VAULT_URL

    # try:
    #     vault_url = settings.AZURE.KEY_VAULT_URL
    #     credential = get_azure_credential()
    #     client = SecretClient(vault_url=vault_url, credential=credential)
    #     logger.info(f"SecretClient created for {vault_url}")
    #     return client
    # except Exception as e:
    #     logger.critical(f"Failed to create SecretClient: {e}")
    #     raise

    logger.warning("Azure connector not fully configured. Implement in config.py")
    raise NotImplementedError("Azure settings not found in config.py")
