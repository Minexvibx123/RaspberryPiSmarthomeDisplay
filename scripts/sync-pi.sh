#!/usr/bin/env bash
# Synchronisiert den HomePanel-Code von diesem Rechner auf den Raspberry Pi.
#
# Verwendung:
#   ./scripts/sync-pi.sh                      # Ziel: pi@192.168.178.138
#   ./scripts/sync-pi.sh user@andere-ip       # anderes Ziel
#
# Geschützt bleiben auf dem Pi: .venv (Architektur-fremd), data/ (SQLite-DB),
# .git, thoughts/. Einmalig passwortfrei machen:
#   ssh-copy-id pi@192.168.178.138
set -euo pipefail

PI_TARGET="${1:-supervisor@192.168.178.138}"
PI_DIR="/home/supervisor/homepanel"

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

if [ ! -d "$APP_DIR/app" ]; then
    echo "Fehler: Skript muss im Projektverzeichnis liegen." >&2
    exit 1
fi

echo "==> Synchronisiere Code nach $PI_TARGET:$PI_DIR"
echo "    (Geschützt: .venv/, data/, .git/, thoughts/ — Passwort ggf. abfragen)"
rsync -avz --delete \
    --exclude '.venv/' \
    --exclude 'data/' \
    --exclude '.git/' \
    --exclude 'thoughts/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    "$APP_DIR/" "$PI_TARGET:$PI_DIR/"

echo ""
echo "==> Fertig. Jetzt auf dem Pi aktivieren:"
echo "    ssh $PI_TARGET"
echo "    cd $PI_DIR && source .venv/bin/activate && pip install -r requirements.txt"
echo "    sudo ./scripts/install.sh   # nur beim ersten Mal nötig (udev-Regel)"
echo "    sudo systemctl restart homepanel.service"
