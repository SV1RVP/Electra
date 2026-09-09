#!/bin/bash
# ==============================================================================
# Electra - UPS Status Central Monitor - Universal Linux Installer
# Author: Alexandros - Ermis Tsourapas (SV1RVP)
# License: GNU Affero General Public License v3.0 (AGPL-3.0)
# ==============================================================================

set -e

echo ""
echo "======================================================================"
echo "    Electra - UPS STATUS CENTRAL MONITOR - LINUX INSTALLER"
echo "    Creator: Alexandros - Ermis Tsourapas (SV1RVP)"
echo "    License: GNU AGPL-3.0"
echo "======================================================================"
echo ""

# 1. Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS=$(uname -s)
fi

echo "[1/5] Detected OS: $OS"
echo "Installing system packages & USB/HID development libraries..."

case $OS in
    ubuntu|debian|raspbian)
        sudo apt-get update -y
        sudo apt-get install -y python3 python3-pip python3-venv libusb-1.0-0-dev libhidapi-dev udev
        ;;
    fedora)
        sudo dnf update -y
        sudo dnf install -y python3 python3-pip libusbx-devel hidapi-devel systemd-udev
        ;;
    centos|rhel|almalinux|rocky)
        sudo dnf install -y epel-release
        sudo dnf update -y
        sudo dnf install -y python3 python3-pip libusbx-devel hidapi-devel systemd-udev
        ;;
    arch|manjaro)
        sudo pacman -Sy --noconfirm python python-pip libusb hidapi systemd
        ;;
    alpine)
        sudo apk update
        sudo apk add python3 py3-pip python3-dev libusb-dev hidapi-dev build-base udev
        ;;
    *)
        echo "[WARNING] Unknown distribution: $OS. Attempting with standard tools..."
        ;;
esac

echo "[OK] System prerequisites installed."
echo ""

# 2. Setup Python Virtual Environment
CURRENT_DIR=$(pwd)
echo "[2/5] Creating Python virtual environment in: $CURRENT_DIR/.venv ..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "[OK] Created .venv directory."
else
    echo "[OK] Existing .venv directory found."
fi

# 3. Upgrade pip and install requirements
echo ""
echo "[3/5] Installing Python dependencies..."
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt

echo "[OK] Python dependencies installed successfully."
echo ""

# 4. USB udev rules for non-root access
echo "[4/5] Configuring udev rules for direct USB access..."
UDEV_RULE_FILE="/etc/udev/rules.d/99-electra-ups.rules"

if [ ! -f "$UDEV_RULE_FILE" ]; then
    echo "Creating $UDEV_RULE_FILE ..."
    sudo bash -c "cat > $UDEV_RULE_FILE << 'EOF'
# Electra UPS Monitoring USB/HID Devices Access
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0665\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"051d\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0764\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"hidraw\", MODE=\"0666\", GROUP=\"plugdev\"
EOF"
    sudo udevadm control --reload-rules || true
    sudo udevadm trigger || true
    echo "[OK] udev rules applied."
else
    echo "[OK] udev rules already present."
fi

# Add current user to plugdev/dialout
sudo usermod -a -G dialout,plugdev "$USER" 2>/dev/null || true

# 5. Startup Script & systemd Service
echo ""
echo "[5/5] Configuring startup scripts and systemd service..."

cat > start_server.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python app.py
else
    python3 app.py
fi
EOF
chmod +x start_server.sh
echo "  - Created start_server.sh for manual launching."

echo ""
read -p "Do you want to enable Electra Autostart on system boot via systemd service? (Y/n): " AUTO_CHOICE
AUTO_CHOICE=${AUTO_CHOICE:-Y}

if [[ "$AUTO_CHOICE" =~ ^[Yy]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/electra.service"
    echo "Creating and starting systemd service ($SERVICE_FILE)..."
    sudo bash -c "cat > $SERVICE_FILE << EOF
[Unit]
Description=Electra - UPS Status Central Monitor
After=network.target

[Service]
User=$USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/.venv/bin/python $CURRENT_DIR/app.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=electra-ups

[Install]
WantedBy=multi-user.target
EOF"

    sudo systemctl daemon-reload
    sudo systemctl enable electra.service
    sudo systemctl restart electra.service
    echo "  - Autostart enabled via systemd service (electra.service)."
else
    echo "  - Autostart skipped. You can run the server manually using ./start_server.sh"
fi

echo ""
echo "======================================================================"
echo "          [SUCCESS] Electra INSTALLED SUCCESSFULLY!                   "
echo "======================================================================"
echo "  - Access WebUI Dashboard: http://localhost:8088 (or http://<IP>:8088)"
echo "  - Manual start: ./start_server.sh"
if [[ "$AUTO_CHOICE" =~ ^[Yy]$ ]]; then
    echo "  - View live service logs: sudo journalctl -u electra -f"
    echo "  - Service status: sudo systemctl status electra"
fi
echo ""
