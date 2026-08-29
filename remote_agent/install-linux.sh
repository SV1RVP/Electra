#!/bin/bash
# ==============================================================================
# Remote UPS Agent - Universal Linux / Raspberry Pi Installer
# Author: Alexandros - Ermis Tsourapas (SV1RVP)
# License: GNU Affero General Public License v3.0 (AGPL-3.0)
# ==============================================================================

set -e

echo ""
echo "======================================================================"
echo "    REMOTE UPS AGENT - UNIVERSAL LINUX / RASPBERRY PI INSTALLER"
echo "======================================================================"
echo ""

# 1. Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS=$(uname -s)
fi

echo "[1/4] Detected OS: $OS"
echo "Installing system packages & USB/HID libraries..."

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
    arch)
        sudo pacman -Syu --noconfirm python python-pip libusb hidapi systemd
        ;;
    opensuse*|suse)
        sudo zypper refresh
        sudo zypper install -y python3 python3-pip python3-virtualenv libusb-1_0-devel hidapi-devel
        ;;
    alpine)
        sudo apk update
        sudo apk add python3 py3-pip libusb-dev hidapi-dev udev
        ;;
    *)
        echo "[WARNING] Unknown distribution: $OS"
        ;;
esac

# 2. Virtual Environment Setup
CURRENT_DIR=$(pwd)
USER=$(whoami)

echo ""
echo "[2/4] Setting up Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. USB udev rules
echo ""
echo "[3/4] Configuring USB udev rules for UPS..."
UDEV_RULE_FILE="/etc/udev/rules.d/99-ups-agent.rules"

sudo bash -c "cat > $UDEV_RULE_FILE << EOF
# Generic MEC0003 HID UPS (0001:0000)
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0001\", ATTR{idProduct}==\"0000\", MODE=\"0666\", GROUP=\"plugdev\"
# Cypress / TECHID Q1 UPS (0665:5161)
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0665\", ATTR{idProduct}==\"5161\", MODE=\"0666\", GROUP=\"plugdev\"
# APC by Schneider Electric (051d)
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"051d\", MODE=\"0666\", GROUP=\"plugdev\"
# CyberPower Systems (0764)
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0764\", MODE=\"0666\", GROUP=\"plugdev\"
# Eaton / Powerware (0463)
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0463\", MODE=\"0666\", GROUP=\"plugdev\"
# Tripp Lite (09ae)
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"09ae\", MODE=\"0666\", GROUP=\"plugdev\"
EOF"

sudo udevadm control --reload-rules || true
sudo udevadm trigger || true

for grp in plugdev dialout uucp; do
    if getent group $grp >/dev/null 2>&1; then
        sudo usermod -a -G $grp $USER || true
    fi
done

# 4. Startup Script & Autostart (systemd)
echo ""
echo "[4/4] Configuring startup scripts & autostart..."

cat > run_agent.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python ups_agent.py
else
    python3 ups_agent.py
fi
EOF
chmod +x run_agent.sh
echo "  - Created run_agent.sh for manual launching."

echo ""
read -p "Do you want to enable Autostart on system boot via systemd service? (Y/n): " AUTO_CHOICE
AUTO_CHOICE=${AUTO_CHOICE:-Y}

if [[ "$AUTO_CHOICE" =~ ^[Yy]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/ups-agent.service"
    echo "Creating and starting systemd service ($SERVICE_FILE)..."
    sudo bash -c "cat > $SERVICE_FILE << EOF
[Unit]
Description=Remote UPS Telemetry Agent
After=network.target

[Service]
User=$USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/.venv/bin/python $CURRENT_DIR/ups_agent.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ups-agent

[Install]
WantedBy=multi-user.target
EOF"

    sudo systemctl daemon-reload
    sudo systemctl enable ups-agent.service
    sudo systemctl restart ups-agent.service
    echo "  - Autostart enabled via systemd (ups-agent.service)."
else
    echo "  - Autostart skipped. Run manually with ./run_agent.sh"
fi

echo ""
echo "======================================================================"
echo "            REMOTE AGENT INSTALLATION COMPLETED!"
echo "======================================================================"
echo "Make sure to edit agent_config.json with the Central Server IP & API key."
echo "  - Manual start: ./run_agent.sh"
if [[ "$AUTO_CHOICE" =~ ^[Yy]$ ]]; then
    echo "  - View live logs: sudo journalctl -u ups-agent -f"
fi
echo ""
