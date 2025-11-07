#!/bin/bash

# PDF Comparison Service - Development Start Script

set -e

echo "Starting PDF Comparison Service (Development Mode)"
echo "=================================================="

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Copy .env.example to .env and configure it."
    exit 1
fi

# Start Redis in background if not running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
fi

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 &
CELERY_PID=$!

# Start API server
echo "Starting API server..."
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Trap Ctrl+C and cleanup
trap "echo 'Stopping services...'; kill $CELERY_PID; exit" INT

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Cleanup
kill $CELERY_PID 2>/dev/null || true
