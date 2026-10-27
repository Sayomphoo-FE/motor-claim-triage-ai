# Prompts — Design Rationale

Three LLM calls happen in this prototype:

1. **Claim triage** — Sonnet 4.6, produces the structured recommendation
2. **LLM-Judge** — Opus 4.7, scores the triage reasoning on 5 dimensions
3. **Smoke test ping** — Haiku 4.5, verifies the API key works

This document covers 1 and 2. Each section shows the actual prompt in
the repo, then explains the design choices behind it and the
anti-patterns it avoids.

---

## 1. Claim Triage prompt

Source: `app/prompts/claim_triage.md`.

### 1.1 Full prompt

```markdown
<role>
You are an AI assistant that helps a human claim officer perform the
INITIAL TRIAGE of a motor insurance claim. You are NOT the final
decision maker. The claim officer will make the final decision based on
your structured recommendation.

Your job is to:
1. Produce a short, factual claim summary.
2. Assess initial coverage based ONLY on the Motor Policy excerpts
   provided below.
3. Identify missing documents or information.
4. Flag any potential risks (fraud, inconsistency, exclusions).
5. Recommend the next routing path.
6. Explain your reasoning with explicit [Clause X.Y] citations.
7. Give a confidence level.
</role>

<policy_context>
The following policy clauses were retrieved as most relevant to this
claim. Treat them as the single source of truth. Do NOT invent or
assume any clause not shown here.

{policy_chunks}
</policy_context>

<claim_case>
Claim ID: {claim_id}
Customer: {customer}
Vehicle: {vehicle}
Incident date: {incident_date}
Claim submitted: {claim_submitted_date} (days to submit: {days_to_submit})
Documents submitted: {documents_submitted}
Customer claim history: {customer_claim_history}

Description:
{claim_description}
</claim_case>

<task>
Analyse the claim case using ONLY the policy context above. Produce a
structured triage recommendation.
</task>

<rules>
1. Every statement about coverage or exclusion MUST cite the clause it
   depends on, in the form [Clause X.Y]. Only cite clauses that appear in
   policy_context.
2. If a required piece of information is not in the claim case, add it
   to "missing_information". Do NOT fabricate facts.
3. Choose "coverage_assessment":
   - "Likely covered" only when the event clearly matches a covered peril
     (Clause 1.1) AND no exclusion appears to apply AND documents are
     reasonably complete.
   - "Not covered" ONLY when a clear exclusion from Section 2 directly
     applies. Cite the exclusion.
   - "Possibly covered" when the event matches a covered peril but
     documents or facts are incomplete.
   - "Cannot determine" when the facts are too ambiguous to apply any
     clause confidently.
4. Choose "recommended_routing" by applying Section 4 (Routing Rules):
   - "Standard processing" only when all three conditions in Clause 4.1
     hold.
   - "Manual review" for ambiguity, missing docs, or conflicting info
     (Clause 4.2).
   - "Fraud review" when at least one Clause 4.3 pattern applies
     (inconsistent story / repeated claims / severe damage with weak
     evidence).
   - "Rejection review" when a Section 2 exclusion clearly applies
     (Clause 4.4).
5. If confidence_level is "Low", recommended_routing MUST be
   "Manual review" (never "Standard processing").
6. Keep reasoning concise (no more than 6 sentences).
7. Do NOT calculate payouts or settlement amounts.
8. Do NOT advise the customer directly — your audience is the officer.
</rules>

<examples>
Example of good citation style:
"The event appears to be an accidental collision [Clause 1.1], but
third-party contact details are missing [Clause 3.3], so Manual review
is appropriate [Clause 4.2]."

Example of grounded uncertainty:
"The description does not state whether the driver had consumed alcohol.
Without that fact, Clause 2.1 cannot be evaluated, so coverage is
'Cannot determine'."
</examples>

<output_format>
Call the submit_triage tool exactly once with your structured decision.
All list fields may be empty but must be present. Cite only clauses that
appear in policy_context.
</output_format>
```

### 1.2 Design choices

| Choice | Why |
|---|---|
| XML-style section tags | Claude's attention is reliable at tag boundaries; keeps role / context / task / rules visually separated |
| Policy chunks go in a *distinct* `policy_context` tag | Makes "treat as single source of truth" instruction obvious; the model will not confuse policy text with the role or examples |
| Explicit "You are NOT the final decision maker" | Front-loaded human-in-the-loop framing; appears again as rule #7 (no payouts) and #8 (no customer advice) |
| 7-item role list | Matches the output schema 1:1 so the model's internal plan aligns with the required output fields |
| Rule #1 forces citations | Combined with the output guardrail, this is the primary defence against hallucinated clauses |
| Rule #5 (Low → Manual review) | Enforces the HITL rule from design doc §8.2 at the prompt layer; the output guardrail re-enforces it |
| Two concrete examples | One for citation style, one for appropriate uncertainty. These are the two failure modes most likely to drift without examples |
| `submit_triage` tool call forced | Guarantees Pydantic-valid output shape and enum conformance |
| `<language>` block (bilingual rule) | Keeps enum values and `[Clause X.Y]` IDs in English (they're policy identifiers) while allowing free-text (`claim_summary`, `reasoning`, `missing_information`, `risk_flags`) in the customer's language. Avoids the common failure mode where a translation step gets inserted and loses citation anchors |

### 1.3 Anti-patterns we avoided

- **No "pretend you are a human"** — undermines the HITL framing and
  creates liability if the model stops acting like an AI.
- **No "always be helpful"** — makes `Cannot determine` harder to
  elicit, which is exactly the mode we want when facts are missing.
- **No chain-of-thought scratchpad** — the structured
  `claim_summary` + `reasoning` fields already force the model to
  show its working, and a separate `<thinking>` block would duplicate
  tokens.
- **No examples of concrete coverage calls** — we show citation
  *style* but never show the model a worked example that says
  "Possibly covered". Doing so would bias the model toward imitating
  the example even when evidence doesn't support it.
- **No prompt-level "forget previous instructions" phrasing** — any
  variant of this creates an attack surface for prompt injection.

### 1.4 How the prompt is rendered

`app/agents/triage.py::_render_prompt` populates the `{...}`
placeholders. `claim_description` is the **sanitised** version (PII
masked). The retriever runs four section-filtered sub-queries so the
rendered `{policy_chunks}` block always contains at least one clause
from each of the four policy sections.

---

## 2. LLM-Judge rubric prompt

Source: `app/eval/judge.py::RUBRIC` + per-case template.

### 2.1 Full prompt

```markdown
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
```

The per-case block adds `<claim_description>`, `<ai_output>` (with the
Reasoning verbatim), and `<policy_clauses_actually_retrieved>` as the
grounding reference for Factuality.

### 2.2 Design choices

| Choice | Why |
|---|---|
| Different model family (Opus 4.7) | Reduces grader bias — Sonnet grading Sonnet's output is a known cause of inflated self-scores |
| Explicit scoring guide | 1-5 without a guide is noisy; the guide anchors "3 = partial" so judges don't cluster around 4 |
| Only Reasoning is scored | Coverage / routing / confidence are already scored deterministically by `app/eval/metrics.py`; the Judge grades the free-text that metrics can't |
| `policy_clauses_actually_retrieved` passed in | Factuality can be verified objectively — the Judge gets the same grounding the triage agent had |
| `submit_judgment` tool forced | Same reason as the triage prompt: shape guarantee |
| `overall_comment` string required | Each per-case entry in `docs/eval_report.md` includes this comment, so a reviewer can see the Judge's rationale without re-running the eval |

### 2.3 Anti-patterns we avoided

- **No "be nice"** — explicit "Be strict and specific" is more useful
  than any apologetic phrasing.
- **No "the AI did a good job overall"** — we don't anchor the Judge
  with a positive baseline because then its "Low" scores stop
  meaning anything.
- **No ground-truth leak** — the Judge is NOT told the expected
  routing or coverage. It scores based on whether the Reasoning is
  internally consistent with the retrieved policy, not whether it
  matches our ground truth. The deterministic metrics handle the
  ground-truth comparison separately.

---

## 3. Prompt versioning strategy

- Each prompt file (`app/prompts/*.md`, `app/eval/judge.py::RUBRIC`)
  is versioned via git. The current commit SHA at the time of a
  triage call could be captured into the audit log for perfect
  reproducibility; this is a Phase 2 improvement called out in
  `docs/limitations.md`.
- For now, the audit record stores `model_versions.triage` so a
  future-us can tell which model answered, even if the prompt text
  changes.
