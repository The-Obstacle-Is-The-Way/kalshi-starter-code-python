#!/usr/bin/env python3
"""
Validate Pydantic models against recorded golden fixtures.

This script compares what our models expect vs what the API actually returns.
It identifies:
1. Fields in API response that our model doesn't have (unexpected fields)
2. Fields our model requires that API doesn't send (missing required fields)
3. Fields our model has as optional that API always sends (could be required)
4. Type mismatches between model and actual data

Usage:
    # First, record golden fixtures:
    uv run python scripts/record_api_responses.py

    # Then validate models:
    uv run python scripts/validate_models_against_golden.py

Output:
    Console report of all mismatches found

Note:
    This is a diagnostic tool - it reports findings but does not modify code.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Final, get_args, get_origin

from kalshi_research.api.models.event import Event
from kalshi_research.api.models.market import Market
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.api.models.portfolio import (
    Fill,
    Order,
    PortfolioBalance,
    PortfolioPosition,
    Settlement,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

GOLDEN_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "golden"

JsonDict = dict[str, Any]

# Regex pattern for extracting choices from AliasChoices string representation
_ALIAS_CHOICES_PATTERN: Final[re.Pattern[str]] = re.compile(r"'([^']+)'")

MODEL_MAPPING: Final[dict[str, tuple[str, type[BaseModel]]]] = {
    # Public endpoints
    # GET /markets/{ticker} returns {"market": {...}}
    "market_single_response.json": ("response.market", Market),
    "markets_list_response.json": ("response.markets[0]", Market),
    # GET /events/{event_ticker} returns {"event": {...}, "markets": [...]}
    "event_single_response.json": ("response.event", Event),
    "events_list_response.json": ("response.events[0]", Event),
    # GET /markets/{ticker}/orderbook returns {"orderbook": {...}}
    "orderbook_response.json": ("response.orderbook", Orderbook),
    # Note: exchange_status_response returns dict, not a model (skipped)
    # Portfolio endpoints
    "portfolio_balance_response.json": ("response", PortfolioBalance),
    # GET /portfolio/positions returns market_positions + event_positions
    "portfolio_positions_response.json": ("response.market_positions[0]", PortfolioPosition),
    "portfolio_orders_response.json": ("response.orders[0]", Order),
    "portfolio_fills_response.json": ("response.fills[0]", Fill),
    "portfolio_settlements_response.json": ("response.settlements[0]", Settlement),
    # Trading endpoints - API returns full Order object wrapped in {"order": {...}}
    # Note: OrderResponse is minimal (order_id, order_status); Order has full details
    "create_order_response.json": ("response.order", Order),
    "cancel_order_response.json": ("response.order", Order),
    "amend_order_response.json": ("response.order", Order),
}


def get_nested_value(data: JsonDict, path: str) -> Any:
    """Extract value from nested dict using dot notation with array support."""
    parts = path.split(".")
    current: Any = data

    for part in parts:
        if "[" in part:
            # Handle array access like "markets[0]"
            key, idx_str = part.rstrip("]").split("[")
            idx = int(idx_str)
            current = current[key][idx]
        else:
            current = current[part]

    return current


def get_model_field_info(model: type[BaseModel]) -> dict[str, dict[str, Any]]:
    """Extract field information from Pydantic model."""
    fields = {}
    for name, field_info in model.model_fields.items():
        annotation = field_info.annotation

        # Check if optional (Union[..., None]); also handle Annotated[T, ...]
        origin = get_origin(annotation)
        if origin is Annotated:
            annotated_args = get_args(annotation)
            if annotated_args:
                annotation = annotated_args[0]

        args = get_args(annotation)
        is_optional = type(None) in args

        # Get the base type
        base_type = annotation
        if is_optional:
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                base_type = non_none_args[0]

        fields[name] = {
            "type": str(base_type),
            "required": field_info.is_required(),
            "optional": is_optional,
            "default": field_info.default if field_info.default is not None else "None",
            "alias": field_info.alias,
            "validation_alias": (
                str(field_info.validation_alias) if field_info.validation_alias else None
            ),
        }

    return fields


def _extract_alias_to_field_map(model_fields: dict[str, dict[str, Any]]) -> dict[str, str]:
    alias_to_field: dict[str, str] = {}
    for fname, finfo in model_fields.items():
        alias_str = finfo.get("validation_alias")
        if not alias_str or "AliasChoices" not in alias_str:
            continue
        for alias in _ALIAS_CHOICES_PATTERN.findall(alias_str):
            alias_to_field[alias] = fname
    return alias_to_field


def _required_present_via_alias(
    *,
    field_name: str,
    field_info: dict[str, Any],
    alias_to_field: dict[str, str],
    response_fields: set[str],
) -> bool:
    alias_str = field_info.get("validation_alias")
    if not alias_str:
        return False
    for alias, mapped in alias_to_field.items():
        if mapped == field_name and alias in response_fields:
            return True
    return False


def analyze_response(
    golden_data: JsonDict,
    model: type[BaseModel],
    fixture_name: str,
) -> JsonDict:
    """Analyze differences between golden fixture and Pydantic model."""
    model_fields = get_model_field_info(model)
    response_fields = set(golden_data.keys())
    model_field_names = set(model_fields.keys())

    alias_to_field = _extract_alias_to_field_map(model_fields)

    # Check for unexpected fields (in response but not in model)
    unexpected = response_fields - model_field_names - set(alias_to_field.keys())

    # Check for missing required fields
    missing_required = [
        fname
        for fname, finfo in model_fields.items()
        if finfo["required"]
        and fname not in response_fields
        and not _required_present_via_alias(
            field_name=fname,
            field_info=finfo,
            alias_to_field=alias_to_field,
            response_fields=response_fields,
        )
    ]

    # Check optional fields that are always present (could upgrade to required)
    optional_but_present = []
    for fname, finfo in model_fields.items():
        if finfo["optional"] and fname in response_fields:
            value = golden_data.get(fname)
            if value is not None:
                optional_but_present.append((fname, type(value).__name__))

    # Try to validate the model
    validation_error = None
    try:
        model.model_validate(golden_data)
    except Exception as e:
        validation_error = str(e)

    return {
        "fixture": fixture_name,
        "model": model.__name__,
        "response_fields": sorted(response_fields),
        "model_fields": sorted(model_field_names),
        "unexpected_fields": sorted(unexpected),
        "missing_required": missing_required,
        "optional_but_present": optional_but_present,
        "validation_error": validation_error,
        "fields_match": (
            len(unexpected) == 0 and len(missing_required) == 0 and validation_error is None
        ),
    }


def print_report(results: list[dict[str, Any]]) -> None:
    """Print validation report."""
    print("\n" + "=" * 70)
    print("MODEL VALIDATION REPORT")
    print("=" * 70)

    issues_found = False

    for result in results:
        fixture = result["fixture"]
        model = result["model"]

        if result["fields_match"]:
            print(f"\n{fixture} -> {model}")
            print("  Status: OK")
            continue

        issues_found = True
        print(f"\n{fixture} -> {model}")
        print("  Status: ISSUES FOUND")

        if result["validation_error"]:
            print("\n  VALIDATION ERROR:")
            print(f"    {result['validation_error'][:200]}...")

        if result["unexpected_fields"]:
            print("\n  UNEXPECTED FIELDS (in API, not in model):")
            for field in result["unexpected_fields"]:
                print(f"    - {field}")

        if result["missing_required"]:
            print("\n  MISSING REQUIRED (model requires, API doesn't send):")
            for field in result["missing_required"]:
                print(f"    - {field}")

        if result["optional_but_present"]:
            print("\n  OPTIONAL BUT ALWAYS PRESENT (consider making required):")
            for field, ftype in result["optional_but_present"][:10]:
                print(f"    - {field}: {ftype}")
            if len(result["optional_but_present"]) > 10:
                print(f"    ... and {len(result['optional_but_present']) - 10} more")

    print("\n" + "=" * 70)
    if issues_found:
        print("RESULT: ISSUES FOUND - Models may not match API reality")
        print("=" * 70)
    else:
        print("RESULT: ALL MODELS MATCH GOLDEN FIXTURES")
        print("=" * 70)


def main() -> None:
    if not GOLDEN_DIR.exists():
        print(f"ERROR: Golden fixtures directory not found: {GOLDEN_DIR}")
        print("Run 'uv run python scripts/record_api_responses.py' first")
        sys.exit(1)

    results: list[dict[str, Any]] = []

    for fixture_file, (path, model) in MODEL_MAPPING.items():
        fixture_path = GOLDEN_DIR / fixture_file

        if not fixture_path.exists():
            print(f"SKIP: {fixture_file} (not recorded yet)")
            continue

        try:
            data: JsonDict = json.loads(fixture_path.read_text())
            response_data = get_nested_value(data, path)

            if response_data is None:
                print(f"SKIP: {fixture_file} (empty response)")
                continue

            result = analyze_response(response_data, model, fixture_file)
            results.append(result)

        except (KeyError, IndexError, TypeError) as e:
            print(f"SKIP: {fixture_file} (path error: {e})")
            continue
        except json.JSONDecodeError as e:
            print(f"SKIP: {fixture_file} (JSON error: {e})")
            continue

    if results:
        print_report(results)
    else:
        print("\nNo fixtures found to validate.")
        print("Run 'uv run python scripts/record_api_responses.py' first")


if __name__ == "__main__":
    main()
