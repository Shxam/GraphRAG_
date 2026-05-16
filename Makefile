.PHONY: help install test lint format clean ingest eval dashboard demo docker-build docker-up docker-down

# Default target
help:
	@echo "PostMortemIQ - Makefile Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install          Install dependencies"
	@echo "  make install-dev      Install dev dependencies"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage"
	@echo "  make lint             Run linters"
	@echo "  make format           Format code with black and isort"
	@echo "  make type-check       Run mypy type checking"
	@echo ""
	@echo "Data & Evaluation:"
	@echo "  make ingest           Ingest real dataset (2M+ tokens)"
	@echo "  make ingest-dry-run   Dry run ingestion (count tokens only)"
	@echo "  make eval             Run accuracy evaluation"
	@echo ""
	@echo "Running:"
	@echo "  make run              Start API server"
	@echo "  make dashboard        Start Streamlit dashboard"
	@echo "  make demo             Run demo (API + Dashboard)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker images"
	@echo "  make docker-up        Start Docker Compose services"
	@echo "  make docker-down      Stop Docker Compose services"
	@echo "  make docker-logs      View Docker logs"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Clean temporary files"
	@echo "  make logs             View recent logs"
	@echo "  make health           Check system health"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio pytest-mock
	pip install black isort mypy pylint flake8

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	pytest-watch tests/ -v

# Code Quality
lint:
	@echo "Running flake8..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	@echo "Running pylint..."
	pylint pipelines/ llm/ graph/ orchestration/ utils/ --exit-zero

format:
	@echo "Formatting with black..."
	black .
	@echo "Sorting imports with isort..."
	isort .

format-check:
	black --check --diff .
	isort --check-only --diff .

type-check:
	mypy --ignore-missing-imports --no-strict-optional .

# Data & Evaluation
ingest:
	python data/ingest_real_data.py

ingest-dry-run:
	python data/ingest_real_data.py --dry-run

eval:
	python evaluation/accuracy_eval.py

# Running
run:
	python main.py

dashboard:
	streamlit run evaluation/dashboard.py

demo:
	@echo "Starting PostMortemIQ demo..."
	@echo "1. Starting API server in background..."
	python main.py &
	@sleep 5
	@echo "2. Starting dashboard..."
	streamlit run evaluation/dashboard.py

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services started. API: http://localhost:8000, Dashboard: http://localhost:8501"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

# Utilities
clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"

logs:
	@echo "Recent logs:"
	@ls -t logs/*.jsonl 2>/dev/null | head -1 | xargs tail -20 || echo "No logs found"

health:
	@echo "Checking system health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "API not running"

# Generate synthetic data
generate-data:
	python data/generate_incidents.py

# Load graph data
load-graph:
	python graph/load_graph.py

# Run benchmark
benchmark:
	@echo "Running benchmark..."
	curl -s http://localhost:8000/benchmark | python -m json.tool

# Quick start (for new users)
quickstart: install generate-data
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and add your API keys"
	@echo "  2. Run 'make run' to start the API"
	@echo "  3. Run 'make dashboard' in another terminal"
	@echo ""

# Development workflow
dev: format lint test
	@echo "✅ Development checks passed!"

# CI simulation
ci: install-dev format-check lint test-cov
	@echo "✅ CI checks passed!"

# Release preparation
release: clean ci
	@echo "✅ Ready for release!"
	@echo "Don't forget to:"
	@echo "  1. Update version in main.py"
	@echo "  2. Update CHANGELOG.md"
	@echo "  3. Tag the release"
