#!/bin/bash

echo "🛑 Stopping existing processes..."

# Kill processes on ports 3000 and 8000
lsof -ti:3000 | xargs kill -9 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Wait a moment for processes to fully stop
sleep 2

echo "🚀 Starting House Whisperer application..."

# Start backend in background
echo "📡 Starting backend API server..."
cd api && uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "💻 Starting frontend development server..."
cd .. && npm start

# When frontend is stopped (Ctrl+C), also stop backend
echo "🛑 Stopping backend..."
kill $BACKEND_PID 2>/dev/null