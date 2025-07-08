.PHONY: help install dev build start lint format type-check test test-watch clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	npm install

dev: ## Run development server
	npm run dev

build: ## Build for production
	npm run build

start: ## Start production server
	npm start

lint: ## Run linting
	npm run lint

format: ## Format code
	npm run format

type-check: ## Run type checking
	npm run type-check

test: ## Run tests
	npm test

test-watch: ## Run tests in watch mode
	npm run test:watch

test-coverage: ## Run tests with coverage
	npm run test:coverage

clean: ## Clean up generated files
	rm -rf .next/
	rm -rf node_modules/
	rm -rf coverage/

check-all: lint type-check test ## Run all checks 