"""Ingest motor policy rules into Qdrant.

Run with: `make ingest` or `uv run python -m scripts.ingest_policy`.
"""
from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console

from app.rag.ingest import DEFAULT_COLLECTION, ingest

console = Console()

POLICY_PATH = Path(__file__).parent.parent / "data" / "policies" / "motor_policy.md"


def main() -> int:
    console.rule("Ingesting policy")
    console.print(f"[dim]Source:[/dim] {POLICY_PATH}")
    if not POLICY_PATH.exists():
        console.print(f"[red]Policy file not found: {POLICY_PATH}[/red]")
        return 1
    try:
        count = ingest(POLICY_PATH)
        console.print(
            f"[green]Ingested {count} clauses into collection "
            f"[bold]{DEFAULT_COLLECTION}[/bold][/green]"
        )
        return 0
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Ingestion failed: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
