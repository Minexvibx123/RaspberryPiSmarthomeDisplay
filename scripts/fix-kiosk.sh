#!/usr/bin/env bash
# HomePanel Kiosk-Installation/Fix (als root ausfuehren:  sudo bash scripts/fix-kiosk.sh)
#
# Architektur:
#  - Autologin auf tty1 => echte Login-Sitzung auf seat0 (DRM-Zugriff garantiert)
#  - ~/.bash_profile startet die Kiosk-Session (cage am DSI-Display, 270°=Landscape)
#  - systemd homepanel-vnc.service => Browser-View (Xvfb + x11vnc + noVNC)
#  - Der alte homepanel.service (PAMName+Conflicts) wird deaktiviert: er
#    verlor den logind-Seat zuverlaessig (Race) und kaempft mit getty um tty1.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || echo root)}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

if [ "$(id -u)" -ne 0 ]; then
    echo "FEHLER: Bitte mit sudo ausfuehren:  sudo bash $0"; exit 1
fi

echo "==> [1/5] Systempakete (Browser-View)"
apt-get update >/dev/null
apt-get install -y xvfb x11vnc novnc websockify x11-xserver-utils

echo "==> [2/5] Autologin auf tty1 einrichten"
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $TARGET_USER --noclear %I \$TERM
EOF

echo "==> [3/5] Kiosk-Hook in $TARGET_HOME/.bash_profile"
mkdir -p "$TARGET_HOME"
PROFILE="$TARGET_HOME/.bash_profile"
HOOK="# ---> HomePanel Kiosk <---"
if ! grep -qF "kiosk-session.sh" "$PROFILE" 2>/dev/null; then
    printf '\n%s\nif [ -z "\${SSH_CONNECTION:-}" ] && [ "\$(tty 2>/dev/null)" = "/dev/tty1" ]; then\n    exec %s/scripts/kiosk-session.sh\nfi\n' "$HOOK" "$APP_DIR" >> "$PROFILE"
    echo "    Hook ergaenzt"
else
    echo "    Hook vorhanden"
fi
chown "$TARGET_USER:" "$PROFILE" 2>/dev/null || true

echo "==> [4/5] Alten homepanel.service deaktivieren, VNC-Service aktivieren"
systemctl stop homepanel.service 2>/dev/null || true
systemctl disable homepanel.service 2>/dev/null || true
systemctl reset-failed homepanel.service 2>/dev/null || true

sed "s#/home/pi/homepanel#$APP_DIR#g; s#User=pi#User=$TARGET_USER#g" \
    "$APP_DIR/systemd/homepanel-vnc.service" | tee /etc/systemd/system/homepanel-vnc.service > /dev/null
systemctl daemon-reload
systemctl enable getty@tty1.service
systemctl enable homepanel-vnc.service
systemctl start homepanel-vnc.service

echo "==> [5/5] Fertig – Neustart noetig (Autologin-Sitzung)"
echo "    sudo reboot"
echo ""
echo "    Nach dem Boot: Panel am Display (270° Landscape) +"
echo "    Browser-View unter  http://<IP>:6080/vnc.html"
echo "    Logs Kiosk:   journalctl --user -b 0 -f  (bzw. Datei ~/homepanel/kiosk.log)"