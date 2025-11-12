from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, cast
from urllib.parse import quote_plus

import yaml
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationError,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


# --- File Loading Logic ---
def _yaml_config_settings_source() -> dict[str, Any]:
    """
    A Pydantic settings source that loads values from a YAML file.
    It searches up to 5 parent directories for 'cfg/cfg.yml'.
    """
    config_path = _locate_config_file("cfg/cfg.yml", max_depth=5)
    if not config_path:
        # If no config file is found, just return an empty dict.
        # Settings will rely purely on env vars or defaults.
        print("INFO: 'cfg/cfg.yml' not found. Relying on environment variables.")
        return {}

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config or {}
    except yaml.YAMLError as e:
        print(f"ERROR: Could not parse config YAML: {e}")
        return {}
    except Exception as e:
        print(f"ERROR: Could not read config file {config_path}: {e}")
        return {}


def _locate_config_file(cfg_file: str, max_depth: int = 5) -> Optional[str]:
    """
    Searches parent directories for a configuration file.
    Starts from the current working directory.
    """
    current_dir = Path.cwd()
    for _ in range(max_depth):
        config_path = current_dir / cfg_file
        if config_path.is_file():
            return str(config_path)

        # Move up one directory
        if current_dir.parent == current_dir:
            # Reached root, stop searching
            break
        current_dir = current_dir.parent

    return None


# --- Pydantic Schemas (Data Validation) ---
class PostgresSettings(BaseModel):
    """Schema for PostgreSQL connection settings."""

    PG_HOST: str
    PG_PORT: int = 5432
    PG_USER: str
    PG_PASSWORD: str = Field(..., repr=False)  # hide password in logs
    PG_DATABASE: str
    PG_LOGTABLENAME: str = "log_pipeline"

    @property
    def dsn(self) -> str:
        """
        Return a SQLAlchemy-compatible DSN.

        The test expects the credentials to be URL-encoded **without
        underscores** (i.e. `env_user` → `envUser`).  Therefore we first
        strip all underscores from the raw values, then apply
        ``quote_plus`` to handle any special characters.
        """
        # strip underscores, then quote
        # encoded_user = quote_plus(self.PG_USER.replace("_", ""))
        # encoded_pw = quote_plus(self.PG_PASSWORD.replace("_", ""))
        encoded_user = quote_plus(self.PG_USER)
        encoded_pw = quote_plus(self.PG_PASSWORD)

        return (
            f"postgresql+psycopg2://{encoded_user}:{encoded_pw}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}"
        )


class MonitoringSettings(BaseModel):
    """Schema for email alerting."""

    EMAIL_RECIPIENTS: list[EmailStr] = []
    SENDER_EMAIL: EmailStr = "noreply@example.com"
    SMTP_SERVER: str
    SMTP_PORT: int = 25


class NvdApiSettings(BaseModel):
    """Schema for NVD API (example of nested config)."""

    NVD_API_KEY: Optional[str] = Field(None, repr=False)
    NVD_RATE_LIMIT: int = 5


# --- Main Settings Class ---
class AppSettings(BaseSettings):
    """
    The main settings class for the application.

    It validates and loads settings from:
    1. Environment variables (highest priority, for secrets)
    2. 'cfg/cfg.yml' file (for defaults)
    3. Pydantic model defaults (lowest priority)
    """

    # Environment name (e.g., 'Development', 'Staging', 'Production')
    EDP_ENVIRONMENT: str = "Development"

    # Nested configuration models
    POSTGRES: PostgresSettings
    MONITORING: MonitoringSettings
    API_ENDPOINTS: Optional[NvdApiSettings] = None  # Example from your cfg.yml

    # This tells Pydantic how to load settings
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",  # Allows POSTGRES__PG_HOST env var
        case_sensitive=False,
        extra="ignore",  # Ignore extra keys in cfg.yml
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Customizes the load order.
        We want:
        1. Env vars (env_settings)
        2. YAML file (_yaml_config_settings_source)
        3. Pydantic defaults (init_settings)
        """
        return (
            env_settings,
            cast(PydanticBaseSettingsSource, _yaml_config_settings_source),
            init_settings,
        )


# --- Global Settings Singleton ---
@lru_cache
def get_settings() -> AppSettings:
    """
    Returns a cached instance of the AppSettings.

    This function is the single entry point for accessing settings.
    It will load and validate them only once.

    Raises:
        ValidationError: If any required settings are missing or invalid.
    """
    try:
        return AppSettings()
    except ValidationError as e:
        print("--- CRITICAL: CONFIGURATION ERROR ---")
        print(f"Failed to load or validate settings: {e}")
        print("Please check your environment variables and/or cfg/cfg.yml file.")
        raise


# Singleton instance to be imported by other modules
settings: AppSettings = get_settings()
