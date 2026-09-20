"""Verification for the safe whitelist-only expression/template engine."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.expressions import ExpressionError, render_template  # noqa: E402

CASES = [
    ("{{ state }}", {"state": "23.4"}, "23.4"),
    ("{{ state | round(1) }}", {"state": 23.44}, "23.4"),
    ("{{ state + \" °C\" }}", {"state": "23.4"}, "23.4 °C"),
    ("{{ state | upper }}", {"state": "printing"}, "PRINTING"),
]

failures = []
for template, context, expected in CASES:
    actual = render_template(template, context)
    if actual != expected:
        failures.append((template, expected, actual))

DANGEROUS = [
    "__import__('os').system('id')",
    "().__class__.__mro__[1].__subclasses__()",
    "open('/etc/passwd').read()",
    "state.__class__",
    "[x for x in range(3)]",
]
for expr in DANGEROUS:
    try:
        render_template("{{ " + expr + " }}", {"state": "1"})
        failures.append((expr, "ExpressionError", "no error raised"))
    except ExpressionError:
        pass

if failures:
    print(f"VERIFICATION FAILED: {failures}")
    sys.exit(1)
print("VERIFICATION PASSED")
