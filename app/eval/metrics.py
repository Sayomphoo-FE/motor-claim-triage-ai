"""Deterministic metrics for triage evaluation.

Ground-truth labels use set-of-acceptable-values (`_any_of`) because
multiple answers can be defensible per PDF §7 (e.g. late-submission
case: Rejection review OR Manual review both acceptable).

Keyword matching for missing_info / risk_flags is intentionally
substring-based + lowercase to tolerate paraphrases — the agent may
write "police report" or "a police report is missing" and both must
count as a hit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import RetrievedChunk, TriageOutput


@dataclass
class CasePRF:
    precision: float
    recall: float
    f1: float
    matched: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)


def _norm(s: str) -> str:
    return s.lower().strip()


def _any_substring_hit(items: list[str], keywords: list[str]) -> list[str]:
    """Return keywords for which at least one item contains that keyword."""
    hits: list[str] = []
    low_items = [_norm(i) for i in items]
    for kw in keywords:
        k = _norm(kw)
        if any(k in it for it in low_items):
            hits.append(kw)
    return hits


def coverage_match(predicted: str, expected: list[str]) -> bool:
    return predicted in expected


def routing_match(predicted: str, expected: list[str]) -> bool:
    return predicted in expected


def confidence_match(predicted: str, expected: list[str]) -> bool:
    return predicted in expected


def missing_info_prf(predicted: list[str], expected_any_of: list[str]) -> CasePRF:
    """Precision/Recall against the set of acceptable keywords.

    - Recall = how many expected keywords the prediction mentioned.
    - Precision = fraction of prediction items that matched any expected
      keyword (unmatched items are either spurious or extra-but-useful;
      we treat them as 'not scored against GT' rather than wrong).
    """
    if not expected_any_of:
        # Nothing expected; precision undefined but recall is trivially 1.
        return CasePRF(precision=1.0, recall=1.0, f1=1.0)

    hit_keywords = _any_substring_hit(predicted, expected_any_of)
    recall = len(hit_keywords) / len(expected_any_of)

    if not predicted:
        precision = 0.0 if expected_any_of else 1.0
    else:
        matched_predicted = sum(
            1
            for p in predicted
            if any(_norm(kw) in _norm(p) for kw in expected_any_of)
        )
        precision = matched_predicted / len(predicted)

    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    missed = [kw for kw in expected_any_of if kw not in hit_keywords]
    return CasePRF(precision, recall, f1, matched=hit_keywords, missed=missed)


def risk_flags_prf(predicted: list[str], expected_any_of: list[str]) -> CasePRF:
    """Same semantics as missing_info_prf but for risk flags."""
    return missing_info_prf(predicted, expected_any_of)


def cited_clauses_coverage(
    predicted_clauses: list[str], expected_any_of: list[str]
) -> float:
    """Fraction of expected clauses that appeared in cited_clauses."""
    if not expected_any_of:
        return 1.0
    preds = {c.strip() for c in predicted_clauses}
    hits = sum(1 for c in expected_any_of if c in preds)
    return hits / len(expected_any_of)


def citation_validity(
    cited_clauses: list[str], retrieved: list[RetrievedChunk]
) -> float:
    """Fraction of cited clauses that actually appear in retrieved context."""
    if not cited_clauses:
        return 1.0  # nothing to verify
    retrieved_ids = {c.clause_id for c in retrieved}
    valid = sum(1 for c in cited_clauses if c.strip() in retrieved_ids)
    return valid / len(cited_clauses)


@dataclass
class CaseScore:
    case_id: str
    coverage_ok: bool
    routing_ok: bool
    confidence_ok: bool
    missing_info: CasePRF
    risk_flags: CasePRF
    cited_coverage: float
    citation_validity: float


def score_case(
    case_id: str,
    output: TriageOutput,
    retrieved: list[RetrievedChunk],
    gt: dict,
) -> CaseScore:
    return CaseScore(
        case_id=case_id,
        coverage_ok=coverage_match(output.coverage_assessment, gt["expected_coverage"]),
        routing_ok=routing_match(output.recommended_routing, gt["expected_routing"]),
        confidence_ok=confidence_match(
            output.confidence_level, gt.get("expected_confidence", ["High", "Medium", "Low"])
        ),
        missing_info=missing_info_prf(
            output.missing_information, gt.get("expected_missing_any_of", [])
        ),
        risk_flags=risk_flags_prf(
            output.risk_flags, gt.get("expected_risk_flags_any_of", [])
        ),
        cited_coverage=cited_clauses_coverage(
            output.cited_clauses, gt.get("expected_cited_clauses_any_of", [])
        ),
        citation_validity=citation_validity(output.cited_clauses, retrieved),
    )


@dataclass
class AggregateScore:
    n: int
    coverage_acc: float
    routing_acc: float
    confidence_acc: float
    missing_info_f1: float
    risk_flags_f1: float
    cited_coverage: float
    citation_validity: float


def aggregate(scores: list[CaseScore]) -> AggregateScore:
    n = len(scores)
    if n == 0:
        return AggregateScore(0, 0, 0, 0, 0, 0, 0, 0)
    return AggregateScore(
        n=n,
        coverage_acc=sum(s.coverage_ok for s in scores) / n,
        routing_acc=sum(s.routing_ok for s in scores) / n,
        confidence_acc=sum(s.confidence_ok for s in scores) / n,
        missing_info_f1=sum(s.missing_info.f1 for s in scores) / n,
        risk_flags_f1=sum(s.risk_flags.f1 for s in scores) / n,
        cited_coverage=sum(s.cited_coverage for s in scores) / n,
        citation_validity=sum(s.citation_validity for s in scores) / n,
    )
