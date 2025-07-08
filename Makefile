.PHONY: help install install-dev test test-watch lint format clean run run-dev docker-up docker-down docker-logs setup check-all install-gpu build-dev build-gpu up-dev up-gpu down clean test-dev test-gpu logs restart-backend restart-frontend restart-celery status status-gpu shell-backend shell-frontend shell-backend-gpu shell-frontend-gpu

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd backend && make install
	@echo "Installing frontend dependencies..."
	cd frontend && make install

install-dev: ## Install development dependencies
	@echo "Installing backend development dependencies..."
	cd backend && make install-dev
	@echo "Installing frontend dependencies..."
	cd frontend && make install

install-gpu: ## Install GPU dependencies
	@echo "Installing GPU dependencies..."
	cd backend && pip install -r requirements-gpu.txt
	cd frontend && npm install

test: ## Run all tests
	@echo "Running backend tests..."
	cd backend && make test
	@echo "Running frontend tests..."
	cd frontend && make test

test-watch: ## Run tests in watch mode
	@echo "Running backend tests in watch mode..."
	cd backend && make test-watch

lint: ## Run linting for all components
	@echo "Linting backend..."
	cd backend && make lint
	@echo "Linting frontend..."
	cd frontend && make lint

format: ## Format code for all components
	@echo "Formatting backend..."
	cd backend && make format
	@echo "Formatting frontend..."
	cd frontend && make format

clean: ## Clean all generated files
	@echo "Cleaning backend..."
	cd backend && make clean
	@echo "Cleaning frontend..."
	cd frontend && make clean

run: ## Run production servers
	@echo "Starting backend server..."
	cd backend && make run &
	@echo "Starting frontend server..."
	cd frontend && make start

run-dev: ## Run development servers
	@echo "Starting backend development server..."
	cd backend && make run-dev &
	@echo "Starting frontend development server..."
	cd frontend && make dev

docker-up: ## Start all services with Docker Compose
	docker-compose -f docker-compose.dev.yml up -d

docker-down: ## Stop all Docker services
	docker-compose -f docker-compose.dev.yml down

docker-logs: ## Show Docker logs
	docker-compose -f docker-compose.dev.yml logs -f

setup: install-dev ## Setup development environment
	@echo "Setting up development environment..."
	@echo "Copy env.example to .env in backend directory"
	cp backend/env.example backend/.env
	@echo "Development environment setup complete!"

check-all: lint test ## Run all checks

build-dev: ## Build development containers (CPU only)
	@echo "Building development containers..."
	docker-compose build

build-gpu: ## Build GPU containers
	@echo "Building GPU containers..."
	docker-compose -f docker-compose.gpu.yml build

up-dev: ## Start development environment (CPU only)
	@echo "Starting development environment..."
	docker-compose up -d

up-gpu: ## Start GPU environment
	@echo "Starting GPU environment..."
	docker-compose -f docker-compose.gpu.yml up -d

down: ## Stop all containers
	@echo "Stopping all containers..."
	docker-compose down
	docker-compose -f docker-compose.gpu.yml down

clean: ## Clean up containers and volumes
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v
	docker-compose -f docker-compose.gpu.yml down -v
	docker system prune -f

test-dev: ## Run tests in development environment
	@echo "Running tests in development environment..."
	docker-compose exec backend pytest
	docker-compose exec frontend npm test

test-gpu: ## Run tests in GPU environment
	@echo "Running tests in GPU environment..."
	docker-compose -f docker-compose.gpu.yml exec backend pytest
	docker-compose -f docker-compose.gpu.yml exec frontend npm test

logs: ## Show logs for all services
	@echo "Showing logs for all services..."
	docker-compose logs -f

logs-gpu: ## Show logs for GPU services
	@echo "Showing logs for GPU services..."
	docker-compose -f docker-compose.gpu.yml logs -f

backend-logs: ## Show backend logs
	@echo "Showing backend logs..."
	docker-compose logs -f backend

frontend-logs: ## Show frontend logs
	@echo "Showing frontend logs..."
	docker-compose logs -f frontend

celery-logs: ## Show celery logs
	@echo "Showing celery logs..."
	docker-compose logs -f celery

flower-logs: ## Show flower logs
	@echo "Showing flower logs..."
	docker-compose logs -f flower

restart-backend: ## Restart backend service
	@echo "Restarting backend service..."
	docker-compose restart backend

restart-frontend: ## Restart frontend service
	@echo "Restarting frontend service..."
	docker-compose restart frontend

restart-celery: ## Restart celery service
	@echo "Restarting celery service..."
	docker-compose restart celery

status: ## Show status of all services
	@echo "Showing status of all services..."
	docker-compose ps

status-gpu: ## Show status of GPU services
	@echo "Showing status of GPU services..."
	docker-compose -f docker-compose.gpu.yml ps

shell-backend: ## Open shell in backend container
	@echo "Opening shell in backend container..."
	docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	@echo "Opening shell in frontend container..."
	docker-compose exec frontend bash

shell-backend-gpu: ## Open shell in GPU backend container
	@echo "Opening shell in GPU backend container..."
	docker-compose -f docker-compose.gpu.yml exec backend bash

shell-frontend-gpu: ## Open shell in GPU frontend container
	@echo "Opening shell in GPU frontend container..."
	docker-compose -f docker-compose.gpu.yml exec frontend bash
