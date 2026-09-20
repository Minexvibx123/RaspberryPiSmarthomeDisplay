"""Smoke test for the local system monitoring API."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent
api_path = root / "plugins" / "system_monitor" / "api.py"
spec = importlib.util.spec_from_file_location("system_monitor_api", api_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
snapshot = module.metrics.snapshot()
assert 0 <= snapshot["cpu_percent"] <= 100
assert 0 <= snapshot["memory_percent"] <= 100
assert 0 <= snapshot["storage_percent"] <= 100
assert snapshot["memory_total"] > 0
assert snapshot["storage_total"] > 0
print("VERIFICATION PASSED")