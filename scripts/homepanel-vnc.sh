#!/usr/bin/env bash
# HomePanel Browser-View: zweite Instanz auf virtuellem Display (Xvfb),
# ausgeliefert ueber x11vnc + noVNC (WebSocket) im LAN.
# URL: http://<pi-ip>:6080/vnc.html
set -u
export DISPLAY=:1
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

LOG=/tmp/opencode/homepanel-vnc
mkdir -p /tmp/opencode

Xvfb :1 -screen 0 1024x600x24 -nolisten tcp > "$LOG.xvfb.log" 2>&1 &
XVFB_PID=$!

cleanup() {
    kill "$WS_PID" "$VNC_PID" "$APP_PID" "$XVFB_PID" 2>/dev/null || true
}
trap 'cleanup' EXIT TERM INT

# Auf X-Server warten (max ~10 s)
for _ in $(seq 1 50); do
    if xset -display :1 q >/dev/null 2>&1; then break; fi
    sleep 0.2
done

"$APP_DIR/.venv/bin/python" -m app.main --windowed > "$LOG.app.log" 2>&1 &
APP_PID=$!

x11vnc -display :1 -localhost -nopw -forever -shared -rfbport 5900 > "$LOG.x11vnc.log" 2>&1 &
VNC_PID=$!

websockify --web=/usr/share/novnc 6080 localhost:5900 > "$LOG.websockify.log" 2>&1 &
WS_PID=$!

# Warten, bis die Panel-Instanz endet (dann raeumen wir auf)
wait "$APP_PID"
echo "HomePanel VNC-Instanz beendet (RC=$?)"