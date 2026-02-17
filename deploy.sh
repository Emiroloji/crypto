#!/bin/bash

# Crypto Trading System - Deployment Script
# This script helps deploy the system to production

set -e

echo "🚀 Crypto Trading System - Deployment"
echo "======================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "❌ Please don't run as root"
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

if ! command_exists docker; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo "✅ All prerequisites met"

# Check .env file
echo ""
echo "📝 Checking configuration..."

if [ ! -f .env ]; then
    echo "❌ .env file not found"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Check if API keys are configured
if grep -q "your_binance_api_key" .env || grep -q "demo_key_paper_trading" .env; then
    echo "⚠️  WARNING: Using demo/placeholder API keys"
    echo "   System will run in DEMO MODE with simulated data"
    read -p "   Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Configuration OK"

# Build and start services
echo ""
echo "🔨 Building and starting services..."

docker-compose down 2>/dev/null || true
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Services failed to start"
    docker-compose logs
    exit 1
fi

echo "✅ Services are running"

# Initialize database
echo ""
echo "💾 Initializing database..."

if command_exists python3; then
    python3 -c "from src.database.connection import init_db; init_db()" 2>/dev/null || true
fi

echo "✅ Database initialized"

# Show status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Access points:"
echo "   Dashboard:   http://localhost:8000"
echo "   API Docs:    http://localhost:8000/docs"
echo "   Grafana:     http://localhost:3000 (admin/admin)"
echo "   Prometheus:  http://localhost:9090"
echo ""
echo "📝 Logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop:"
echo "   docker-compose down"
echo ""
