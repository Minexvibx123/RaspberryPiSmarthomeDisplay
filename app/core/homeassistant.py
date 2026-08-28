"""Minimal, synchronous Home Assistant REST API client.

Used for one-shot calls (initial entity load, service calls, connection
test). Live state updates flow through the WebSocket client instead.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    entity_id: str
    state: str
    attributes: dict
    domain: str = ""

    def __post_init__(self):
        if not self.domain:
            self.domain = self.entity_id.split(".")[0]

    @property
    def friendly_name(self) -> str:
        return self.attributes.get("friendly_name", self.entity_id)

    @property
    def area(self) -> str:
        return self.attributes.get("area", "") or self.attributes.get("room", "")


class HomeAssistantAPIError(Exception):
    pass


class HomeAssistantClient:
    def __init__(self, base_url: str, token: str, timeout: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def test_connection(self) -> tuple[bool, str]:
        try:
            resp = requests.get(f"{self.base_url}/api/", headers=self._headers, timeout=self.timeout)
            if resp.status_code == 401:
                return False, "Ungültiges Zugriffstoken"
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"
            return True, "OK"
        except requests.exceptions.ConnectionError:
            return False, "Server nicht erreichbar"
        except requests.exceptions.Timeout:
            return False, "Zeitüberschreitung"
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unexpected error during connection test")
            return False, str(exc)

    def get_states(self) -> list[Entity]:
        resp = requests.get(f"{self.base_url}/api/states", headers=self._headers, timeout=self.timeout)
        resp.raise_for_status()
        return [Entity(e["entity_id"], e["state"], e.get("attributes", {})) for e in resp.json()]

    def get_state(self, entity_id: str) -> Optional[Entity]:
        resp = requests.get(f"{self.base_url}/api/states/{entity_id}", headers=self._headers, timeout=self.timeout)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        e = resp.json()
        return Entity(e["entity_id"], e["state"], e.get("attributes", {}))

    def call_service(self, domain: str, service: str, entity_id: Optional[str] = None, **data: Any) -> None:
        payload = dict(data)
        if entity_id:
            payload["entity_id"] = entity_id
        resp = requests.post(
            f"{self.base_url}/api/services/{domain}/{service}",
            headers=self._headers, json=payload, timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise HomeAssistantAPIError(f"{domain}.{service} failed: HTTP {resp.status_code}")

    def get_config(self) -> dict:
        resp = requests.get(f"{self.base_url}/api/config", headers=self._headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_logbook(self, start_time: str, entity_id: Optional[str] = None) -> list[dict]:
        params = {"start_time": start_time}
        if entity_id:
            params["entity_id"] = entity_id
        resp = requests.get(
            f"{self.base_url}/api/logbook", headers=self._headers, params=params, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()
