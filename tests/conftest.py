import importlib
from typing import Any

import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from core import alerting, logging, monitoring
from core import config as config_module
from core.connectors import postgres


@pytest.fixture
def reload_settings(monkeypatch: MonkeyPatch) -> Any:
    """
    Fixture to force a reload of the config module and
    all dependent modules *after* setting new env vars.
    """

    def _set_env_and_reload(vars_dict: dict[str, str]) -> None:
        """
        Helper function that sets env vars and triggers the reload.
        This is what the test function will call.
        """
        # Set the new env vars
        for k, v in vars_dict.items():
            if v == "":
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)

        # NOW, clear caches
        config_module.get_settings.cache_clear()
        if hasattr(postgres, "create_postgres_engine"):
            postgres.create_postgres_engine.cache_clear()

        # Reload all modules
        try:
            importlib.reload(config_module)
            importlib.reload(alerting)
            importlib.reload(logging)
            importlib.reload(postgres)
            importlib.reload(monitoring)
        except ValidationError:
            raise  # Re-raise it for the test
        except Exception as e:
            print(f"Reloading failed: {e}")
            pass

    # Yield the helper function
    yield _set_env_and_reload

    # --- Teardown (after test) ---
    config_module.get_settings.cache_clear()

    if hasattr(postgres, "create_postgres_engine"):
        postgres.create_postgres_engine.cache_clear()

    try:
        importlib.reload(config_module)
        importlib.reload(alerting)
        importlib.reload(logging)
        importlib.reload(postgres)
        importlib.reload(monitoring)
    except ValidationError:
        pass  # We don't care about validation errors on cleanup
    except Exception:
        pass
