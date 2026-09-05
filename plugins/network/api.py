from __future__ import annotations

import re
import subprocess


class NetworkMonitor:
    def probe(self, host: str) -> dict[str, object]:
        result = subprocess.run(["ping", "-c", "1", "-W", "2", host], capture_output=True, text=True, timeout=3)
        match = re.search(r"time=([\d.]+) ms", result.stdout)
        return {"host": host, "online": result.returncode == 0, "response_ms": float(match.group(1)) if match else None}