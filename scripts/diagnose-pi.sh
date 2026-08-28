#!/usr/bin/env bash
# Sammelt Diagnose-Infos für HomePanel-Probleme auf dem Raspberry Pi.
# Auf dem PI ausführen:  bash scripts/diagnose-pi.sh
set -uo pipefail

APP_DIR="/home/supervisor/homepanel"

echo "=========== SYSTEM ==========="
uname -m
head -2 /etc/os-release
echo "--- Gruppen des Users ($(whoami)):"
groups

echo ""
echo "=========== SERVICE-DATEI (/etc/systemd/system/homepanel.service) ==========="
if [ -f /etc/systemd/system/homepanel.service ]; then
    cat /etc/systemd/system/homepanel.service
else
    echo "*** FEHLT! ***"
fi

echo ""
echo "=========== SYSTEMCTL ==========="
echo "--- is-enabled:"
systemctl is-enabled homepanel.service 2>&1
echo "--- is-active:"
systemctl is-active homepanel.service 2>&1
echo "--- status:"
systemctl status homepanel.service --no-pager -l 2>&1 | head -20

echo ""
echo "=========== LETZTE 40 LOG-ZEILEN ==========="
journalctl -u homepanel.service -n 40 --no-pager 2>&1 | tail -40

echo ""
echo "=========== VENV / PYTHON ==========="
ls -la "$APP_DIR/.venv/bin/python" 2>/dev/null || echo "*** venv-python FEHLT unter $APP_DIR/.venv ***"
"$APP_DIR/.venv/bin/python" -V 2>&1

echo ""
echo "=========== PYSIDE CHECK ==========="
"$APP_DIR/.venv/bin/python" - <<'EOF' 2>&1
import sys
try:
    import PySide6
    print("PySide6 Version:", PySide6.__version__)
except Exception as e:
    print("PySide6 IMPORT FEHLGESCHLAGEN:", e)
EOF

echo ""
echo "=========== DISPLAY-BERECHTIGUNG (für Standby/Aus) ==========="
ls -la /sys/class/backlight/*/bl_power 2>/dev/null || echo "Kein Backlight unter /sys/class/backlight gefunden"

echo ""
echo "=========== FERTIG – bitte KOMPLETTE Ausgabe zurückkopieren ==========="
