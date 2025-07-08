# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **exlm** project - a Domain-Specific LLM Automation Platform. The project is currently in the initial planning phase with a Product Requirements Document (PRD) written in Korean.

## Project Goals

Build an automated platform that:

- Fine-tunes open-source LLMs or uses paid APIs for specific domains
- Generates domain-specific synthetic datasets
- Combines latest algorithms (DPO, ORPO, QLoRA, RAG, etc.)
- Serves models via vLLM with OpenAI-compatible APIs
- Generates code for new training pipelines based on user-selected techniques

## Planned Architecture

### Frontend

- **Framework**: React/Next.js
- **Purpose**: UI for model selection, pipeline configuration, and monitoring

### Backend

- **API**: FastAPI
- **Pipeline Management**: Prefect/Celery
- **Model Training**: Hugging Face Transformers, PEFT, trl
- **Data Generation**: Integration with OpenAI, Claude, Gemini APIs
- **Code Generation**: Python + Jinja2 templates
- **Model Serving**: vLLM
- **Monitoring**: W&B/MLflow
- **Deployment**: Docker/Kubernetes

## Key Features

1. **Model Selection & Training**

   - Support for latest open-source LLMs (Llama3, Mistral, Qwen2, Phi-3, etc.)
   - LoRA/QLoRA for efficient fine-tuning
   - Latest techniques: DPO, ORPO, RAG

2. **Domain Data Generation**

   - Synthetic data generation using LLM APIs
   - Prompt template management
   - Data quality evaluation and filtering

3. **Training Pipeline Automation**

   - End-to-end automation: upload → preprocess → train → evaluate → save
   - Mix and match latest techniques
   - Real-time monitoring

4. **Model Serving**

   - vLLM for OpenAI API-compatible serving
   - Optional TGI, FastAPI serving
   - Automated deployment

5. **Code Generation**
   - Generate complete training pipelines based on selected techniques
   - Outputs: train.py, data_pipeline.py, serve.py, README, requirements

## Development Commands

Since the project is in initial planning phase, no build/test commands exist yet. When implementing:

### Expected Python Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt

# Run backend API (once implemented)
uvicorn main:app --reload

# Run tests (once implemented)
pytest
```

### Expected Frontend Setup

```bash
# Install dependencies (once package.json exists)
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

## Project Status

**Current Phase**: Planning/Design

- PRD completed in Korean
- No code implementation yet
- Technology stack defined but not initialized

## Next Steps

When starting implementation:

1. Initialize backend with FastAPI structure
2. Set up frontend with React/Next.js
3. Create Docker configuration
4. Implement basic model selection UI
5. Set up pipeline orchestration with Prefect/Celery

## 개발 자동화 및 루프 (for Claude Code)

This project provides an automated development loop to allow Claude Code to repeatedly build, test, debug, and receive feedback. Please refer to the following details to ensure Claude Code can build/test/debug/receive feedback in real-time:

### 1. Backend Development Loop

- **Makefile**: `backend/Makefile` can be used to automate the development loop with the following commands:
  - `make install-dev` : Install development dependencies
  - `make run-dev` : Run FastAPI development server (hot reload)
  - `make test` : Run full tests and coverage
  - `make lint`/`make format`/`make type-check` : Automate code quality
  - `make check-all` : Check overall quality and tests
- **Tests**: Basic tests and pytest setup are available in the `tests/` folder.
- **Debugging**: VS Code has a launch.json setup to debug FastAPI server/tests.
- **Feedback Loop**: Test failure/success, coverage, lint results are immediately visible.

### 2. Frontend Development Loop

- **Makefile**: `frontend/Makefile` can be used to automate the development loop with the following commands:
  - `make dev` : Run Next.js development server
  - `make test`/`make test-watch`/`make test-coverage` : Jest-based tests
  - `make lint`/`make format`/`make type-check` : Automate code quality
- **Tests**: Basic test examples are available in the `src/__tests__/` folder.
- **Debugging**: VS Code has React/Next.js debugging capabilities.

### 3. Docker and Integrated Development Environment

- **docker-compose.dev.yml**: Allows running a development environment in one go (backend, frontend, db, redis, celery, etc.)
  - Manage with `make docker-up`/`make docker-down`/`make docker-logs`
- **Dockerfile.dev**: Provides Dockerfile for development for backend/frontend

### 4. VS Code Development Environment

- `.vscode/settings.json` : Python, TypeScript, ESLint, formatter, test automation setup
- `.vscode/launch.json` : FastAPI, Pytest, current file debugging support

### 5. Project Root Makefile

- `make install-dev` : Install all dependencies
- `make run-dev` : Run backend/frontend development servers simultaneously
- `make test`/`make lint`/`make format` : Check overall quality
- `make setup` : Automate development environment setup

### 6. Feedback Loop Example

1. Modify code
2. Run `make test` or `make check-all`
3. Immediately check test failure/success, coverage/quality report
4. If necessary, debug breakpoint in VS Code

Claude Code should actively utilize the automated development loop to repeatedly build, test, debug, and receive feedback. (e.g., code after writing, run tests/build/quality check, repeat if failure, analyze and fix)

---

Claude Code is intended to be used in this automated development loop, and should be used to repeatedly build, test, debug, and receive feedback. (e.g., code after writing, run tests/build/quality check, repeat if failure, analyze and fix)

---
