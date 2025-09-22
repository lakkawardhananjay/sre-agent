#!/bin/bash

# Development setup script for SRE Agent
# This script sets up the local development environment

set -e

echo "🚀 Setting up SRE Agent development environment"

# Check if Python 3.11+ is available
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)
REQUIRED_VERSION="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "❌ Python 3.11+ is required. Current version: $PYTHON_VERSION"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

echo "✅ Python version check passed: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "🛠️  Installing development dependencies..."
pip install pytest httpx pytest-asyncio black flake8 mypy

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔐 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Make scripts executable
echo "🔨 Making scripts executable..."
chmod +x deploy-gke.sh

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Edit .env file with your Gemini API key and other configuration"
echo "3. Run the application: python -m uvicorn src.sre_agent.main:app --reload"
echo "4. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "Useful commands:"
echo "- Start dev server: uvicorn src.sre_agent.main:app --reload"
echo "- Run tests: pytest"
echo "- Format code: black src/"
echo "- Lint code: flake8 src/"
echo "- Type check: mypy src/"
echo "- Docker build: docker build -t sre-agent ."
echo "- Docker run: docker-compose up"