#!/usr/bin/env bash
# HomePanel: cage mit Touch-Fix bauen und installieren.
#
# Problem: Debian cage 0.3.1 + wlroots 0.20 setzen fuer reale libinput-
# Touchscreens kein output_name -> cage mappt den Touch nie auf einen
# Output -> die 270°-Output-Transformation wird nicht auf die Touch-
# Koordinaten angewendet (Touch bleibt im Portrait-Raster).
#
# Fix: Patch (patches/cage-0.3.1-touch-mapping.patch) ergaenzt
#   1. Fallback: Touch auf das einzige Output mappen, wenn kein
#      output_name vorhanden ist (Kiosk = 1 Display).
#   2. Nachruesten: Touch-Devices, die VOR dem ersten Output eintreffen,
#      werden bei handle_new_output nachtraeglich gemappt.
#
# Das Binary wird nach /usr/local/bin/cage installiert (Apt-Paket
# /usr/bin/cage bleibt unberuehrt; /usr/local/bin hat PATH-Vorrang).
set -euo pipefail

CAGE_VER="v0.3.1"
BUILD_DIR="/tmp/opencode/cage-build"
PATCH="$HOME/homepanel/patches/cage-0.3.1-touch-mapping.patch"

if ! command -v meson >/dev/null; then
    echo "Build-Werkzeuge fehlen. Installiere..."
    sudo apt-get install -y --no-install-recommends \
        meson ninja-build libwlroots-0.20-dev libwayland-dev \
        libxkbcommon-dev libinput-dev libgbm-dev libdrm-dev
fi

rm -rf "$BUILD_DIR"
git clone --quiet --depth 1 --branch "$CAGE_VER" https://github.com/cage-kiosk/cage "$BUILD_DIR"
cd "$BUILD_DIR"
git apply "$PATCH"
meson setup build
ninja -C build
sudo ninja -C build install
sudo chmod 755 /usr/local/bin/cage
echo "OK: /usr/local/bin/cage installiert. Kiosk-Session neu starten:"
echo "    sudo systemctl restart getty@tty1"