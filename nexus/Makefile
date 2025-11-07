.PHONY: help install setup dev docker-up docker-down test clean

help:
	@echo "PDF Comparison Service - Make Commands"
	@echo "======================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup      - Initial setup (create venv, install deps)"
	@echo "  make install    - Install dependencies only"
	@echo ""
	@echo "Development:"
	@echo "  make dev        - Start development server"
	@echo "  make worker     - Start Celery worker"
	@echo "  make redis      - Start Redis in Docker"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up  - Start all services with Docker Compose"
	@echo "  make docker-down - Stop all Docker services"
	@echo "  make docker-logs - View Docker logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean      - Clean temporary files"
	@echo "  make format     - Format code with black"
	@echo "  make lint       - Lint code with flake8"
	@echo ""

setup:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	cp -n .env.example .env || true
	mkdir -p outputs logs temp
	@echo "✓ Setup complete! Edit .env and add your API keys."

install:
	. venv/bin/activate && pip install -r requirements.txt

dev:
	. venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	. venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

redis:
	docker run -d -p 6379:6379 --name pdf_comparison_redis redis:alpine || docker start pdf_comparison_redis

docker-up:
	docker-compose up -d
	@echo "✓ Services started!"
	@echo "  API: http://localhost:8000"
	@echo "  Docs: http://localhost:8000/docs"
	@echo "  Flower: http://localhost:5555"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

test:
	. venv/bin/activate && pytest

test-cov:
	. venv/bin/activate && pytest --cov=app --cov-report=html --cov-report=term

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf outputs/* temp/* logs/*
	@echo "✓ Cleaned temporary files"

format:
	. venv/bin/activate && black app/ tests/

lint:
	. venv/bin/activate && flake8 app/ tests/ --max-line-length=100

health:
	curl -s http://localhost:8000/api/v1/health | python -m json.tool

# Development workflow
dev-all: redis
	@echo "Starting all development services..."
	@make -j2 worker dev

# Production build
build:
	docker-compose build

# View logs
logs-api:
	tail -f logs/app.log

logs-worker:
	docker-compose logs -f worker
