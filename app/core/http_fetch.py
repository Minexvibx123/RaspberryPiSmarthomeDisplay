"""Lightweight background HTTP fetch helper for internet-connected widgets.

Every request runs in its own short-lived QThread so a slow or unreachable
API can never block touch input or freeze the panel. Widgets receive
results back via plain Python callbacks invoked on the Qt main thread
(through Qt's signal/slot queued-connection mechanism).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import requests
from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 6.0

# Keeps a strong reference to every in-flight request. Without this, nothing
# would own the returned _FetchThread once fetch() returns, and Python could
# garbage-collect it while its background OS thread is still running - which
# Qt treats as fatal (process abort), not just a Python exception.
_ACTIVE_THREADS: set["_FetchThread"] = set()


class _FetchThread(QThread):
    finished_ok = Signal(object)
    finished_error = Signal(str)

    def __init__(self, url: str, params: Optional[dict], headers: Optional[dict], as_json: bool):
        super().__init__()
        self.url = url
        self.params = params
        self.headers = headers
        self.as_json = as_json

    def run(self) -> None:
        try:
            resp = requests.get(self.url, params=self.params, headers=self.headers, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            self.finished_ok.emit(resp.json() if self.as_json else resp.text)
        except Exception as exc:  # noqa: BLE001 - any network/parse failure is reported, never raised
            logger.debug("Background fetch failed for %s: %s", self.url, exc)
            self.finished_error.emit(str(exc))


def _guard(callback: Callable) -> Callable:
    """Swallow RuntimeError from calling into an already-deleted Qt widget."""

    def wrapper(*args):
        try:
            callback(*args)
        except RuntimeError:
            logger.debug("Ignoring fetch callback for a widget that was already removed")

    return wrapper


def fetch(
    url: str,
    on_success: Callable[[Any], None],
    on_error: Optional[Callable[[str], None]] = None,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    as_json: bool = True,
    parent: Optional[QObject] = None,
) -> _FetchThread:
    """Fire off a background GET request; callbacks run on the Qt main thread.

    The thread is intentionally NOT made a Qt child of `parent` (e.g. the
    requesting widget): if the widget gets deleted while a request is still
    in flight, a parented QThread would be destroyed mid-run, which Qt
    treats as fatal (aborts the whole process). Instead the thread manages
    its own lifetime and self-deletes once finished, while callbacks are
    guarded against being invoked on an already-deleted widget.
    """
    thread = _FetchThread(url, params, headers, as_json)
    thread.finished_ok.connect(_guard(on_success))
    if on_error:
        thread.finished_error.connect(_guard(on_error))
    _ACTIVE_THREADS.add(thread)
    thread.finished.connect(lambda: _ACTIVE_THREADS.discard(thread))
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread
