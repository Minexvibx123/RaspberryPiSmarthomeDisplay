"""Central service/API registry.

HomePanel is growing from a single back-end hub (StateManager) into a modular
platform. The ServiceRegistry is the seam plugins use to look up the services
they need (database, settings, state manager, ...) and to offer their own
services to other plugins. It is intentionally small and dependency-free.

Core services are registered once at application startup in
``MainWindow._start_runtime``; plugins receive a reference to the registry and
use ``resolve()`` instead of hard-wiring imports.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Resolve services by name. Missing services raise a clear KeyError."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any, replace: bool = False) -> None:
        """Register a service under ``name``.

        A service may only be registered once unless ``replace`` is True -
        duplicate registrations are usually a wiring bug and are surfaced
        loudly instead of silently overwriting something.
        """
        if name in self._services and not replace:
            raise KeyError(f"Service '{name}' is already registered")
        self._services[name] = service
        logger.debug("Registered service '%s'", name)

    def resolve(self, name: str) -> Any:
        """Return the service registered under ``name``."""
        if name not in self._services:
            raise KeyError(f"No service registered as '{name}'")
        return self._services[name]

    def get(self, name: str) -> Optional[Any]:
        """Like :meth:`resolve` but returns None instead of raising."""
        return self._services.get(name)

    def names(self) -> list[str]:
        """Names of all registered services."""
        return list(self._services.keys())

    def registered(self, name: str) -> bool:
        return name in self._services
