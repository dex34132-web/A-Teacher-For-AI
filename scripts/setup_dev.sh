#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VENV_DIR="${PROJECT_ROOT}/.venv"

echo "==> Creating virtual environment in ${VENV_DIR} ..."
python3 -m venv "${VENV_DIR}"

echo "==> Activating virtual environment ..."
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "==> Upgrading pip ..."
pip install --upgrade pip

echo "==> Installing project in editable mode with dev dependencies ..."
pip install -e "${PROJECT_ROOT}[dev,all]"

echo "==> Running initial lint check ..."
ruff check "${PROJECT_ROOT}/core" || true

echo "==> Running type check ..."
mypy "${PROJECT_ROOT}/core" || true

echo ""
echo "Development environment ready."
echo "Activate with:  source ${VENV_DIR}/bin/activate"
