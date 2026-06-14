#!/bin/bash
# Start the Illustrate web server
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed."
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies (creates .venv if needed)
cd "$PROJECT_DIR"
uv sync

# Compile Illustrate if needed
if [ ! -f "$PROJECT_DIR/Illustrate/illustrate" ]; then
    echo "Compiling Illustrate..."
    gfortran "$PROJECT_DIR/Illustrate/illustrate.f" -o "$PROJECT_DIR/Illustrate/illustrate"
fi

echo "Starting Illustrate web server at http://127.0.0.1:5001"
cd "$SCRIPT_DIR"
uv run python app.py
