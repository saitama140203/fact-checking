#!/bin/bash
# ===========================
# Start Production Environment
# ===========================

echo "🚀 Starting Fake News Detector - Production"
echo "============================================"

# Check for docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check for docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Build and start
echo ""
echo "📦 Building containers..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "============================================"
echo "✅ Production services started!"
echo ""
echo "   Backend API: http://localhost:8000"
echo "   API Docs:    http://localhost:8000/docs"
echo "   Frontend:    http://localhost:3000"
echo ""
echo "   Use 'docker-compose logs -f' to view logs"
echo "   Use 'docker-compose down' to stop"
echo "============================================"

