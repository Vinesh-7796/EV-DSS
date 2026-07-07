#!/usr/bin/env bash
# =============================================================================
# EV-DDSS Run Script (Unix/Linux/macOS)
# =============================================================================
# Usage:
#   ./scripts/run.sh              # Start the server
#   ./scripts/run.sh --test       # Run the test suite
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON="$VENV_PATH/bin/python"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

if [ "${1:-}" = "--test" ]; then
    echo "Running tests..."
    "$PYTHON" -m pytest tests/ -v
else
    echo "Starting EV-DDSS server..."
    "$PYTHON" main.py
fi
