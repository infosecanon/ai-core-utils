# ai_core_utils

Core utilities for AI and Data Engineering projects.

This library provides a standardized, centralized, and tested set of tools to enforce team-wide coding principles. It handles common tasks such as configuration, logging, monitoring, and database connections.

## Core Features

* **Standardized Logging:** A single function (`setup_logging`) to configure structured logging for all services.
* **Colorful Console Logs**: Enhanced logging with colorlog for easy-to-read, color-coded console output.
* **Dynamic UML Tracing**: A `@global_tracer.trace` decorator that generates PlantUML sequence diagrams of your code's execution path.
* **Secure Configuration:** Pydantic-based settings management that loads from `cfg.yml` and environment variables (for secrets).
* **Automated Monitoring:** A simple decorator (`@monitor_script`) that adds performance monitoring (CPU, RAM, time), error alerting, and database logging to any function.
* **Standard Connectors:** Centralized, pre-configured functions to create clients for Postgres, AWS, Azure, Snowflake, etc.

## Quick Start & Usage

Here is how to use the core library features in a new project.

### Configuration

The library is configured by a `cfg/cfg.yml` file placed in the project's root directory. It is automatically validated against the library's `Pydantic` schemas.

**Important:** For **Secrets Management**, all sensitive values (like `PG_PASSWORD`) **must** be set as **environment variables**. Environment variables always override the `.yml` file.

**Example `cfg/cfg.yml` (for local development):**
```yaml
EDP_ENVIRONMENT: 'Development'

POSTGRES:
  PG_HOST: 'localhost'
  PG_PORT: 5432
  PG_USER: 'postgres'
  PG_DATABASE: 'reveal'
  PG_LOGTABLENAME: 'log_pipeline'
  # PG_PASSWORD is set as an environment variable!
  # export POSTGRES__PG_PASSWORD='my_secret_password'

MONITORING:
  EMAIL_RECIPIENTS: [test@test.com]
  SENDER_EMAIL: test@test.com
  SMTP_SERVER: test.test.net
  SMTP_PORT: 25
```

### Standard Logging
At the top of your script, call `setup_logging()` once. This will configure the root logger to output to both console and a log file, with log levels automatically set based on the `EDP_ENVIRONMENT` in your config.

```python
import logging
from src.core.logging import setup_logging

# This one line sets up all logging rules
# It reads 'EDP_ENVIRONMENT' from your config
setup_logging(script_name="my_app")

# Now, use the standard logging library anywhere in your app
logger = logging.getLogger(__name__)

logger.info("This is an info message (green).")
logger.debug("This will only show in 'Development' environment (cyan).")
logger.warning("This is a warning (yellow).")
logger.error("This is an error (red).")
```

### Function Monitoring & Alerting
For any main ETL function or long-running process, add the `@monitor_script` decorator. This automatically adds:
* Execution timing
* CPU and Memory profiling
* Automated email alerts on failure
* A summary log written to the Postgres `log_pipeline` table

```python
import logging
from src.core.logging import setup_logging
from src.core.monitoring import monitor_script

# 1. Set up standard logging
setup_logging(script_name="my_etl")
logger = logging.getLogger(__name__)

# 2. Add the decorator. That's it.
@monitor_script(main_function_name="MyETLProcess")
def run_etl():
    """Main ETL function."""
    logger.info("Starting ETL...")
    # ... do work ...
    logger.info("ETL finished.")

if __name__ == "__main__":
    run_etl()
```

### Dynamic UML Tracing
You can trace any function's execution path by adding the @global_tracer.trace decorator. This is useful for visualizing complex data flows.

A finally block in your main script can then render the trace to a PNG.

```python
# In main.py
import logging
from pathlib import Path

# --- 1. Import all your new tools ---
from src.core.logging import setup_logging
from src.core.plantuml_tracer import global_tracer
from src.core.diagram_renderer import render_plantuml_to_png

# --- 2. Import your project's decorated functions ---
# from my_project.data_loader import load_data, clean_data
# (Make sure they have @global_tracer.trace)

# --- 3. Call setup_logging() FIRST ---
setup_logging(script_name="main_run")
logger = logging.getLogger(__name__)

# --- 4. Define and decorate functions ---
@global_tracer.trace
def load_data(file_path: str):
    logger.info(f"Loading data from {file_path}")
    return "raw_data"

@global_tracer.trace
def clean_data(data: str):
    logger.info(f"Cleaning {data}")
    return "cleaned_data"

def main():
    logger.info("Starting the main process...")
    # The decorator will automatically log these calls
    raw_data = load_data("my_file.csv")
    cleaned_data = clean_data(raw_data)
    logger.info("Main process finished.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Process failed: {e}", exc_info=True)
    finally:
        # --- 5. Generate the diagram at the very end ---
        logger.info("Generating trace diagram...")
        output_path = Path("reports/process_trace")
        puml_content = global_tracer.get_diagram()

        # This creates 'reports/process_trace.png'
        render_plantuml_to_png(puml_content, output_path)
```


### Using Connectors
Access standardized, pre-configured clients and database engines.
```python
from src.core.connectors.postgres import create_postgres_engine
from src.core.connectors.aws import get_s3_client
from src.core.config import settings

# Get the standard SQLAlchemy engine
# It's cached, so multiple calls are fast and efficient
pg_engine = create_postgres_engine()

# Get a pre-configured Boto3 client
s3 = get_s3_client()

# You can also access validated config settings directly
print(f"Connecting to Postgres host: {settings.POSTGRES.PG_HOST}")
```


## Directory Overview
```
ai_utils_core/
├─ cfg/
│  └─ cfg.yml
├─ src/
│  └─ core/
│     ├─ airflow.py            # Standard Airflow DAG/Task helper classes
│     ├─ alerting.py           # send_error_email()
│     ├─ config.py             # Pydantic-based config & env var loading
│     ├─ logging.py            # setup_logging() with colorlog
│     ├─ monitoring.py         # @monitor_script decorator
│     ├─ diagram_renderer.py   # Renders PlantUML diagrams
│     ├─ plantuml_tracer.py    # @global_tracer decorator
│     ├─ plantuml-1.2025.10.jar  # PlantUML rendering engine
│     └─ connectors/
│        ├─ postgres.py         # create_postgres_engine()
│        ├─ aws.py              # get_boto3_session()
│        ├─ azure.py            # get_azure_credential()
│        ├─ salesforce.py       # get_salesforce_client()
│        ├─ snowflake.py        # create_snowflake_engine()
│        └─ sqlite.py           # create_sqlite_engine()
│
├─ tests/                      # Unit tests for all modules
│  ├─ __init__.py             # Makes 'tests' a package
│  ├─ test_config.py
│  └─ ...
│
├─ reports/
│  └─ (UML diagrams are saved here)
│
├─ main.py                   # Test script for new features
├─ .gitignore
├─ .pre-commit-config.yaml   # Linter, formatter, secrets
├─ CONTRIBUTING.md           # How to add to this library
├─ pyproject.toml            # Defines the package, dependencies
└─ README.md                 # How to use the library
```

## Contributing
Contributions are welcome! Please see CONTRIBUTING.md for details on the development process, how to set up your environment, and how to submit pull requests.
