.PHONY: help install install-dev test test-watch lint format type-check clean run run-dev docker-build docker-run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt

test: ## Run tests
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term -f

lint: ## Run linting
	flake8 app/ tests/
	black --check app/ tests/
	isort --check-only app/ tests/

format: ## Format code
	black app/ tests/
	isort app/ tests/

type-check: ## Run type checking
	mypy app/

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

run: ## Run production server
	uvicorn app.main:app --host 0.0.0.0 --port 8000

run-dev: ## Run development server with auto-reload
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker-build: ## Build Docker image
	docker build -t exlm-backend .

docker-run: ## Run Docker container
	docker run -p 8000:8000 exlm-backend

setup-db: ## Setup database (requires PostgreSQL)
	alembic upgrade head

create-migration: ## Create new migration
	alembic revision --autogenerate -m "$(message)"

check-all: format lint type-check test ## Run all checks 