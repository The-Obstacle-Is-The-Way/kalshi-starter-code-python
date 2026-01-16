#!/usr/bin/env python3
"""
Detect likely inline mock drift in tests.

This is a heuristic guardrail for DEBT-018: it scans test files for inline JSON dict
literals used in `httpx.Response(..., json=...)` for successful (200) responses and
warns when those payloads are missing required fields for core models.

Why this exists:
- Inline mocks can silently drift away from SSOT fixtures and models.
- Tests may keep passing because they bypass real Pydantic parsing.

This script is intentionally conservative:
- It only inspects inline dict literals (not fixtures loaded from disk).
- It only checks responses with status code 200.
- It only checks a small set of well-known response shapes.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from kalshi_research.api.models.event import Event
from kalshi_research.api.models.market import Market

if TYPE_CHECKING:
    from pydantic import BaseModel


@dataclass(frozen=True)
class DriftFinding:
    filepath: Path
    lineno: int
    message: str


_TEST_ROOT: Final[Path] = Path("tests")


def _required_fields(model: type[BaseModel]) -> set[str]:
    return {name for name, field in model.model_fields.items() if field.is_required()}


_MODEL_REQUIRED_FIELDS: Final[dict[str, set[str]]] = {
    "market": _required_fields(Market),
    "markets": _required_fields(Market),
    "event": _required_fields(Event),
    "events": _required_fields(Event),
}


def _extract_int_constant(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def _status_code_from_response_call(call: ast.Call) -> int | None:
    if call.args:
        status = _extract_int_constant(call.args[0])
        if status is not None:
            return status

    for kw in call.keywords:
        if kw.arg in {"status_code", "status"}:
            status = _extract_int_constant(kw.value)
            if status is not None:
                return status

    return None


def _dict_keys_if_literal(node: ast.Dict) -> set[str] | None:
    if any(key is None for key in node.keys):
        return None
    keys: set[str] = set()
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
        else:
            return None
    return keys


def _find_dict_for_key(node: ast.Dict, key: str) -> ast.Dict | None:
    for k, v in zip(node.keys, node.values, strict=False):
        if isinstance(k, ast.Constant) and k.value == key and isinstance(v, ast.Dict):
            return v
    return None


def _find_list_for_key(node: ast.Dict, key: str) -> ast.List | None:
    for k, v in zip(node.keys, node.values, strict=False):
        if isinstance(k, ast.Constant) and k.value == key and isinstance(v, ast.List):
            return v
    return None


def _missing_required_fields(*, model_key: str, payload_node: ast.AST) -> set[str] | None:
    required = _MODEL_REQUIRED_FIELDS.get(model_key)
    if not required:
        return None

    present: set[str] | None = None

    if isinstance(payload_node, ast.Dict):
        present = _dict_keys_if_literal(payload_node)
    elif isinstance(payload_node, ast.List):
        element_keys: set[str] = set()
        for element in payload_node.elts:
            if not isinstance(element, ast.Dict):
                continue
            element_present = _dict_keys_if_literal(element)
            if element_present is None:
                continue
            element_keys |= element_present

        # Avoid false positives for endpoints that use the same wrapper key but a different element
        # shape (e.g., candlesticks uses "markets" but elements are candlestick bundles).
        if element_keys and (element_keys & required):
            present = element_keys

    if present is None:
        return None

    return required - present


def _inspect_response_call(*, filepath: Path, call: ast.Call) -> list[DriftFinding]:
    status_code = _status_code_from_response_call(call)
    if status_code != 200:
        return []

    json_kw = next((kw for kw in call.keywords if kw.arg == "json"), None)
    if json_kw is None or not isinstance(json_kw.value, ast.Dict):
        return []

    root = json_kw.value
    findings: list[DriftFinding] = []

    for key in sorted(_MODEL_REQUIRED_FIELDS.keys()):
        nested_dict = _find_dict_for_key(root, key)
        if nested_dict is not None:
            missing = _missing_required_fields(model_key=key, payload_node=nested_dict)
            if not missing:
                continue
            missing_str = ", ".join(sorted(missing))
            findings.append(
                DriftFinding(
                    filepath=filepath,
                    lineno=call.lineno,
                    message=f"Inline mock for '{key}' is missing required fields: {missing_str}",
                )
            )
            continue

        nested_list = _find_list_for_key(root, key)
        if nested_list is not None:
            missing = _missing_required_fields(model_key=key, payload_node=nested_list)
            if not missing:
                continue
            missing_str = ", ".join(sorted(missing))
            findings.append(
                DriftFinding(
                    filepath=filepath,
                    lineno=call.lineno,
                    message=(
                        f"Inline mock list for '{key}' is missing required fields: {missing_str}"
                    ),
                )
            )

    return findings


def _find_response_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "Response":
            calls.append(node)
            continue
        if isinstance(fn, ast.Attribute) and fn.attr == "Response":
            calls.append(node)
    return calls


def _iter_test_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("test_*.py"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect likely inline mock drift in tests.")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Exit 0 even if drift is detected (still prints findings).",
    )
    args = parser.parse_args(argv)

    findings: list[DriftFinding] = []

    for filepath in _iter_test_files(_TEST_ROOT):
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for call in _find_response_calls(tree):
            findings.extend(_inspect_response_call(filepath=filepath, call=call))

    if not findings:
        print("✅ No inline mock drift findings")
        return 0

    print(f"⚠️  Inline mock drift findings: {len(findings)}")
    for finding in findings:
        rel = finding.filepath.as_posix()
        print(f"  - {rel}:{finding.lineno}: {finding.message}")

    if args.warn_only:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
