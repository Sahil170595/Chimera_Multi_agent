.PHONY: help install dev-install test lint format clean docker-build docker-up setup-dev benchmark security-check

# Default target
help:
	@echo "Muse Protocol - Available Commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  setup-dev     Set up development environment"
	@echo "  install       Install package in production mode"
	@echo "  dev-install   Install package with dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  test          Run tests with pytest"
	@echo "  test-cov      Run tests with coverage"
	@echo "  lint          Run linting checks (flake8, isort, black)"
	@echo "  format        Format code (isort, black)"
	@echo "  security-check Run security checks (bandit, safety)"
	@echo ""
	@echo "Benchmarking:"
	@echo "  benchmark     Run benchmark tests"
	@echo "  benchmark-all Run all benchmark types"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker images"
	@echo "  docker-up     Start services with docker-compose"
	@echo "  docker-down   Stop services"
	@echo ""
	@echo "Utilities:"
	@echo "  clean         Clean Python cache files"
	@echo "  check-env     Validate environment configuration"
	@echo "  run-episode   Generate new episode"
	@echo "  run-i18n      Sync translations"
	@echo "  validate-posts Validate episode posts"

setup-dev:
	@echo "🚀 Setting up development environment..."
	@bash setup-dev.sh

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=apps --cov=agents --cov=integrations --cov=schemas --cov-report=html --cov-report=term

lint:
	@echo "🔍 Running linting checks..."
	flake8 --exclude=.history --count --statistics
	isort --check-only --diff .
	black --check --diff .

format:
	@echo "🎨 Formatting code..."
	isort .
	black .

security-check:
	@echo "🔒 Running security checks..."
	bandit -r apps/ agents/ integrations/ schemas/
	safety check

benchmark:
	@echo "📊 Running benchmark tests..."
	python test_benchmarks.py

benchmark-all:
	@echo "📊 Running all benchmark types..."
	python test_benchmarks.py
	@echo "✅ All benchmarks completed"

clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +

docker-build:
	@echo "🐳 Building Docker images..."
	docker build -f infra/Dockerfile.cli -t muse-protocol-cli .
	docker build -f infra/Dockerfile.orchestrator -t muse-protocol-orchestrator .

docker-up:
	@echo "🐳 Starting services..."
	docker compose -f infra/docker-compose.yml up -d

docker-down:
	@echo "🐳 Stopping services..."
	docker compose -f infra/docker-compose.yml down

check-env:
	@if [ ! -f env.local ]; then echo "❌ Error: env.local file not found. Copy env.sample to env.local and fill in values."; exit 1; fi
	@echo "✅ Environment file found"

run-episode: check-env
	@echo "📝 Generating new episode..."
	python -m apps.cli episodes new --series chimera || echo "Episode generation failed - check implementation"

run-i18n: check-env
	@echo "🌍 Syncing translations..."
	python -m apps.cli i18n sync --langs de,zh,hi || echo "Translation failed - check implementation"

validate-posts:
	@echo "✅ Validating posts..."
	python -m apps.cli check || echo "Validation failed - check implementation"

