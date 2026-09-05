#!/usr/bin/env bash
# Updates an existing HomePanel checkout from its configured GitHub origin.
# Local source changes are deliberately preserved and block the update.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="homepanel.service"

cd "$APP_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Fehler: $APP_DIR ist keine Git-Arbeitskopie." >&2
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Abbruch: Lokale Codeänderungen wurden erkannt und bleiben geschützt." >&2
    echo "Bitte zuerst committen, sichern oder zurücksetzen; danach erneut ausführen." >&2
    exit 1
fi

BRANCH="$(git branch --show-current)"
if [ -z "$BRANCH" ]; then
    echo "Fehler: Kein lokaler Git-Branch ausgecheckt." >&2
    exit 1
fi

echo "==> Lade Änderungen von origin/$BRANCH"
git fetch --prune origin "$BRANCH"

LOCAL_REVISION="$(git rev-parse HEAD)"
REMOTE_REVISION="$(git rev-parse "origin/$BRANCH")"
if [ "$LOCAL_REVISION" = "$REMOTE_REVISION" ]; then
    echo "HomePanel ist bereits aktuell."
    exit 0
fi

if ! git merge-base --is-ancestor HEAD "origin/$BRANCH"; then
    echo "Abbruch: Der lokale Branch kann nicht sicher per Fast-Forward aktualisiert werden." >&2
    echo "Bitte lokale Commits zuerst mit GitHub abgleichen." >&2
    exit 1
fi

WAS_ACTIVE=false
if systemctl is-active --quiet "$SERVICE_NAME"; then
    WAS_ACTIVE=true
    echo "==> Stoppe $SERVICE_NAME"
    sudo systemctl stop "$SERVICE_NAME"
fi

restart_service() {
    if [ "$WAS_ACTIVE" = true ]; then
        echo "==> Starte $SERVICE_NAME wieder"
        sudo systemctl start "$SERVICE_NAME"
    fi
}
trap restart_service EXIT

echo "==> Aktualisiere Programmcode"
git merge --ff-only "origin/$BRANCH"

echo "==> Aktualisiere Python-Abhängigkeiten"
if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
    python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

echo "==> Aktualisiere systemd-Service"
sudo sed "s#/home/pi/homepanel#$APP_DIR#g; s#User=pi#User=$(whoami)#g" \
    "$APP_DIR/systemd/homepanel.service" | sudo tee "/etc/systemd/system/$SERVICE_NAME" > /dev/null
sudo systemctl daemon-reload

echo "Update auf $(git rev-parse --short HEAD) abgeschlossen."