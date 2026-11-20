"""Pydantic schemas for claim input and triage output.

Mirrors the assignment PDF:
- `ClaimInput` matches §5.2 "Sample Claim Input Fields"
- `TriageOutput` matches §6 "Expected AI Output Format"

Extra fields (confidence floats, cited_clauses, retrieved_context) are
candidate additions permitted by the assignment to improve
explainability and evaluation.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

CLAIM_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-_]{1,24}$")

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


CLAIM_TYPES = [
    "Third-party damage",
    "Own damage",
    "Theft",
    "Natural disaster",
    "Other",
]

HISTORY_CLAIM_TYPES = [
    "Windshield",
    "Accident / collision",
    "Theft",
    "Natural disaster",
    "Other",
]

HISTORY_FLAGS = [
    "Short interval between claims",
    "Fraud suspicion",
]

HISTORY_PERIODS = ["12 months", "24 months", "36 months"]


class ClaimInput(BaseModel):
    """Input case following assignment PDF §5.2."""

    claim_id: str = Field(..., description="Unique claim case identifier")
    policy_number: str = Field("", description="Insurance policy number (e.g. POL-2026-14201)")
    claim_type: str = Field("", description="Type of claim event")
    customer: str = Field(..., description="Customer name or anonymized customer ID")
    vehicle: str = Field(..., description="Vehicle model or category")
    incident_date: date = Field(..., description="Date when the incident occurred")
    incident_location: str = Field("", description="Location where the incident occurred")
    claim_submitted_date: date = Field(..., description="Date when claim was submitted")
    claim_description: str = Field(..., description="Free-text description of the incident")
    documents_submitted: list[str] = Field(
        default_factory=list,
        description="List of documents the customer has submitted",
    )
    prior_claims_count: int = Field(0, ge=0, le=10, description="Number of prior claims (0–10; ≥3 displayed as 3+)")
    prior_claims_period: str = Field("24 months", description="Lookback window for prior claims")
    prior_claim_types: list[str] = Field(default_factory=list, description="Types of prior claims submitted")
    history_flags: list[str] = Field(default_factory=list, description="Risk signals from claims history")

    @computed_field
    @property
    def customer_claim_history(self) -> str:
        """Formatted summary sent to Claude — derived from structured history fields."""
        if self.prior_claims_count == 0:
            return "No prior claims"
        count_str = "3+" if self.prior_claims_count >= 3 else str(self.prior_claims_count)
        parts = [f"{count_str} claim(s) in past {self.prior_claims_period}"]
        if self.prior_claim_types:
            parts.append(f"types: {', '.join(self.prior_claim_types)}")
        if self.history_flags:
            parts.append("; ".join(self.history_flags))
        return ". ".join(parts)

    @field_validator("claim_id")
    @classmethod
    def _validate_claim_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Claim ID cannot be empty")
        if not CLAIM_ID_RE.match(v):
            raise ValueError(
                "Claim ID must be 2–25 characters, letters/numbers/hyphens only "
                "(e.g. CLM-2026-00001)"
            )
        return v

    @field_validator("claim_description")
    @classmethod
    def _validate_description(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Claim description must be at least 10 characters")
        if len(v) > 5000:
            raise ValueError("Claim description must be under 5,000 characters")
        return v

    @field_validator("documents_submitted", mode="before")
    @classmethod
    def _normalise_docs(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v)  # type: ignore[arg-type]

    @model_validator(mode="after")
    def _validate_dates(self) -> "ClaimInput":
        from datetime import date as _date
        today = _date.today()
        if self.incident_date > today:
            raise ValueError("Incident date cannot be in the future")
        if self.claim_submitted_date > today:
            raise ValueError("Claim submitted date cannot be in the future")
        if self.claim_submitted_date < self.incident_date:
            raise ValueError("Claim submitted date cannot be before incident date")
        return self

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
