#!/bin/bash
# ==============================================================================
# Electra - UPS Status Central Monitor - Linux Uninstaller
# Author: Alexandros - Ermis Tsourapas (SV1RVP)
# License: GNU Affero General Public License v3.0 (AGPL-3.0)
# ==============================================================================

set -e

echo ""
echo "======================================================================"
echo "      Electra - UPS STATUS CENTRAL MONITOR - LINUX UNINSTALLER"
echo "    Creator: Alexandros - Ermis Tsourapas (SV1RVP)"
echo "======================================================================"
echo ""

SERVICES=("electra.service" "ups-status.service")

echo "[1/3] Stopping and disabling systemd services..."
for SERVICE_NAME in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        sudo systemctl stop "$SERVICE_NAME"
        echo "  - $SERVICE_NAME stopped."
    fi

    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        sudo systemctl disable "$SERVICE_NAME"
        echo "  - $SERVICE_NAME disabled."
    fi

    SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
    if [ -f "$SERVICE_FILE" ]; then
        sudo rm -f "$SERVICE_FILE"
        echo "  - $SERVICE_FILE removed."
    fi
done

sudo systemctl daemon-reload

echo ""
echo "[2/3] Removing udev rules..."
for UDEV in "/etc/udev/rules.d/99-electra-ups.rules" "/etc/udev/rules.d/99-ups-status.rules"; do
    if [ -f "$UDEV" ]; then
        sudo rm -f "$UDEV"
        echo "  - $UDEV removed."
    fi
done
sudo udevadm control --reload-rules || true

echo ""
echo "[3/3] Cleaning up virtual environment and runtime cache..."
if [ -d ".venv" ]; then
    rm -rf ".venv"
    echo "  - .venv directory deleted."
fi

echo ""
echo "======================================================================"
echo "                 [SUCCESS] UNINSTALLATION COMPLETED!"
echo "======================================================================"
echo "The background service, system configurations, and .venv have been removed."
echo ""
