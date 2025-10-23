#!/bin/bash

# Standalone PDF Parser Test Script
# This script activates the virtual environment and runs the test

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Starting PDF Parser Test"
echo "Backend directory: $BACKEND_DIR"
echo "Test directory: $SCRIPT_DIR"

# Check if virtual environment exists
if [ -d "$BACKEND_DIR/venv" ]; then
    echo "📦 Activating virtual environment..."
    source "$BACKEND_DIR/venv/bin/activate"
elif [ -d "$BACKEND_DIR/.venv" ]; then
    echo "📦 Activating virtual environment..."
    source "$BACKEND_DIR/.venv/bin/activate"
else
    echo "⚠️  Warning: No virtual environment found in $BACKEND_DIR"
    echo "Make sure you have the required dependencies installed."
fi

# Change to test directory
cd "$SCRIPT_DIR"

# Check if Python and required modules are available
python -c "import docling, tiktoken" 2>/dev/null || {
    echo "❌ Required dependencies not found."
    echo "Please install dependencies in the backend:"
    echo "  cd $BACKEND_DIR"
    echo "  pip install -r requirements.txt"  # or however dependencies are installed
    exit 1
}

echo "✅ Dependencies found"

# Run the test
echo "🔍 Starting interactive test runner..."
python run_test.py "$@"

echo "🎉 Test completed!"



