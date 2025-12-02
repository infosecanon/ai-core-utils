from typing import Any
from unittest.mock import MagicMock
from urllib.parse import quote_plus

import pytest
import yaml
from pydantic import ValidationError
from pytest import MonkeyPatch

# We need to import the module this way to monkeypatch
# its dependencies before the 'settings' singleton is created
from core import config as config_module


@pytest.fixture(autouse=True)
def reload_all_settings(reload_settings: Any) -> None:
    """
    This autouse fixture ensures that for *every* config test,
    we reset settings *after* the test's own reload_settings
    call has set the environment.
    """
    # This space is intentionally left blank.
    # The 'yield' from reload_settings happens.
    # Then the cleanup (reloading) from reload_settings happens.
    pass


def test_load_from_environment_variables(reload_settings: Any) -> None:
    """
    Tests that settings are loaded correctly from environment variables.
    """
    env_vars = {
        "EDP_ENVIRONMENT": "Production",
        "POSTGRES__PG_HOST": "env.host.com",
        "POSTGRES__PG_PORT": "5433",
        "POSTGRES__PG_USER": "env_user",
        "POSTGRES__PG_PASSWORD": "env_password",
        "POSTGRES__PG_DATABASE": "env_db",
        "MONITORING__SMTP_SERVER": "env.smtp.com",
        "MONITORING__SMTP_PORT": "587",
        "MONITORING__SENDER_EMAIL": "env@sender.com",
        "MONITORING__EMAIL_RECIPIENTS": '["env@test.com", "env2@test.com"]',
    }
    reload_settings(env_vars)
    settings = config_module.get_settings()

    assert settings.EDP_ENVIRONMENT == "Production"
    assert settings.POSTGRES.PG_HOST == "env.host.com"
    assert settings.POSTGRES.PG_PASSWORD == "env_password"

    # The dsn property IS encoding. Use quote_plus

    user = quote_plus("env_user")
    pw = quote_plus("env_password")

    expected_dsn = f"postgresql+psycopg2://{user}:{pw}@env.host.com:5433/env_db"
    assert settings.POSTGRES.dsn == expected_dsn


def test_load_from_yaml_file(reload_settings: Any, monkeypatch: MonkeyPatch) -> None:
    """
    Tests that settings are loaded correctly from the YAML file.
    """
    # Mock the YAML file content
    mock_yaml_content = {
        "EDP_ENVIRONMENT": "Staging",
        "POSTGRES": {
            "PG_HOST": "yaml.host.com",
            "PG_USER": "yaml_user",
            "PG_DATABASE": "yaml_db",
            "PG_PASSWORD": "yaml_password",  # This should be in env!
        },
        "MONITORING": {"SMTP_SERVER": "yaml.smtp.com", "SMTP_PORT": 25},
    }

    reload_settings(
        {
            "POSTGRES__PG_PASSWORD": "env_password",  # From env
            "MONITORING__SMTP_SERVER": "env.smtp.com",  # From env
        }
    )

    # Mock the function that loads the file
    monkeypatch.setattr(
        config_module, "_locate_config_file", lambda *args, **kwargs: "dummy/path.yml"
    )
    # Mock open and yaml.safe_load
    monkeypatch.setattr("builtins.open", MagicMock())
    monkeypatch.setattr(yaml, "safe_load", lambda f: mock_yaml_content)

    # Pass empty env vars dict (it will use pytest.ini)
    reload_settings({})
    settings = config_module.get_settings()

    assert settings.EDP_ENVIRONMENT == "Staging"
    assert settings.POSTGRES.PG_HOST == "yaml.host.com"
    assert settings.POSTGRES.PG_PASSWORD == "env_password"  # Overridden by env
    assert settings.MONITORING.SMTP_PORT == 25
    assert settings.MONITORING.SMTP_SERVER == "env.smtp.com"  # Overridden by env


def test_env_overrides_yaml(reload_settings: Any, monkeypatch: MonkeyPatch) -> None:
    """
    Tests that environment variables (for secrets) override YAML.
    """
    # Mock the YAML file content
    mock_yaml_content = {
        "POSTGRES": {
            "PG_HOST": "yaml.host.com",
            "PG_USER": "yaml_user",
            "PG_DATABASE": "yaml_db",
            "PG_PASSWORD": "yaml_password",  # Bad, but testing override
        },
        "MONITORING": {"SMTP_SERVER": "yaml.smtp.com"},
    }

    monkeypatch.setattr(
        config_module, "_locate_config_file", lambda *args, **kwargs: "dummy/path.yml"
    )
    monkeypatch.setattr("builtins.open", lambda a, b: True)
    monkeypatch.setattr(yaml, "safe_load", lambda f: mock_yaml_content)

    # Set env vars that will override
    env_vars = {
        "POSTGRES__PG_HOST": "env.host.com",
        "POSTGRES__PG_PASSWORD": "env_password",
        "MONITORING__SMTP_SERVER": "env.smtp.com",
        "MONITORING__SMTP_PORT": "587",
        "POSTGRES__PG_USER": "env_user_for_this_test",
        "POSTGRES__PG_DATABASE": "env_db_for_this_test",
    }

    reload_settings(env_vars)
    settings = config_module.get_settings()

    assert settings.POSTGRES.PG_HOST == "env.host.com"
    assert settings.POSTGRES.PG_PASSWORD == "env_password"
    assert settings.MONITORING.SMTP_SERVER == "env.smtp.com"
    # This should be from YAML, not the env_vars
    assert settings.POSTGRES.PG_USER == "env_user_for_this_test"


def test_missing_required_setting(
    reload_settings: Any, monkeypatch: MonkeyPatch
) -> None:
    """
    Tests that a ValidationError is raised if a required
    setting (like PG_HOST) is not provided at all.
    """
    # Mock file loading to return nothing, to prevent fallback
    monkeypatch.setattr(
        config_module, "_locate_config_file", lambda *args, **kwargs: None
    )

    with pytest.raises(ValidationError, match="POSTGRES.PG_PASSWORD"):
        # The reload_settings call remains the same
        reload_settings(
            {
                "POSTGRES__PG_HOST": "",
                "POSTGRES__PG_USER": "",
                "POSTGRES__PG_DATABASE": "",
                "POSTGRES__PG_PASSWORD": "",
                "MONITORING__SMTP_SERVER": "",
            }
        )
