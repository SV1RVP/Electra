#!/bin/bash
# ==============================================================================
# Remote UPS Agent - Linux Uninstaller
# Author: Alexandros - Ermis Tsourapas (SV1RVP)
# License: GNU Affero General Public License v3.0 (AGPL-3.0)
# ==============================================================================

set -e

echo ""
echo "======================================================================"
echo "         REMOTE UPS AGENT - LINUX UNINSTALLER"
echo "======================================================================"
echo ""

read -p "This will stop and remove the Remote UPS Agent service. Proceed? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

SERVICE_NAME="ups-agent.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
UDEV_RULE="/etc/udev/rules.d/99-ups-agent.rules"

if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl stop "$SERVICE_NAME"
    echo "  - Service stopped."
fi

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    sudo systemctl disable "$SERVICE_NAME"
    echo "  - Service disabled."
fi

if [ -f "$SERVICE_FILE" ]; then
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
    echo "  - Service file removed."
fi

if [ -f "$UDEV_RULE" ]; then
    sudo rm -f "$UDEV_RULE"
    sudo udevadm control --reload-rules || true
    echo "  - udev rules removed."
fi

read -p "Do you want to remove the Python virtual environment (.venv)? (y/N): " del_venv
if [[ "$del_venv" == "y" || "$del_venv" == "Y" ]]; then
    if [ -d ".venv" ]; then
        rm -rf ".venv"
        echo "  - .venv removed."
    fi
fi

echo ""
echo "======================================================================"
echo "                 UNINSTALLATION COMPLETED!"
echo "======================================================================"
echo ""
