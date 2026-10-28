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

    console.print(
        f"[dim]Retrieved {len(result.retrieved)} policy chunks: "
        f"{', '.join(c.clause_id for c in result.retrieved)}[/dim]"
    )
    if result.input_guard.pii_triggers:
        console.print(
            f"[yellow]Input guard masked PII: "
            f"{', '.join(set(t.split(':')[0] for t in result.input_guard.pii_triggers))}[/yellow]"
        )
    if result.output_guard_triggers:
        console.print(
            f"[yellow]Output guard triggered: {', '.join(result.output_guard_triggers)}[/yellow]"
        )
    console.print(f"[dim]Latency: {result.latency_ms} ms  "
                  f"Audit: data/audit_logs/{result.audit.session_id}.json[/dim]\n")
    _render_output(result.output)
    return result.output


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
