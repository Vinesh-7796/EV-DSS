#!/usr/bin/env bash
# =============================================================================
# EV-DDSS Environment Setup Script (Unix/Linux/macOS)
# =============================================================================
# Usage:
#   ./scripts/setup.sh            # Create venv and install dependencies
#   ./scripts/setup.sh --dev      # Include dev dependencies
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"

echo "========================================"
echo "  EV-DDSS Environment Setup"
echo "========================================"
echo ""

# Check Python version
python3 --version

# Create virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
    echo "  Virtual environment created at: $VENV_PATH"
else
    echo "Virtual environment already exists: $VENV_PATH"
fi

# Activate paths
PIP="$VENV_PATH/bin/pip"
PYTHON="$VENV_PATH/bin/python"

# Upgrade pip
echo "Upgrading pip..."
"$PYTHON" -m pip install --upgrade pip --quiet

# Install requirements
echo "Installing production dependencies..."
"$PIP" install -r "$PROJECT_ROOT/requirements.txt" --quiet

# Install dev dependencies if requested
if [ "${1:-}" = "--dev" ]; then
    echo "Installing development dependencies..."
    "$PIP" install -r "$PROJECT_ROOT/requirements-dev.txt" --quiet
fi

# Create .env from example if not exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "Created .env from .env.example - please update with your settings."
fi

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the application:"
echo "  python main.py"
echo ""
echo "To run tests:"
echo "  python main.py test"
echo "  (or) pytest tests/ -v"
