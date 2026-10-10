from __future__ import annotations

import concurrent.futures
import ipaddress
import json
import re
import subprocess


class NetworkMonitor:
    MAX_HOSTS = 256
    MAX_WORKERS = 32

    def probe(self, host: str) -> dict[str, object]:
        result = subprocess.run(["ping", "-c", "1", "-W", "2", host], capture_output=True, text=True, timeout=3)
        match = re.search(r"time=([\d.]+) ms", result.stdout)
        return {"host": host, "online": result.returncode == 0, "response_ms": float(match.group(1)) if match else None}

    @staticmethod
    def _parse_private_network(cidr: str) -> ipaddress.IPv4Network:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as exc:
            raise ValueError("Bitte ein gültiges IPv4-Netz angeben.") from exc
        if not isinstance(network, ipaddress.IPv4Network):
            raise ValueError("Netzwerkerkennung unterstützt nur IPv4.")
        private_ranges = (
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
        )
        if not any(network.subnet_of(private_range) for private_range in private_ranges):
            raise ValueError("Aus Sicherheitsgründen sind nur private IPv4-Netze erlaubt.")
        if network.num_addresses > NetworkMonitor.MAX_HOSTS:
            raise ValueError("Der Scan ist auf maximal 256 IPv4-Adressen begrenzt (mindestens /24).")
        return network

    @staticmethod
    def local_private_network() -> str:
        """Return the first private IPv4 network on the default-route interface."""
        try:
            routes = subprocess.run(
                ["ip", "-j", "-4", "route", "show", "default"],
                capture_output=True, text=True, timeout=2, check=True,
            )
            route_entries = json.loads(routes.stdout)
            interface = next((entry.get("dev") for entry in route_entries if entry.get("dev")), None)
            if not interface:
                raise RuntimeError
            addresses = subprocess.run(
                ["ip", "-j", "-4", "address", "show", "dev", interface],
                capture_output=True, text=True, timeout=2, check=True,
            )
            for entry in json.loads(addresses.stdout):
                for address in entry.get("addr_info", []):
                    if address.get("scope") != "global":
                        continue
                    network = ipaddress.ip_network(
                        f"{address['local']}/{address['prefixlen']}", strict=False,
                    )
                    return str(NetworkMonitor._parse_private_network(str(network)))
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            pass
        raise RuntimeError("Lokales privates IPv4-Netz nicht automatisch gefunden; CIDR manuell eingeben.")

    @staticmethod
    def _scan_host(address: ipaddress.IPv4Address) -> dict[str, object] | None:
        try:
            result = subprocess.run(
                ["ping", "-n", "-c", "1", "-W", "1", "-q", str(address)],
                capture_output=True, text=True, timeout=1.5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        match = re.search(r"time=([\d.]+) ms", result.stdout)
        try:
            lookup = subprocess.run(
                ["getent", "hosts", str(address)],
                capture_output=True, text=True, timeout=1,
            )
            fields = lookup.stdout.split()
            name = fields[1] if lookup.returncode == 0 and len(fields) > 1 else ""
        except (OSError, subprocess.SubprocessError):
            name = ""
        return {
            "host": str(address),
            "name": name,
            "response_ms": float(match.group(1)) if match else None,
        }

    def discover(self, cidr: str | None = None) -> list[dict[str, object]]:
        """Ping-sweep an explicitly requested private IPv4 subnet (no port scan)."""
        network = self._parse_private_network(cidr or self.local_private_network())
        addresses = list(network.hosts())
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(self.MAX_WORKERS, max(1, len(addresses))),
        ) as pool:
            results = [result for result in pool.map(self._scan_host, addresses) if result]
        return results