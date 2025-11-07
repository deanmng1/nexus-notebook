#!/bin/bash

# PDF Comparison Service - Setup Script
# This script sets up the development environment

set -e

echo "==================================="
echo "PDF Comparison Service - Setup"
echo "==================================="

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p outputs logs temp

# Set permissions
chmod +x scripts/*.sh

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys (OpenAI or Anthropic)"
echo "2. Start Redis: docker run -d -p 6379:6379 redis:alpine"
echo "3. Start Celery worker: celery -A app.workers.celery_app worker --loglevel=info"
echo "4. Start API server: uvicorn app.main:app --reload"
echo ""
echo "Or use Docker:"
echo "  docker-compose up"
echo ""
echo "Access the API docs at: http://localhost:8000/docs"
echo "==================================="
