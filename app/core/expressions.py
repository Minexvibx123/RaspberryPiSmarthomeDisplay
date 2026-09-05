"""Safe, whitelist-only expression templates for the future Custom Widget Builder.

Only a tiny, explicitly allowed subset of Python syntax is evaluated (names,
numeric/string constants, +, -, *, /, unary +/-) plus a small set of filter
functions applied via ``{{ expr | filter(args) }}``. Anything outside this
whitelist raises :class:`ExpressionError` instead of being executed - there is
no ``eval``/``exec`` of arbitrary user-supplied Python code.
"""
from __future__ import annotations

import ast
import operator
import re
from typing import Any


class ExpressionError(ValueError):
    """Raised for any expression that is invalid or outside the safe subset."""


def _to_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ExpressionError(f"'{value}' ist keine Zahl") from None


FILTERS = {
    "round": lambda value, ndigits=0: round(_to_number(value), int(ndigits)),
    "upper": lambda value: str(value).upper(),
    "lower": lambda value: str(value).lower(),
    "int": lambda value: int(_to_number(value)),
    "float": lambda value: float(_to_number(value)),
    "abs": lambda value: abs(_to_number(value)),
}

_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval_node(node: ast.AST, context: dict) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, context)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, float)) or node.value is None:
            return node.value
        raise ExpressionError("Unzulässiger Wert im Ausdruck")
    if isinstance(node, ast.Name):
        if node.id not in context:
            raise ExpressionError(f"Unbekannte Variable '{node.id}'")
        return context[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        if isinstance(node.op, ast.Add) and (isinstance(left, str) or isinstance(right, str)):
            return f"{left}{right}"
        return _BINOPS[type(node.op)](_to_number(left), _to_number(right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_to_number(_eval_node(node.operand, context)))
    raise ExpressionError("Unzulässiger Ausdruck (nur Namen, Zahlen, Text, + - * / erlaubt)")


def eval_expression(expr: str, context: dict) -> Any:
    """Evaluate a single whitelisted expression such as ``state + " °C"``."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"Syntaxfehler: {exc}") from exc
    return _eval_node(tree, context)


def _apply_filter(value: Any, filter_expr: str) -> Any:
    filter_expr = filter_expr.strip()
    name, _, args_str = filter_expr.partition("(")
    name = name.strip()
    if name not in FILTERS:
        raise ExpressionError(f"Unbekannter Filter '{name}'")
    args: list[Any] = []
    args_str = args_str.rstrip(")").strip()
    if args_str:
        tree = ast.parse(f"({args_str},)", mode="eval")
        for element in tree.body.elts:  # type: ignore[attr-defined]
            args.append(_eval_node(element, {}))
    return FILTERS[name](value, *args)


_TEMPLATE_PATTERN = re.compile(r"\{\{(.*?)\}\}")


def render_template(template: str, context: dict) -> str:
    """Render a ``{{ state | round(1) }}``-style template against ``context``."""

    def replace(match: re.Match) -> str:
        parts = match.group(1).split("|")
        value = eval_expression(parts[0].strip(), context)
        for filter_expr in parts[1:]:
            value = _apply_filter(value, filter_expr)
        return str(value)

    return _TEMPLATE_PATTERN.sub(replace, template)
