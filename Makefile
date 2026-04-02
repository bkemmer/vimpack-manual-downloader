.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  %-25s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

test: ## Run tests using pytest
	python3 -m pytest tests/

lint: ## Run linting using ruff
	python3 -m ruff check

format: ## Format code using ruff
	python3 -m ruff format

install-dev-requirements: ## Install development requirements
	python3 -m pip install -r requirements-dev.txt
