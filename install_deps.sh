#!/usr/bin/env bash
# Simple installer: creates .venv and installs pip requirements from requirements.txt
set -e

REQ=requirements.txt
VENV_DIR=".venv"

if [ ! -f "$REQ" ]; then
  echo "requirements.txt not found. Please place this script in the repo root."
  exit 1
fi

python3 -m pip install --upgrade pip setuptools wheel

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# Activate venv for this script
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$REQ"

echo ""
echo "Done. Activate the virtualenv with:"
echo "  source $VENV_DIR/bin/activate"
echo "Then run:"
echo "  python bot_gui.py"
