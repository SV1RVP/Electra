#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================================"
echo "  Electra Remote Agent - Manual Update Launcher"
echo "========================================================"
echo ""

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python update.py
elif command -v python3 &>/dev/null; then
    python3 update.py
else
    python update.py
fi

echo ""
