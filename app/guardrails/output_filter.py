"""Output guardrail: verify citations + enforce safety invariants.

Three checks are run in order. Each check may MUTATE the TriageOutput
to a safer value and append a human-readable trigger string.

1. Citation validity
   Every clause ID in `cited_clauses` must appear in the retrieved
   context. Unknown clauses are stripped and the event is logged.

2. "Not covered" requires a retrieved exclusion
   The model may only assert "Not covered" when at least one Section-2
   clause was retrieved AND cited. Otherwise we downgrade to
   "Cannot determine" and switch routing to Manual review. This is
   the hallucination firewall for the most consequential claim call.

3. Low confidence must route Manual review
   Rule from the design doc §8.2. If Low + Standard processing, we
   bump to Manual review.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import RetrievedChunk, TriageOutput


@dataclass
class OutputGuardResult:
    output: TriageOutput
    triggers: list[str] = field(default_factory=list)
    modified: bool = False


def _is_exclusion(clause_id: str) -> bool:
    return clause_id.startswith("2.")


def verify(output: TriageOutput, retrieved: list[RetrievedChunk]) -> OutputGuardResult:
    triggers: list[str] = []
    retrieved_ids = {c.clause_id for c in retrieved}

    # 1. Strip citations that aren't in retrieved context.
    kept: list[str] = []
    for cid in output.cited_clauses:
        c = cid.strip()
        if c in retrieved_ids:
            kept.append(c)
        else:
            triggers.append(f"citation_invalid:{c}")
    if kept != output.cited_clauses:
        output = output.model_copy(update={"cited_clauses": kept})

    # 2. "Not covered" requires at least one retrieved Section-2 clause
    #    AND at least one cited Section-2 clause.
    if output.coverage_assessment == "Not covered":
        retrieved_exclusions = any(_is_exclusion(c) for c in retrieved_ids)
        cited_exclusions = any(_is_exclusion(c) for c in kept)
        if not (retrieved_exclusions and cited_exclusions):
            triggers.append("not_covered_without_exclusion→Cannot determine")
            output = output.model_copy(
                update={
                    "coverage_assessment": "Cannot determine",
                    "recommended_routing": "Manual review",
                    "confidence_level": "Low",
                }
            )

    # 3. Low confidence must not go to Standard processing.
    if (
        output.confidence_level == "Low"
        and output.recommended_routing == "Standard processing"
    ):
        triggers.append("low_confidence_standard_routing→Manual review")
        output = output.model_copy(update={"recommended_routing": "Manual review"})

    return OutputGuardResult(output=output, triggers=triggers, modified=bool(triggers))
