.DEFAULT_GOAL := help

# Enable uv in PATH (user may install to ~/.local/bin)
export PATH := $(HOME)/.local/bin:$(PATH)

CASE ?= case1

.PHONY: help
help:  ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install:  ## Install deps via uv
	uv sync

.PHONY: freeze
freeze:  ## Export requirements.txt for reviewers
	uv pip compile pyproject.toml -o requirements.txt

.PHONY: up
up:  ## Start Qdrant via docker-compose
	docker compose up -d qdrant

.PHONY: down
down:  ## Stop and remove containers
	docker compose down

.PHONY: logs
logs:  ## Tail Qdrant logs
	docker compose logs -f qdrant

.PHONY: ingest
ingest:  ## Ingest policy rules into Qdrant
	uv run python -m scripts.ingest_policy

.PHONY: demo
demo:  ## Run a single case through the triage pipeline (CASE=case1..case5)
	uv run python -m app.cli --case data/test_cases/$(CASE).json

.PHONY: eval
eval:  ## Run all test cases and generate eval report
	uv run python -m scripts.evaluate

.PHONY: ui
ui:  ## Launch Streamlit UI
	uv run streamlit run app/ui/app.py

.PHONY: test
test:  ## Run pytest
	uv run pytest -v

.PHONY: lint
lint:  ## Run ruff
	uv run ruff check app scripts tests

.PHONY: format
format:  ## Auto-format with ruff
	uv run ruff format app scripts tests

.PHONY: smoke
smoke:  ## Smoke-test API + Qdrant connectivity
	uv run python -m scripts.smoke_test

.PHONY: clean
clean:  ## Remove caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
