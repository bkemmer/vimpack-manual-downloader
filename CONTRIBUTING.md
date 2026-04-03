# Contributing

Thank you for your interest in contributing to `vimpack-manual-downloader`! Before you submit your code or Pull Requests, please set up your local development environment and make sure the tests pass.

## Development Setup

We use a `Makefile` to simplify common development tasks. 

To install the necessary development dependencies found in `requirements-dev.txt`, run the following command:

```bash
make install-dev-requirements
```

## Running Tests

Our tests are located in `tests/`. We use `pytest` for testing the main script functionalities.

Before committing your changes, please ensure that all tests run successfully by executing:

```bash
make test
```

## Linting and Code Formatting

We use `ruff` to keep the code clean and well-formatted. You can check for linting errors and format the codebase by running:

```bash
make lint
make format
```
