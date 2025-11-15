#!/bin/bash

echo "🔍 LangSmith Trace Visualizer - Startup Script"
echo "=============================================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if Flask API is running
echo "🔌 Checking Flask API connection..."
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Flask API is running at http://localhost:5000"
else
    echo "⚠️  Flask API is not running at http://localhost:5000"
    echo ""
    echo "Please start the Flask API first:"
    echo "  cd .."
    echo "  python api.py"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

echo ""
echo "🚀 Starting development server..."
echo ""
echo "The visualization will open at: http://localhost:3000"
echo ""

npm run dev
