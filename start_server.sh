#!/bin/bash
cd "$(dirname "$0")"
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python app.py
else
    python3 app.py
fi
