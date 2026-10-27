"""Claim Triage Agent.

Flow:
    ClaimInput → generate retrieval queries → RAG lookup →
    build prompt → Claude Sonnet 4.6 with forced tool-use for
    structured output → TriageOutput.

Structured output is enforced via Anthropic's tool-use feature: we give
Claude a `submit_triage` tool whose JSON schema is derived from the
Pydantic model, then force `tool_choice` to that tool. This guarantees
the model returns a validated TriageOutput shape.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from app.rag.retriever import retrieve_multi
from app.schemas import ClaimInput, RetrievedChunk, TriageOutput

load_dotenv()

TRIAGE_MODEL = os.getenv("TRIAGE_MODEL", "claude-sonnet-4-6")
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "claim_triage.md"

# Keep this schema aligned with app/schemas.py TriageOutput.
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


def _generate_queries(claim: ClaimInput) -> list[tuple[str, str | None]]:
    """Produce 4 targeted sub-queries, one per policy section.

    Sub-queries let us pull the most relevant clauses from each section
    (covered events, exclusions, required documents, routing) rather
    than relying on a single generic claim-description query.
    """
    desc = claim.claim_description
    docs = ", ".join(claim.documents_submitted) or "none"
    history = claim.customer_claim_history or "none"
    return [
        (f"Covered perils for: {desc}", "1"),
        (f"Exclusions that might apply to: {desc}. History: {history}.", "2"),
        (f"Required documents for this claim type. Submitted: {docs}.", "3"),
        (f"Routing rules for this claim situation: {desc}", "4"),
    ]


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    return "\n\n---\n\n".join(
        f"[Clause {c.clause_id}] (section: {c.section}, score: {c.score:.2f})\n{c.text}"
        for c in chunks
    )


def _render_prompt(claim: ClaimInput, chunks: list[RetrievedChunk]) -> str:
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
        claim_description=claim.claim_description,
    )


class TriageAgent:
    def __init__(self, model: str = TRIAGE_MODEL):
        self.client = Anthropic()
        self.model = model

    def run(self, claim: ClaimInput) -> tuple[TriageOutput, list[RetrievedChunk]]:
        """Run triage. Returns (output, retrieved_chunks) for audit."""
        queries = _generate_queries(claim)
        chunks = retrieve_multi(
            [q for q, _ in queries],
            top_k_per_query=3,
            section_nums=[s for _, s in queries],
        )
        prompt = _render_prompt(claim, chunks)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
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
        return TriageOutput.model_validate(payload), chunks
