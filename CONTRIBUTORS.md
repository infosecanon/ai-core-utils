# Contributing to ai_utils_core

Thank you for contributing to our core library! This document outlines the process for local development, testing, and submitting changes.

## Local Development Setup

1.  **Clone the repository:**
    ```bash
    git clone <REPO_URL>
    cd ai_utils_core
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the library in editable mode with dev dependencies:**
    This command installs all packages from `pyproject.toml`'s `[dependencies]` and `[dev]` sections.
    ```bash
    pip install -e ".[dev]"
    ```

4.  **Install pre-commit hooks:**
    This will automatically run the linter (`ruff`), formatter (`ruff format`), and type checker (`mypy`) before each commit.
    ```bash
    pre-commit install
    ```

Your environment is now set up.

## Running Tests

This project uses `pytest` for unit testing. All new code **must** be accompanied by unit tests.

* **Mocking:** All external services (databases, APIs, SMTP servers) **must** be mocked using `pytest.monkeypatch` or `unittest.mock`. Tests should *never* make live network calls.
* **Location:** Tests for `src/ai_utils_core/module.py` should be in `tests/test_module.py`.

**To run all tests:**
```bash
pytest
```

To run tests with coverage: This will show which lines of code are not covered by tests. We aim for high coverage on all new functionality.

```bash
pytest --cov=src/ai_utils_core
```

## Code Style & Linting
We enforce a strict code style to maintain consistency. This is handled automatically by pre-commit, but you can run the checks manually.
* Linter & Formatter: `ruff`
* Type Checking: `mypy`

To run all checks manually:
```bash
pre-commit run -a
```

To just format the code:

```bash
ruff format .
```

## Submitting a Pull Request
1. Create a new feature branch from main:
```bash
git checkout main
git pull
git checkout -b feature/my-new-connector
```

2. Write your code and add unit tests for your new functionality.
Ensure all tests pass:
```bash
pytest
```

3. Commit your changes. The pre-commit hooks will run automatically.
```bash
git add .
git commit -m "feat: Add new redis connector"
```

4. Push your branch to the remote:
```bash
git push -u origin feature/my-new-connector
```

5. Open a Pull Request against the main branch
* In the PR description, explain what the change does and link to any relevant issues.
* Request a review. The PR requires at least one approval to be merged.
