#!/usr/bin/env bash
# HomePanel Kiosk-Session – wird von der tty1-Autologin-Shell gestartet.
#
# Warum nicht systemd+PAMName: logind vergibt den DRM-Seat nur zuverlaessig
# an eine echte Login-Sitzung am Konsolen-TTY. Die klassische Losung ist
# Autologin auf tty1 + cage direkt in dieser Sitzung.
set -u
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export QT_QPA_PLATFORM=wayland
export PYTHONUNBUFFERED=1
# WAYLAND_DISPLAY wird von cage selbst fuer Clients gesetzt

# Logs auf die Konsole wuerden hinter/auf dem Panel erscheinen -> Datei
exec >> "$HOME/kiosk.log" 2>&1

log() { echo "[kiosk-session] $(date '+%H:%M:%S') $*"; }
log "starte Kiosk-Session (cage am DSI-Display)"

while true; do
    /usr/bin/cage -d -- "$APP_DIR/.venv/bin/python" -m app.main &
    CAGE_PID=$!

    # Auf den Wayland-Socket warten und Landscape-Rotation (270°) setzen.
    i=0
    until XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" WAYLAND_DISPLAY=wayland-0 \
          wlr-randr --output DSI-1 --transform 270 2>/dev/null; do
        i=$((i+1))
        sleep 1
        [ $i -ge 20 ] && { log "Rotation konnte nicht gesetzt werden"; break; }
    done

    # Blockieren, solange cage laeuft
    wait "$CAGE_PID"
    RC=$?
    log "cage beendet (RC=$RC) – Neustart in 3 s"
    sleep 3
done