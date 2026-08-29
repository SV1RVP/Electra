#!/bin/bash
cd "$(dirname "$0")"
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python ups_agent.py
else
    python3 ups_agent.py
fi
