"""LLM-as-Judge for triage reasoning quality.

Opus 4.7 (a different model family from the Sonnet 4.6 that produced
the output) scores the Reasoning field on 5 dimensions, each 1-5:

    Factuality          — only cites clauses that exist in context
    Completeness        — covers the key points of the case
    Clarity             — concise and readable
    Policy alignment    — recommendation is consistent with policy
    Appropriate uncertainty — uses "Cannot determine" / Low confidence
                              when the facts truly warrant it

Scoring is forced-tool to guarantee structured output.
"""
from __future__ import annotations

import json
import os
from typing import Literal

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.schemas import RetrievedChunk, TriageOutput

load_dotenv()
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-opus-4-7")

Score = Literal[1, 2, 3, 4, 5]


class JudgeScore(BaseModel):
    factuality: Score = Field(..., description="Does reasoning only cite clauses that exist?")
    completeness: Score = Field(..., description="Does it cover the key points?")
    clarity: Score = Field(..., description="Is it concise and easy to read?")
    policy_alignment: Score = Field(..., description="Is the recommendation consistent with policy?")
    appropriate_uncertainty: Score = Field(..., description="Does it use uncertainty well?")
    overall_comment: str = Field(..., description="One or two sentences summarising.")

    @property
    def mean(self) -> float:
        return (
            self.factuality
            + self.completeness
            + self.clarity
            + self.policy_alignment
            + self.appropriate_uncertainty
        ) / 5


JUDGE_TOOL = {
    "name": "submit_judgment",
    "description": "Submit a structured 1-5 score for each rubric dimension.",
    "input_schema": {
        "type": "object",
        "properties": {
            "factuality": {"type": "integer", "minimum": 1, "maximum": 5},
            "completeness": {"type": "integer", "minimum": 1, "maximum": 5},
            "clarity": {"type": "integer", "minimum": 1, "maximum": 5},
            "policy_alignment": {"type": "integer", "minimum": 1, "maximum": 5},
            "appropriate_uncertainty": {"type": "integer", "minimum": 1, "maximum": 5},
            "overall_comment": {"type": "string"},
        },
        "required": [
            "factuality",
            "completeness",
            "clarity",
            "policy_alignment",
            "appropriate_uncertainty",
            "overall_comment",
        ],
    },
}

RUBRIC = """\
You are an impartial reviewer scoring an AI-generated motor-insurance
claim triage recommendation. Score the Reasoning on 5 dimensions,
1 (poor) to 5 (excellent). Be strict and specific.

Dimensions:
1. Factuality — The reasoning should ONLY cite clauses listed under
   "Policy clauses actually retrieved" below. Any citation outside
   that list is a hallucination and should drop this score.
2. Completeness — The reasoning should cover the main points the
   officer needs: covered peril (if any), applicable exclusions,
   missing documents, risk flags.
3. Clarity — Concise (no more than ~6 sentences), structured, no fluff.
4. Policy alignment — The recommended routing and coverage call must
   be consistent with the clauses cited.
5. Appropriate uncertainty — Prefer "Cannot determine" / "Low"
   confidence when key facts are missing; penalise overconfident
   claims unsupported by evidence.

Scoring guide (apply uniformly):
    5 = fully meets the dimension with no issues
    4 = meets with minor issues
    3 = partially meets; noticeable gaps
    2 = largely fails
    1 = fails completely or is actively misleading

Call `submit_judgment` exactly once.
"""


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no clauses retrieved)"
    return "\n".join(f"- [Clause {c.clause_id}] {c.section}" for c in chunks)


def judge_output(
    reasoning: str,
    output: TriageOutput,
    retrieved: list[RetrievedChunk],
    claim_description: str,
    model: str = JUDGE_MODEL,
) -> JudgeScore:
    client = Anthropic()
    user_prompt = f"""{RUBRIC}

<claim_description>
{claim_description}
</claim_description>

<ai_output>
Coverage: {output.coverage_assessment}
Routing: {output.recommended_routing}
Confidence: {output.confidence_level}
Cited clauses: {", ".join(output.cited_clauses) or "(none)"}

Reasoning:
{reasoning}
</ai_output>

<policy_clauses_actually_retrieved>
{_format_chunks(retrieved)}
</policy_clauses_actually_retrieved>
"""
    resp = client.messages.create(
        model=model,
        max_tokens=800,
        tools=[JUDGE_TOOL],
        tool_choice={"type": "tool", "name": "submit_judgment"},
        messages=[{"role": "user", "content": user_prompt}],
    )
    tool_block = next(
        b for b in resp.content if getattr(b, "type", None) == "tool_use"
    )
    payload = (
        tool_block.input
        if isinstance(tool_block.input, dict)
        else json.loads(tool_block.input)
    )
    return JudgeScore.model_validate(payload)
