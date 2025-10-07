#!/bin/bash
# Development Environment Setup Script for Muse Protocol

set -e

echo "🚀 Setting up Muse Protocol development environment..."

# Check if Python 3.9+ is installed
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.9+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -e .[dev]

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Copy environment file if it doesn't exist
if [ ! -f "env.local" ]; then
    echo "📋 Creating environment file..."
    cp env.sample env.local
    echo "⚠️  Please edit env.local with your configuration"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p reports

# Run initial tests
echo "🧪 Running initial tests..."
python -m pytest tests/ -v

echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit env.local with your configuration"
echo "2. Run 'source venv/bin/activate' to activate the environment"
echo "3. Run 'make help' to see available commands"
echo "4. Run 'python test_benchmarks.py' to test the benchmark system"
