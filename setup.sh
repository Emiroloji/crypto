#!/bin/bash

# Advanced Crypto Trading System - Setup Script

set -e

echo "=================================="
echo "Crypto Trading System Setup"
echo "=================================="

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

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys before running the system"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p models
mkdir -p monitoring/grafana/dashboards

# Start Docker services
echo "Starting Docker services..."
docker-compose up -d postgres redis

# Wait for services
echo "Waiting for services to start..."
sleep 10

# Initialize database
echo "Initializing database..."
python -c "from src.database.connection import init_db; init_db()"

echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: python main.py"
echo "3. Access API at http://localhost:8000"
echo ""
echo "⚠️  IMPORTANT: Paper trading is enabled by default"
echo "   Review QUICKSTART.md for detailed instructions"
echo "=================================="
