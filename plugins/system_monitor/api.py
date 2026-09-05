"""Local Linux system metrics without external dependencies."""
from __future__ import annotations

import os
from pathlib import Path


class SystemMetrics:
    def __init__(self) -> None:
        self._cpu_previous: tuple[int, int] | None = None
        self._network_previous: tuple[int, int] | None = None

    def snapshot(self) -> dict[str, float | None]:
        cpu_total, cpu_idle = self._cpu_times()
        cpu_percent = 0.0
        if self._cpu_previous:
            total_delta = cpu_total - self._cpu_previous[0]
            idle_delta = cpu_idle - self._cpu_previous[1]
            if total_delta > 0:
                cpu_percent = round(100 * (1 - idle_delta / total_delta), 1)
        self._cpu_previous = (cpu_total, cpu_idle)

        memory_total, memory_available = self._memory()
        storage = os.statvfs("/")
        storage_total = storage.f_blocks * storage.f_frsize
        storage_available = storage.f_bavail * storage.f_frsize
        received, sent = self._network_bytes()
        down_rate = up_rate = 0.0
        if self._network_previous:
            down_rate = max(0, received - self._network_previous[0])
            up_rate = max(0, sent - self._network_previous[1])
        self._network_previous = (received, sent)
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": round(100 * (1 - memory_available / memory_total), 1) if memory_total else 0.0,
            "memory_used": memory_total - memory_available,
            "memory_total": memory_total,
            "storage_percent": round(100 * (1 - storage_available / storage_total), 1) if storage_total else 0.0,
            "storage_used": storage_total - storage_available,
            "storage_total": storage_total,
            "temperature": self._temperature(),
            "download_rate": down_rate,
            "upload_rate": up_rate,
        }

    @staticmethod
    def _cpu_times() -> tuple[int, int]:
        fields = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
        values = [int(value) for value in fields]
        return sum(values), values[3] + (values[4] if len(values) > 4 else 0)

    @staticmethod
    def _memory() -> tuple[int, int]:
        values = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.split()[0]) * 1024
        return values.get("MemTotal", 0), values.get("MemAvailable", values.get("MemFree", 0))

    @staticmethod
    def _network_bytes() -> tuple[int, int]:
        received = sent = 0
        for line in Path("/proc/net/dev").read_text(encoding="utf-8").splitlines()[2:]:
            _interface, values = line.split(":", 1)
            fields = values.split()
            received += int(fields[0])
            sent += int(fields[8])
        return received, sent

    @staticmethod
    def _temperature() -> float | None:
        for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
            try:
                return int(path.read_text(encoding="utf-8").strip()) / 1000
            except (OSError, ValueError):
                continue
        return None


metrics = SystemMetrics()