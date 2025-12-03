#!/bin/bash
# ===========================
# Start Development Environment
# ===========================

echo "🚀 Starting Fake News Detector - Development"
echo "============================================"

# Backend
echo ""
echo "📡 Starting Backend API..."
cd backend
python run.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Frontend
echo ""
echo "🌐 Starting Frontend..."
cd ../frontend
pnpm dev &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo "✅ Services started!"
echo ""
echo "   Backend API: http://localhost:8000"
echo "   API Docs:    http://localhost:8000/docs"
echo "   Frontend:    http://localhost:3000"
echo ""
echo "   Press Ctrl+C to stop all services"
echo "============================================"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

