"""Pydantic schemas for claim input and triage output.

Mirrors the assignment PDF:
- `ClaimInput` matches §5.2 "Sample Claim Input Fields"
- `TriageOutput` matches §6 "Expected AI Output Format"

Extra fields (confidence floats, cited_clauses, retrieved_context) are
candidate additions permitted by the assignment to improve
explainability and evaluation.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

CoverageAssessment = Literal[
    "Likely covered",
    "Possibly covered",
    "Not covered",
    "Cannot determine",
]

RoutingDecision = Literal[
    "Standard processing",
    "Manual review",
    "Fraud review",
    "Rejection review",
]

ConfidenceLevel = Literal["High", "Medium", "Low"]

ResponseLanguage = Literal["auto", "th", "en"]


class ClaimInput(BaseModel):
    """Input case following assignment PDF §5.2."""

    claim_id: str = Field(..., description="Unique claim case identifier")
    customer: str = Field(..., description="Customer name or anonymized customer ID")
    vehicle: str = Field(..., description="Vehicle model or category")
    incident_date: date = Field(..., description="Date when the incident occurred")
    claim_submitted_date: date = Field(..., description="Date when claim was submitted")
    claim_description: str = Field(..., description="Free-text description of the incident")
    documents_submitted: list[str] = Field(
        default_factory=list,
        description="List of documents the customer has submitted",
    )
    customer_claim_history: str = Field(
        "",
        description="Historical claim count or behavior (e.g. '1 claim in past 24 months')",
    )
    response_language: ResponseLanguage = Field(
        "auto",
        description=(
            "Override the language of free-text output. "
            "'auto' = detect from claim_description; 'th' = force Thai; "
            "'en' = force English. Enum values and Clause IDs stay English regardless."
        ),
    )

    @field_validator("documents_submitted", mode="before")
    @classmethod
    def _normalise_docs(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v)  # type: ignore[arg-type]

    def days_to_submit(self) -> int:
        """Days elapsed between incident and claim submission."""
        return (self.claim_submitted_date - self.incident_date).days


class RetrievedChunk(BaseModel):
    """A single policy chunk returned from Qdrant."""

    clause_id: str
    section: str
    text: str
    score: float


class TriageOutput(BaseModel):
    """Structured triage output following assignment PDF §6."""

    claim_summary: str = Field(..., description="Short summary of the case")
    coverage_assessment: CoverageAssessment = Field(
        ..., description="Initial coverage assessment"
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Missing documents or data items",
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Potential risk flags detected",
    )
    recommended_routing: RoutingDecision = Field(
        ..., description="Where this claim should be routed"
    )
    reasoning: str = Field(
        ...,
        description="Clear explanation of the recommendation (cite [Clause X.Y])",
    )
    confidence_level: ConfidenceLevel = Field(..., description="Overall confidence")
    cited_clauses: list[str] = Field(
        default_factory=list,
        description="Clause IDs the reasoning relies on (e.g. ['1.1', '2.2'])",
    )
