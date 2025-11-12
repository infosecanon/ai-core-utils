# ai_utils_core

Core utilities for AI and Data Engineering projects.

This library provides a standardized, centralized, and tested set of tools to enforce team-wide coding principles. It handles common tasks such as configuration, logging, monitoring, and database connections.

## Core Features

* **Standardized Logging:** A single function (`setup_logging`) to configure structured logging for all services.
* **Secure Configuration:** Pydantic-based settings management that loads from `cfg.yml` and environment variables (for secrets).
* **Automated Monitoring:** A simple decorator (`@monitor_script`) that adds performance monitoring (CPU, RAM, time), error alerting, and database logging to any function.
* **Standard Connectors:** Centralized, pre-configured functions to create clients for Postgres, AWS, Azure, Snowflake, and more.

## Quick Start & Usage

Here is how to use the core library features in a new project.

### 1. Configuration

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

## Standard Logging
At the top of your script, call `setup_logging()` once. This will configure the root logger to output to both console and a log file, with log levels automatically set based on the `EDP_ENVIRONMENT` in your config.



## How to Use This in a Project:
At the top of any script (e.g., an Airflow task), add:

```python
import logging
from ai_utils_core.logging import setup_logging
from ai_utils_core.monitoring import monitor_script

# 1. Set up standard logging
setup_logging()

# 2. Add the decorator. That's it.
@monitor_script(main_function_name="MyETLProcess")
def run_etl():
    """Main ETL function."""
    logging.info("Starting ETL...")

    # ... do work ...

    logging.info("ETL finished.")

    # 3. The decorator looks for this string in the return value.
    return "Total Records Updated: 150"

if __name__ == "__main__":
    run_etl()
```

Another example:
```python
import logging
from ai_utils_core.logging import setup_logging

# This one line sets up all logging rules
setup_logging()

# Now, use the standard logging library anywhere in your app
logging.info("This is an info message.")
logging.debug("This will only show in 'Development' environment.")
logging.error("This is an error.")
```

## Function Monitoring & Alerting
For any main ETL function or long-running process, add the `@monitor_script` decorator. This automatically adds:
* Execution timing
* CPU and Memory profiling
* Automated email alerts on failure
* A summary log written to the Postgres `edp_monitoring` table


## Using Connectors
Access standardized, pre-configured clients and database engines.

```python
from ai_utils_core.connectors.postgres import create_postgres_engine
from ai_utils_core.connectors.aws import get_s3_client
from ai_utils_core.config import settings

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
│     ├─ airflow.py        # Standard Airflow DAG/Task helper classes
│     ├─ alerting.py       # send_error_email()
│     ├─ config.py         # Pydantic-based config & env var loading
│     ├─ logging.py        # setup_logging()
│     ├─ monitoring.py     # @monitor_script decorator and MonitorScript class
│     └─ connectors/
│        ├─ postgres.py     # create_postgres_engine(), DBLog, write_to_database()
│        ├─ aws.py          # get_boto3_session(), get_s3_client()
│        ├─ azure.py        # get_azure_credential(), get_blob_service_client()
│        ├─ salesforce.py   # get_salesforce_client()
│        ├─ snowflake.py    # create_snowflake_engine()
│        └─ sqlite.py       # create_sqlite_engine()
│
├─ tests/                  # Unit tests for all modules
│  ├─ test_config.py
│  ├─ test_logging.py
│  └─ connectors/
│     ├─ test_postgres.py
│     └─ ...
│
├─ .gitignore
├─ .pre-commit-config.yaml # Linter, formatter, secrets (CI/CD principle)
├─ CONTRIBUTING.md         # How to add to this library (Documentation)
├─ pyproject.toml          # Defines the package, dependencies (Reproducibility)
└─ README.md               # How to use the library (Documentation)
```

## Contributing
Contributions are welcome! Please see CONTRIBUTING.md for details on the development process, how to set up your environment, and how to submit pull requests.
