#!/usr/bin/env bash
# Manual kiosk launcher (useful for testing without systemd/eglfs).
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
xset s off || true
xset -dpms || true
xset s noblank || true

"$APP_DIR/.venv/bin/python" -m app.main
