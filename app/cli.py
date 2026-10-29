"""CLI entry point: run a single claim case through the triage agent.

Usage:
    uv run python -m app.cli --case data/test_cases/case1_parked_car.json
    make demo CASE=case1_parked_car
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.agents.triage import TriageAgent
from app.schemas import ClaimInput, TriageOutput

console = Console()


def _render_output(output: TriageOutput) -> None:
    console.print(Panel(output.claim_summary, title="Claim summary", border_style="cyan"))

    tbl = Table(show_header=False, box=None, pad_edge=False)
    tbl.add_column(style="bold")
    tbl.add_column()
    tbl.add_row("Coverage:", output.coverage_assessment)
    tbl.add_row("Routing:", output.recommended_routing)
    tbl.add_row("Confidence:", output.confidence_level)
    tbl.add_row("Cited clauses:", ", ".join(output.cited_clauses) or "-")
    console.print(tbl)

    missing = "\n".join(f"• {x}" for x in output.missing_information) or "(none)"
    console.print(Panel(missing, title="Missing information", border_style="yellow"))

    risks = "\n".join(f"• {x}" for x in output.risk_flags) or "(none)"
    console.print(Panel(risks, title="Risk flags", border_style="red"))

    console.print(Panel(output.reasoning, title="Reasoning", border_style="green"))


def run_case(case_path: Path) -> TriageOutput:
    data = json.loads(case_path.read_text(encoding="utf-8"))
    claim = ClaimInput.model_validate(data)

    console.rule(f"Running triage on {claim.claim_id}")
    agent = TriageAgent()
    with console.status("[dim]Retrieving policy + calling Claude Sonnet...[/dim]"):
        result = agent.run(claim)

    _render_trace(result)
    console.print()
    _render_output(result.output)
    return result.output


def _render_trace(result) -> None:
    """Visual timeline of the pipeline stages, mirrors the Streamlit UI."""
    console.rule(
        f"[bold]Pipeline execution trace[/bold] · "
        f"total [cyan]{result.latency_ms} ms[/cyan]"
    )
    max_ms = max((s.duration_ms for s in result.trace), default=1) or 1
    tbl = Table(show_header=False, box=None, pad_edge=False)
    tbl.add_column(justify="right", style="dim", width=2)
    tbl.add_column(width=4)
    tbl.add_column(style="bold")
    tbl.add_column(justify="right", style="cyan", width=10)
    tbl.add_column()
    for step in result.trace:
        bar_len = max(1, int(step.duration_ms / max_ms * 24))
        color = {"ok": "green", "warn": "yellow", "info": "blue"}.get(step.status, "white")
        tbl.add_row(
            str(step.index),
            step.icon,
            step.name,
            f"{step.duration_ms:>5} ms",
            f"[{color}]{'█' * bar_len}[/{color}] [dim]{step.details[:60]}[/dim]",
        )
    console.print(tbl)


def main() -> int:
    parser = argparse.ArgumentParser(description="Motor claim triage CLI")
    parser.add_argument(
        "--case",
        type=Path,
        required=True,
        help="Path to a claim case JSON file (see data/test_cases/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON output instead of the rich-rendered view",
    )
    args = parser.parse_args()

    if not args.case.exists():
        console.print(f"[red]Case file not found: {args.case}[/red]")
        return 1

    output = run_case(args.case)
    if args.json:
        console.print_json(output.model_dump_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
