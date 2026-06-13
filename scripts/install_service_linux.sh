#!/usr/bin/env bash
#
# Installs nfc-unlock-pc as a systemd --user service that starts at login
# and keeps watching the ACR122U for your enrolled tag.
#
# Usage:
#   bash scripts/install_service_linux.sh
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Prefer a project virtualenv if one exists, otherwise fall back to python3
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python3)"
fi

UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

cat > "$UNIT_DIR/nfc-unlock-pc.service" <<EOF
[Unit]
Description=NFC Unlock PC - tap-to-unlock background service
After=graphical-session.target

[Service]
ExecStart=$PYTHON $PROJECT_ROOT/src/main.py run
Restart=on-failure
RestartSec=5
Environment=DISPLAY=${DISPLAY:-:0}
Environment=WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}
Environment=XAUTHORITY=${XAUTHORITY:-%h/.Xauthority}

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now nfc-unlock-pc.service

echo "Installed and started nfc-unlock-pc.service (systemd --user)."
echo "Check status with: systemctl --user status nfc-unlock-pc.service"
echo "Logs with:         journalctl --user -u nfc-unlock-pc.service -f"
echo
echo "To remove: systemctl --user disable --now nfc-unlock-pc.service && rm $UNIT_DIR/nfc-unlock-pc.service"
