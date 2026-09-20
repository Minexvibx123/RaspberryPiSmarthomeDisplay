#!/usr/bin/env bash
# One-time installer for Raspberry Pi OS (Bookworm/Trixie, 64-bit).
# Sets up all system packages (Wayland-Kiosk + Qt runtime), creates a
# virtualenv, installs Python requirements and enables autostart via systemd.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_SRC="$APP_DIR/systemd/homepanel.service"
SERVICE_DST="/etc/systemd/system/homepanel.service"

# libglib2.0-0t64 (Trixie+) vs. libglib2.0-0 (Bookworm/älter)
GLIB_PACKAGE="libglib2.0-0t64"
if ! apt-cache show "$GLIB_PACKAGE" >/dev/null 2>&1; then
    GLIB_PACKAGE="libglib2.0-0"
fi

echo "==> Installing system dependencies"
echo "    Kiosk: cage (Wayland-Compositor), wlr-randr (Rotation), xwayland"
echo "    Qt/PySide6 runtime + Python tooling"
sudo apt-get update
sudo apt-get install -y \
    python3-venv python3-pip \
    cage wlr-randr xwayland \
    libgl1 libegl1 "$GLIB_PACKAGE" libdbus-1-3 \
    libfontconfig1 libfreetype6 libharfbuzz0b \
    libxkbcommon0 libxkbcommon-x11-0 \
    libwayland-client0 libwayland-cursor0 libwayland-server0 \
    libxcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-shm0 \
    libxcb-xfixes0 libxcb-xinerama0 libxcb-xkb1 \
    fonts-dejavu-core

echo "==> Verifying kiosk tools"
command -v cage >/dev/null 2>&1 || { echo "    FEHLER: 'cage' wurde nicht installiert." >&2; exit 1; }
command -v wlr-randr >/dev/null 2>&1 || { echo "    FEHLER: 'wlr-randr' wurde nicht installiert." >&2; exit 1; }
echo "    cage $(cage --version 2>/dev/null || echo 'ok')"
echo "    wlr-randr $(wlr-randr --version 2>/dev/null || echo 'ok')"

echo "==> Ensuring user '$USER' is in 'video' group (required for backlight/DRM access)"
if id -nG "$USER" | grep -qw video; then
    echo "    User '$USER' is already in 'video' group."
else
    sudo usermod -aG video "$USER"
    echo "    Added '$USER' to 'video' group – re-login or reboot required for this to take effect."
fi

echo "==> Creating virtual environment"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Installing systemd service"
sudo sed "s#/home/pi/homepanel#$APP_DIR#g; s#User=pi#User=$(whoami)#g" "$SERVICE_SRC" | sudo tee "$SERVICE_DST" > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable homepanel.service

echo "==> Installing udev rule for backlight write access (Standby-Feature)"
sudo tee /etc/udev/rules.d/99-homepanel-backlight.rules > /dev/null << 'UDEV_EOF'
# Allow members of the 'video' group to control display backlight brightness
# and power state – required by HomePanel's Standby feature (bl_power + brightness).
ACTION=="add", SUBSYSTEM=="backlight", RUN+="/bin/sh -c 'chgrp video /sys/class/backlight/%k/brightness /sys/class/backlight/%k/bl_power; chmod g+w /sys/class/backlight/%k/brightness /sys/class/backlight/%k/bl_power'"
UDEV_EOF
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=backlight

# Immediately apply permissions so a reboot isn't strictly required for the udev part
for dev in /sys/class/backlight/*; do
    [ -e "$dev/brightness" ] && sudo chgrp video "$dev/brightness" && sudo chmod g+w "$dev/brightness"
    [ -e "$dev/bl_power" ]  && sudo chgrp video "$dev/bl_power"  && sudo chmod g+w "$dev/bl_power"
done

echo ""
echo "=========================================================="
echo "  Installation abgeschlossen!"
echo "=========================================================="
echo ""
echo "Nächste Schritte:"
echo ""
echo "  1. Bitte JETZT neu starten (Gruppenänderung 'video' wird"
echo "     erst nach Reboot/Login wirksam):"
echo ""
echo "       sudo reboot"
echo ""
echo "  2. Nach dem Reboot prüfen:"
echo "       sudo systemctl start homepanel.service"
echo "       sudo systemctl status homepanel.service"
echo ""
echo "  3. Logs anzeigen:"
echo "       journalctl -u homepanel.service -f"
echo ""
echo "Hinweis: Die Standby-Funktion der App (Display dimmen/ausschalten)"
echo "         schreibt in /sys/class/backlight/*/brightness + bl_power."
echo "         Die installierte udev-Regel gewährt der 'video'-Gruppe"
echo "         Schreibrechte – kein sudo nötig."
echo "=========================================================="
