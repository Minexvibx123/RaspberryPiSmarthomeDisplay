"""Verification for the safe conditional visibility/styling evaluator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.conditions import matches_condition  # noqa: E402


CASES = [
    ("on", "equals", "on", True),
    ("off", "not_equals", "on", True),
    ("31.5", "greater_than", "30", True),
    ("25", "less_than", "30", True),
    ("printing", "contains", "print", True),
    ("unavailable", "online", "", False),
    ("connected", "online", "", True),
    ("offline", "offline", "", True),
    ("on", "true", "", True),
    ("off", "false", "", True),
    ("not-a-number", "greater_than", "5", False),
]

failures = []
for value, operator, expected, result in CASES:
    actual = matches_condition(value, operator, expected)
    if actual != result:
        failures.append((value, operator, expected, actual, result))

if failures:
    print(f"VERIFICATION FAILED: {failures}")
    sys.exit(1)
print("VERIFICATION PASSED")