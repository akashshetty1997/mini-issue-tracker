.DEFAULT_GOAL := help
COMPOSE := docker compose
API_TEST := $(COMPOSE) --profile test run --rm --build api-test

.PHONY: help up down logs test lint

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

up: ## Build and start the full stack in the background
	$(COMPOSE) up --build -d

down: ## Stop the stack (data is kept in the pgdata volume)
	$(COMPOSE) down

logs: ## Follow logs from all services
	$(COMPOSE) logs -f

test: ## Run the backend test suite inside the dev image
	$(API_TEST) pytest

lint: ## Run ruff and mypy on the backend
	$(API_TEST) sh -c "ruff check . && ruff format --check . && mypy app"
