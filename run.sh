#!/bin/bash
# ── Logistics AI Assistant — Run Script ──────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚛 Logistics AI Assistant"
echo "========================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Please install it."
    exit 1
fi

# Create virtual environment if needed
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet

# Setup .env if not exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚙️  Creating .env from template..."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "⚠️  Please set your OPENAI_API_KEY in .env file"
    echo "   (The system will use regex-based fallback without it)"
fi

# Create upload directory
mkdir -p "$SCRIPT_DIR/backend/uploads"

# Run the server
echo ""
echo "🚀 Starting server at http://localhost:8000"
echo "📖 API docs at http://localhost:8000/docs"
echo ""

cd "$SCRIPT_DIR/backend"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
