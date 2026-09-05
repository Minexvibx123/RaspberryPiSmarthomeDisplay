#!/usr/bin/env bash
# Installs HomePanel directly from the official GitHub repository.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Minexvibx123/RaspberryPiSmarthomeDisplay/main/scripts/install-github.sh | bash
#
# Optional environment variables:
#   HOMEPANEL_DIR=/home/pi/homepanel HOMEPANEL_BRANCH=main bash install-github.sh
set -euo pipefail

REPOSITORY_URL="${HOMEPANEL_REPOSITORY:-https://github.com/Minexvibx123/RaspberryPiSmarthomeDisplay.git}"
BRANCH="${HOMEPANEL_BRANCH:-main}"
INSTALL_DIR="${HOMEPANEL_DIR:-$HOME/homepanel}"

if [ -e "$INSTALL_DIR" ]; then
    echo "Fehler: Zielverzeichnis existiert bereits: $INSTALL_DIR" >&2
    echo "Für bestehende Installationen nutze: $INSTALL_DIR/scripts/update-github.sh" >&2
    exit 1
fi

echo "==> Installiere Git und Systemvoraussetzungen"
sudo apt-get update
sudo apt-get install -y git

echo "==> Klone HomePanel aus GitHub ($BRANCH)"
git clone --branch "$BRANCH" --single-branch "$REPOSITORY_URL" "$INSTALL_DIR"

echo "==> Richte HomePanel ein"
"$INSTALL_DIR/scripts/install.sh"

echo ""
echo "Installation abgeschlossen. Updates installierst du später mit:"
echo "  $INSTALL_DIR/scripts/update-github.sh"