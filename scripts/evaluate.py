"""Run the full evaluation suite.

For each test case:
  1. Parse the case JSON.
  2. Run the TriageAgent.
  3. Score the output deterministically against ground truth.
  4. Ask the LLM-Judge (Opus 4.7) to grade the Reasoning.

Produces:
  - data/eval/results.json  (machine-readable)
  - docs/eval_report.md     (reviewer-facing)
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from app.agents.triage import TriageAgent
from app.eval.judge import JudgeScore, judge_output
from app.eval.metrics import AggregateScore, CaseScore, score_case
from app.schemas import ClaimInput

load_dotenv()
console = Console()

ROOT = Path(__file__).parent.parent
CASES_DIR = ROOT / "data" / "test_cases"
GT_PATH = ROOT / "data" / "eval" / "ground_truth.json"
RESULTS_PATH = ROOT / "data" / "eval" / "results.json"
REPORT_PATH = ROOT / "docs" / "eval_report.md"

CASE_FILES = [
    "case1_parked_car.json",
    "case2_illegal_racing.json",
    "case3_theft_no_police.json",
    "case4_fraud_risk.json",
    "case5_late_submission.json",
]


def _case_id(filename: str) -> str:
    return Path(filename).stem


def _run_one(agent: TriageAgent, case_path: Path, gt: dict) -> dict[str, Any]:
    case_id = _case_id(case_path.name)
    console.print(f"[cyan]▶ {case_id}[/cyan]")

    claim = ClaimInput.model_validate_json(case_path.read_text(encoding="utf-8"))
    result = agent.run(claim)
    output, chunks = result.output, result.retrieved
    det = score_case(case_id, output, chunks, gt[case_id])
    judgment = judge_output(output.reasoning, output, chunks, claim.claim_description)

    _print_case_summary(det, judgment)

    return {
        "case_id": case_id,
        "input": json.loads(claim.model_dump_json()),
        "output": json.loads(output.model_dump_json()),
        "retrieved_clauses": [c.clause_id for c in chunks],
        "guardrail_triggers": {
            "input": result.input_guard.pii_triggers
            + [f"injection:{t}" for t in result.input_guard.injection_triggers],
            "output": result.output_guard_triggers,
        },
        "latency_ms": result.latency_ms,
        "audit_file": f"{result.audit.session_id}.json",
        "deterministic": _case_score_to_dict(det),
        "judge": judgment.model_dump() | {"mean": round(judgment.mean, 2)},
    }


def _case_score_to_dict(s: CaseScore) -> dict[str, Any]:
    return {
        "coverage_ok": s.coverage_ok,
        "routing_ok": s.routing_ok,
        "confidence_ok": s.confidence_ok,
        "missing_info": asdict(s.missing_info),
        "risk_flags": asdict(s.risk_flags),
        "cited_coverage": s.cited_coverage,
        "citation_validity": s.citation_validity,
    }


def _print_case_summary(d: CaseScore, j: JudgeScore) -> None:
    def tick(ok: bool) -> str:
        return "[green]✓[/green]" if ok else "[red]✗[/red]"

    tbl = Table(show_header=False, box=None, pad_edge=False)
    tbl.add_column(style="dim")
    tbl.add_column()
    tbl.add_row("coverage", tick(d.coverage_ok))
    tbl.add_row("routing", tick(d.routing_ok))
    tbl.add_row("missing_info F1", f"{d.missing_info.f1:.2f}")
    tbl.add_row("risk_flags F1", f"{d.risk_flags.f1:.2f}")
    tbl.add_row("cited coverage", f"{d.cited_coverage:.2f}")
    tbl.add_row("citation validity", f"{d.citation_validity:.2f}")
    tbl.add_row("judge mean", f"{j.mean:.2f}")
    console.print(tbl)
    console.print()


def _render_report(
    rows: list[dict[str, Any]], agg: AggregateScore, judge_mean: float
) -> str:
    lines: list[str] = []
    lines.append("# Evaluation Report — Motor Claim Triage Assistant")
    lines.append("")
    lines.append(
        f"**Cases:** {agg.n}  "
        f"**Triage model:** `claude-sonnet-4-6`  "
        f"**Judge model:** `claude-opus-4-7`"
    )
    lines.append("")
    lines.append("## Aggregate metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Coverage accuracy | {agg.coverage_acc:.0%} |")
    lines.append(f"| Routing accuracy | {agg.routing_acc:.0%} |")
    lines.append(f"| Confidence accuracy | {agg.confidence_acc:.0%} |")
    lines.append(f"| Missing-info F1 (avg) | {agg.missing_info_f1:.2f} |")
    lines.append(f"| Risk-flags F1 (avg) | {agg.risk_flags_f1:.2f} |")
    lines.append(f"| Cited-clause coverage (avg) | {agg.cited_coverage:.2f} |")
    lines.append(f"| Citation validity (avg) | {agg.citation_validity:.2f} |")
    lines.append(f"| LLM-Judge mean score (0-5) | {judge_mean:.2f} |")
    lines.append("")
    lines.append("## Per-case results")
    lines.append("")

    for r in rows:
        d = r["deterministic"]
        j = r["judge"]
        o = r["output"]
        lines.append(f"### {r['case_id']}")
        lines.append("")
        lines.append(f"- **Coverage:** {o['coverage_assessment']}  "
                     f"({'✓' if d['coverage_ok'] else '✗'} vs ground truth)")
        lines.append(f"- **Routing:** {o['recommended_routing']}  "
                     f"({'✓' if d['routing_ok'] else '✗'} vs ground truth)")
        lines.append(f"- **Confidence:** {o['confidence_level']}  "
                     f"({'✓' if d['confidence_ok'] else '✗'})")
        lines.append(f"- **Cited clauses:** {', '.join(o['cited_clauses']) or '—'}")
        lines.append(f"- **Citation validity:** {d['citation_validity']:.2f}")
        lines.append(
            f"- **Missing-info F1:** {d['missing_info']['f1']:.2f} "
            f"(matched: {d['missing_info']['matched'] or '—'}; "
            f"missed: {d['missing_info']['missed'] or '—'})"
        )
        lines.append(
            f"- **Risk-flags F1:** {d['risk_flags']['f1']:.2f} "
            f"(matched: {d['risk_flags']['matched'] or '—'}; "
            f"missed: {d['risk_flags']['missed'] or '—'})"
        )
        lines.append("")
        lines.append("**LLM-Judge:**")
        lines.append("")
        lines.append("| Dim | Score |")
        lines.append("|---|---|")
        lines.append(f"| Factuality | {j['factuality']} |")
        lines.append(f"| Completeness | {j['completeness']} |")
        lines.append(f"| Clarity | {j['clarity']} |")
        lines.append(f"| Policy alignment | {j['policy_alignment']} |")
        lines.append(f"| Appropriate uncertainty | {j['appropriate_uncertainty']} |")
        lines.append(f"| **Mean** | **{j['mean']}** |")
        lines.append("")
        lines.append(f"_{j['overall_comment']}_")
        lines.append("")
        lines.append("**Reasoning (verbatim):**")
        lines.append("")
        lines.append("> " + o["reasoning"].replace("\n", "\n> "))
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    agent = TriageAgent()

    rows: list[dict[str, Any]] = []

    console.rule("Running evaluation")
    for fname in CASE_FILES:
        row = _run_one(agent, CASES_DIR / fname, gt)
        rows.append(row)

    agg = _rebuild_aggregate(rows)
    judge_mean = sum(r["judge"]["mean"] for r in rows) / len(rows)

    RESULTS_PATH.write_text(
        json.dumps(
            {
                "cases": rows,
                "aggregate": asdict(agg),
                "judge_mean": judge_mean,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(_render_report(rows, agg, judge_mean), encoding="utf-8")

    console.rule("Summary")
    console.print(f"[green]Report written to:[/green] {REPORT_PATH}")
    console.print(f"[green]Raw results:[/green] {RESULTS_PATH}")
    return 0


def _rebuild_aggregate(rows: list[dict[str, Any]]) -> AggregateScore:
    n = len(rows)
    if n == 0:
        return AggregateScore(0, 0, 0, 0, 0, 0, 0, 0)
    return AggregateScore(
        n=n,
        coverage_acc=sum(r["deterministic"]["coverage_ok"] for r in rows) / n,
        routing_acc=sum(r["deterministic"]["routing_ok"] for r in rows) / n,
        confidence_acc=sum(r["deterministic"]["confidence_ok"] for r in rows) / n,
        missing_info_f1=sum(r["deterministic"]["missing_info"]["f1"] for r in rows) / n,
        risk_flags_f1=sum(r["deterministic"]["risk_flags"]["f1"] for r in rows) / n,
        cited_coverage=sum(r["deterministic"]["cited_coverage"] for r in rows) / n,
        citation_validity=sum(r["deterministic"]["citation_validity"] for r in rows) / n,
    )


if __name__ == "__main__":
    sys.exit(main())
