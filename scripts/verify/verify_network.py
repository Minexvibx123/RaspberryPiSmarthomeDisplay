"""Offline verification for the network plugin discovery API."""
from __future__ import annotations

import ipaddress
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from plugins.network.api import NetworkMonitor  # noqa: E402


def check_rejected(cidr: str) -> None:
    try:
        NetworkMonitor._parse_private_network(cidr)
    except ValueError:
        return
    raise AssertionError(f"Unsafe or oversized network was accepted: {cidr}")


assert str(NetworkMonitor._parse_private_network("192.168.178.138/24")) == "192.168.178.0/24"
assert str(NetworkMonitor._parse_private_network("10.1.2.3/32")) == "10.1.2.3/32"
check_rejected("8.8.8.0/24")
check_rejected("192.168.0.0/23")
check_rejected("fd00::/64")

route = subprocess.CompletedProcess(
    ["ip"], 0, json.dumps([{"dev": "wlan0", "dst": "default"}]), "",
)
addresses = subprocess.CompletedProcess(
    ["ip"], 0,
    json.dumps([{"addr_info": [{"scope": "global", "local": "192.168.178.138", "prefixlen": 24}]}]),
    "",
)
with patch("plugins.network.api.subprocess.run", side_effect=[route, addresses]):
    assert NetworkMonitor.local_private_network() == "192.168.178.0/24"

monitor = NetworkMonitor()
with patch.object(
    NetworkMonitor, "_scan_host",
    side_effect=lambda address: {"host": str(address), "name": "", "response_ms": None},
):
    results = monitor.discover("192.168.178.0/30")
assert [item["host"] for item in results] == ["192.168.178.1", "192.168.178.2"]

with patch(
    "plugins.network.api.subprocess.run",
    side_effect=[
        subprocess.CompletedProcess([], 0, "64 bytes time=2.3 ms", ""),
        subprocess.CompletedProcess([], 0, "192.168.178.2 device.local\n", ""),
    ],
):
    result = monitor._scan_host(ipaddress.IPv4Address("192.168.178.2"))
assert result == {"host": "192.168.178.2", "name": "device.local", "response_ms": 2.3}

print("VERIFICATION PASSED")