"""Claim Triage Agent.

Flow:
    ClaimInput → input guardrail (PII mask + injection detect) →
    generate retrieval queries → RAG lookup →
    build prompt → Claude Sonnet 4.6 with forced tool-use for
    structured output → output guardrail (citation + safety) →
    TriageResult (output + retrieved chunks + audit record).

Structured output is enforced via Anthropic's tool-use feature: we give
Claude a `submit_triage` tool whose JSON schema is derived from the
Pydantic model, then force `tool_choice` to that tool. This guarantees
the model returns a validated TriageOutput shape.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from app.guardrails.input_filter import InputGuardResult, sanitize_text
from app.guardrails.output_filter import verify as verify_output
from app.observability.audit import AuditRecord, write_audit
from app.rag.retriever import retrieve_multi
from app.schemas import ClaimInput, RetrievedChunk, TriageOutput

load_dotenv()

TRIAGE_MODEL = os.getenv("TRIAGE_MODEL", "claude-sonnet-4-6")
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "claim_triage.md"

TRIAGE_TOOL = {
    "name": "submit_triage",
    "description": "Submit the final structured triage recommendation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "claim_summary": {
                "type": "string",
                "description": "Short factual summary of the case (2-3 sentences).",
            },
            "coverage_assessment": {
                "type": "string",
                "enum": [
                    "Likely covered",
                    "Possibly covered",
                    "Not covered",
                    "Cannot determine",
                ],
            },
            "missing_information": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Documents or facts not provided but needed.",
            },
            "risk_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Potential risk signals (fraud, inconsistency, etc.).",
            },
            "recommended_routing": {
                "type": "string",
                "enum": [
                    "Standard processing",
                    "Manual review",
                    "Fraud review",
                    "Rejection review",
                ],
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "Concise reasoning with [Clause X.Y] citations. "
                    "No more than 6 sentences."
                ),
            },
            "confidence_level": {
                "type": "string",
                "enum": ["High", "Medium", "Low"],
            },
            "cited_clauses": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Clause IDs cited in reasoning, e.g. ['1.1', '4.2'].",
            },
        },
        "required": [
            "claim_summary",
            "coverage_assessment",
            "missing_information",
            "risk_flags",
            "recommended_routing",
            "reasoning",
            "confidence_level",
            "cited_clauses",
        ],
    },
}


@dataclass
class TraceStep:
    """One instrumented step of the triage pipeline. Collected during
    `TriageAgent.run` and surfaced on `TriageResult.trace` so the UI
    can show reviewers *what happened in what order and how long each
    piece took*."""

    index: int
    icon: str
    name: str
    duration_ms: int
    details: str  # one-liner summary suitable for a step card
    status: str = "ok"  # "ok" | "warn" | "info"


@dataclass
class TriageResult:
    output: TriageOutput
    retrieved: list[RetrievedChunk]
    input_guard: InputGuardResult
    output_guard_triggers: list[str]
    audit: AuditRecord
    latency_ms: int
    trace: list[TraceStep] = field(default_factory=list)


def _generate_queries(claim_description: str, customer_history: str, documents: str) -> list[tuple[str, str | None]]:
    """Produce 4 targeted sub-queries, one per policy section."""
    return [
        (f"Covered perils for: {claim_description}", "1"),
        (f"Exclusions that might apply to: {claim_description}. History: {customer_history}.", "2"),
        (f"Required documents for this claim type. Submitted: {documents}.", "3"),
        (f"Routing rules for this claim situation: {claim_description}", "4"),
    ]


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    return "\n\n---\n\n".join(
        f"[Clause {c.clause_id}] (section: {c.section}, score: {c.score:.2f})\n{c.text}"
        for c in chunks
    )


def _render_prompt(
    claim: ClaimInput, sanitized_description: str, chunks: list[RetrievedChunk]
) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        policy_chunks=_format_chunks(chunks),
        claim_id=claim.claim_id,
        customer=claim.customer,
        vehicle=claim.vehicle,
        incident_date=claim.incident_date.isoformat(),
        claim_submitted_date=claim.claim_submitted_date.isoformat(),
        days_to_submit=claim.days_to_submit(),
        documents_submitted=", ".join(claim.documents_submitted) or "(none provided)",
        customer_claim_history=claim.customer_claim_history or "(none provided)",
        claim_description=sanitized_description,
    )


class TriageAgent:
    def __init__(self, model: str = TRIAGE_MODEL, persist_audit: bool = True):
        self.client = Anthropic()
        self.model = model
        self.persist_audit = persist_audit

    def run(
        self,
        claim: ClaimInput,
        on_step: Callable[["TraceStep"], None] | None = None,
    ) -> TriageResult:
        """Run the full guarded triage pipeline.

        A `TraceStep` is appended for each named stage so the UI can
        show a reviewer-friendly timeline. Timing comes from
        `time.perf_counter()` deltas between checkpoints.

        If `on_step` is supplied, it is invoked synchronously after
        every stage completes. The UI uses this to push live updates
        to a floating trace panel so the reviewer can watch the
        pipeline advance in real time rather than waiting for the
        whole call to finish.
        """
        trace: list[TraceStep] = []
        t0 = time.perf_counter()
        last = t0

        def _tick() -> int:
            nonlocal last
            now = time.perf_counter()
            ms = int((now - last) * 1000)
            last = now
            return ms

        def _emit(step: TraceStep) -> None:
            trace.append(step)
            if on_step is not None:
                try:
                    on_step(step)
                except Exception:  # noqa: BLE001 — UI callbacks must never kill the run
                    pass

        # 1. Input guardrail — sanitize free-text fields.
        input_guard = sanitize_text(claim.claim_description)
        sanitized_description = input_guard.sanitized
        _emit(TraceStep(
            index=1,
            icon="🧹",
            name="Input Guardrail",
            duration_ms=_tick(),
            details=(
                f"PII masked: {len(input_guard.pii_triggers)} · "
                f"Injection flags: {len(input_guard.injection_triggers)}"
            ),
            status="warn" if (input_guard.pii_triggers or input_guard.injection_triggers) else "ok",
        ))

        # 2. RAG query generation.
        docs = ", ".join(claim.documents_submitted) or "none"
        history = claim.customer_claim_history or "none"
        queries = _generate_queries(sanitized_description, history, docs)
        _emit(TraceStep(
            index=2,
            icon="🔎",
            name="RAG Query Generation",
            duration_ms=_tick(),
            details=f"Built {len(queries)} section-filtered sub-queries (sections 1-4)",
            status="info",
        ))

        # 3. Vector retrieval.
        chunks = retrieve_multi(
            [q for q, _ in queries],
            top_k_per_query=3,
            section_nums=[s for _, s in queries],
        )
        clause_ids = ", ".join(c.clause_id for c in chunks)
        _emit(TraceStep(
            index=3,
            icon="📚",
            name="Vector Retrieval",
            duration_ms=_tick(),
            details=(
                f"Qdrant top-3 × 4 queries → {len(chunks)} unique chunks "
                f"[{clause_ids}]"
            ),
        ))

        # 4. Prompt build.
        prompt = _render_prompt(claim, sanitized_description, chunks)
        _emit(TraceStep(
            index=4,
            icon="✏️",
            name="Prompt Build",
            duration_ms=_tick(),
            details=f"Rendered prompt with {len(chunks)} clauses · {len(prompt):,} chars",
            status="info",
        ))

        # 5. LLM call. 4000-token budget so a long Thai `reasoning`
        # cannot truncate trailing enum fields off the tool call.
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "submit_triage"},
            messages=[{"role": "user", "content": prompt}],
        )
        tool_block = next(
            b for b in response.content if getattr(b, "type", None) == "tool_use"
        )
        payload = (
            tool_block.input
            if isinstance(tool_block.input, dict)
            else json.loads(tool_block.input)
        )
        raw_output = TriageOutput.model_validate(payload)
        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "input_tokens", "?")
        out_tok = getattr(usage, "output_tokens", "?")
        _emit(TraceStep(
            index=5,
            icon="🤖",
            name=f"Claude Sonnet ({self.model})",
            duration_ms=_tick(),
            details=(
                f"Forced tool-use · stop_reason={response.stop_reason} · "
                f"in={in_tok} / out={out_tok} tokens"
            ),
        ))

        # 6. Output guardrail.
        guard = verify_output(raw_output, chunks)
        _emit(TraceStep(
            index=6,
            icon="✅",
            name="Output Guardrail",
            duration_ms=_tick(),
            details=(
                "Verified citations + safety invariants · "
                f"triggers: {len(guard.triggers)}"
            ),
            status="warn" if guard.triggers else "ok",
        ))

        total_ms = int((time.perf_counter() - t0) * 1000)

        # 7. Build + write audit record.
        audit = AuditRecord(claim_id=claim.claim_id)
        audit.set_customer(claim.customer)
        audit.model_versions = {"triage": self.model}
        audit.input_guard_triggers = (
            input_guard.pii_triggers + [f"injection:{t}" for t in input_guard.injection_triggers]
        )
        audit.output_guard_triggers = guard.triggers
        audit.retrieved_chunks = [
            {"clause_id": c.clause_id, "section": c.section, "score": round(c.score, 3)}
            for c in chunks
        ]
        audit.triage_output = json.loads(guard.output.model_dump_json())
        audit.cited_clauses = guard.output.cited_clauses
        audit.routing_decision = guard.output.recommended_routing
        audit.coverage_assessment = guard.output.coverage_assessment
        audit.confidence_level = guard.output.confidence_level
        audit.latency_ms = total_ms

        if self.persist_audit:
            write_audit(audit)
        _emit(TraceStep(
            index=7,
            icon="📝",
            name="Audit Write",
            duration_ms=_tick(),
            details=f"JSON written → data/audit_logs/{audit.session_id}.json",
            status="info",
        ))

        return TriageResult(
            output=guard.output,
            retrieved=chunks,
            input_guard=input_guard,
            output_guard_triggers=guard.triggers,
            audit=audit,
            latency_ms=total_ms,
            trace=trace,
        )
