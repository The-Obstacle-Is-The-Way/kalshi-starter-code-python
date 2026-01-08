import json
import uuid
from pathlib import Path
from typing import Any, cast

import typer
from rich.console import Console

console = Console()


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp.{uuid.uuid4().hex}")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp_path.replace(path)


def load_json_storage_file(*, path: Path, kind: str, required_list_key: str) -> dict[str, Any]:
    if not path.exists():
        return {required_list_key: []}

    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError:
        console.print(f"[red]Error:[/red] {kind} file is not valid JSON: {path}")
        console.print("[dim]Fix the file or restore from backup.[/dim]")
        console.print("[dim]This command will not modify it.[/dim]")
        raise typer.Exit(1) from None

    if not isinstance(raw, dict):
        console.print(f"[red]Error:[/red] {kind} file must contain a JSON object: {path}")
        raise typer.Exit(1) from None

    if required_list_key not in raw or not isinstance(raw[required_list_key], list):
        console.print(
            f"[red]Error:[/red] {kind} file has an unexpected schema: {path} "
            f"(expected key '{required_list_key}: [...]')"
        )
        raise typer.Exit(1) from None

    return cast("dict[str, Any]", raw)
