"""Background Home Assistant WebSocket client with automatic reconnection.

Runs in its own QThread so the UI never blocks. Emits Qt signals that the
StateManager (and ultimately widgets) subscribe to. Designed to be resilient:
a dropped connection never crashes or freezes the panel - it just keeps
retrying with backoff and reports its status.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal
from websocket import WebSocketApp

logger = logging.getLogger(__name__)

RECONNECT_MIN_DELAY = 2
RECONNECT_MAX_DELAY = 30


class HomeAssistantWebSocket(QObject):
    """Public API - lives on the main thread, delegates work to a QThread."""

    connected = Signal()
    disconnected = Signal(str)  # reason
    state_changed = Signal(str, dict)  # entity_id, new state dict
    connection_status = Signal(bool)

    def __init__(self, base_url: str, token: str):
        super().__init__()
        self.base_url = base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
        self.token = token
        self._thread: Optional[_WebSocketThread] = None

    def start(self) -> None:
        if self._thread and self._thread.isRunning():
            return
        self._thread = _WebSocketThread(f"{self.base_url}/api/websocket", self.token)
        self._thread.connected.connect(self.connected.emit)
        self._thread.disconnected.connect(self.disconnected.emit)
        self._thread.state_changed.connect(self.state_changed.emit)
        self._thread.connection_status.connect(self.connection_status.emit)
        self._thread.start()

    def stop(self) -> None:
        if self._thread:
            self._thread.stop()
            self._thread.wait(3000)
            self._thread = None


class _WebSocketThread(QThread):
    connected = Signal()
    disconnected = Signal(str)
    state_changed = Signal(str, dict)
    connection_status = Signal(bool)

    def __init__(self, url: str, token: str):
        super().__init__()
        self.url = url
        self.token = token
        self._stop_requested = False
        self._ws: Optional[WebSocketApp] = None
        self._msg_id = 1

    def stop(self) -> None:
        self._stop_requested = True
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    def run(self) -> None:
        delay = RECONNECT_MIN_DELAY
        while not self._stop_requested:
            try:
                self._run_once()
            except Exception:
                logger.exception("WebSocket loop error")
            if self._stop_requested:
                break
            self.connection_status.emit(False)
            self.disconnected.emit("reconnecting")
            time.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX_DELAY)
        logger.info("WebSocket thread stopped")

    def _run_once(self) -> None:
        self._ws = WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._ws.run_forever(ping_interval=20, ping_timeout=10)

    # -- websocket-client callbacks (run on this thread) ------------------ #
    def _on_open(self, _ws) -> None:
        logger.info("WebSocket connection opened, awaiting auth challenge")

    def _on_message(self, _ws, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return
        msg_type = data.get("type")
        if msg_type == "auth_required":
            self._ws.send(json.dumps({"type": "auth", "access_token": self.token}))
        elif msg_type == "auth_ok":
            self.connection_status.emit(True)
            self.connected.emit()
            self._subscribe()
        elif msg_type == "auth_invalid":
            logger.error("Home Assistant rejected the access token")
            self._ws.close()
        elif msg_type == "event":
            event = data.get("event", {})
            if event.get("event_type") == "state_changed":
                new_state = event["data"].get("new_state")
                if new_state:
                    self.state_changed.emit(new_state["entity_id"], new_state)

    def _on_error(self, _ws, error) -> None:
        logger.warning("WebSocket error: %s", error)

    def _on_close(self, _ws, _status, _msg) -> None:
        logger.info("WebSocket connection closed")

    def _subscribe(self) -> None:
        self._msg_id += 1
        self._ws.send(json.dumps({"id": self._msg_id, "type": "subscribe_events", "event_type": "state_changed"}))
