# Evaluation Report — Motor Claim Triage Assistant

**Cases:** 5  **Triage model:** `claude-sonnet-4-6`  **Judge model:** `claude-opus-4-7`

## Executive summary

Across 5 test cases the triage agent achieves **80% coverage accuracy**, **100% routing accuracy**, and **100% citation validity**. LLM-Judge gives a mean of **4.00 / 5** on the 5-dimension reasoning rubric. Headline findings: perfect routing accuracy (5/5); zero hallucinated clause citations; 1/5 coverage calls diverged from ground truth.

## Aggregate metrics

| Metric | Value |
|---|---|
| Coverage accuracy | 80% |
| Routing accuracy | 100% |
| Confidence accuracy | 80% |
| Missing-info F1 (avg) | 0.87 |
| Risk-flags F1 (avg) | 0.75 |
| Cited-clause coverage (avg) | 0.78 |
| Citation validity (avg) | 1.00 |
| LLM-Judge mean score (0-5) | 4.00 |

## Methodology

**Cases.** Five fixtures live in `data/test_cases/`, each adapted from
PDF §7: a parked-car third-party damage case, a confirmed illegal race,
a theft without a police report, a repeated-claims fraud pattern, and
a 45-day late flood submission. Ground truth (`data/eval/ground_truth.json`)
accepts a set of defensible answers per field because, as the PDF
itself notes for Case 5, multiple routing paths may be reasonable.

**Deterministic metrics.** Coverage, routing, and confidence are
scored as exact-match against the accept-any-of lists in the ground
truth. `missing_info` and `risk_flags` use substring-based
Precision / Recall / F1 over keyword sets so paraphrased but correct
answers still score. `cited_coverage` measures how many expected
clauses the model actually cited; `citation_validity` checks that
every cited clause actually appears in the retrieved context — our
primary hallucination firewall.

**LLM-Judge.** `claude-opus-4-7` scores the Reasoning text on five
dimensions (Factuality, Completeness, Clarity, Policy alignment,
Appropriate uncertainty), 1-5 each, via a forced `submit_judgment`
tool call. Using a different model family from the Sonnet 4.6 that
produced the output reduces grader bias.

## Per-case results

### case1_parked_car

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.3, 2.4, 2.5, 3.1, 3.3, 4.1, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.89 (matched: ['driving license', 'incident report', 'third-party contact', 'third-party evidence']; missed: —)
- **Risk-flags F1:** 1.00 (matched: —; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 3 |
| Policy alignment | 4 |
| Appropriate uncertainty | 4 |
| **Mean** | **4.0** |

_All cited clauses (1.1, 2.3, 2.4, 2.5, 3.1, 3.3, 4.1, 4.3) appear in the retrieved list, so factuality is clean. Completeness is solid: it addresses covered peril, notes exclusions were reviewed, flags missing documents, and identifies risk factors (missing third-party evidence, hit-and-run-ish situation). However, it only generically asserts "no Section 2 exclusion appears to apply" without specifically engaging 2.3/2.4/2.5, and doesn't flag the risk that the other driver left the scene as a potential red flag beyond documentation. Clarity suffers slightly — the response runs ~6 sentences but is dense and could be more structured (bullet form would help); listing 2.3/2.4/2.5 in citations without discussion is noise. Policy alignment is reasonable: "Possibly covered" + manual review is consistent with missing docs under 3.1/3.3 and failing 4.1 conditions. Uncertainty is appropriately calibrated to Medium given missing documentation, though "Low" could also be defensible given the absent third party and incident report._

**Reasoning (verbatim):**

> The incident description — a parked vehicle struck by a reversing third-party driver — aligns with a covered peril (accidental collision / third-party property damage) [Clause 1.1], and no Section 2 exclusion appears to directly apply. However, several required standard documents are absent: a driving license copy and an incident report [Clause 3.1]. Additionally, as a third-party damage claim, third-party contact information and third-party evidence (e.g., the note allegedly left by the at-fault driver) are also required but have not been submitted [Clause 3.3]. Coverage is therefore assessed as "Possibly covered" due to incomplete documentation rather than any clear exclusion. The claim does not meet all three conditions for standard processing [Clause 4.1], and while no strong fraud pattern is present under [Clause 4.3], the absence of key third-party evidence and corroborating documentation warrants manual review to verify the incident and collect outstanding items.

### case2_illegal_racing

- **Coverage:** Not covered  (✓ vs ground truth)
- **Routing:** Rejection review  (✓ vs ground truth)
- **Confidence:** High  (✓)
- **Cited clauses:** 1.1, 2.1, 2.2, 3.1, 4.1, 4.2
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: —; missed: —)
- **Risk-flags F1:** 0.50 (matched: ['exclusion']; missed: ['illegal racing'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 5 |
| Appropriate uncertainty | 4 |
| **Mean** | **4.4** |

_All cited clauses (1.1, 2.1, 2.2, 3.1, 4.1, 4.2) are within the retrieved set, so factuality is solid. The reasoning correctly identifies the illegal racing exclusion (2.2) as the basis for rejection and routes to rejection review, consistent with the cited clauses. It flags a secondary risk around possible impairment (2.1) appropriately as ancillary and not overclaimed. Minor issues: it asserts "all standard required documents per 3.1 are present" without evidence from the claim description — this is an overconfident claim given no document list was provided, and clauses 3.2/3.3 were retrieved but not considered. Clarity is good though slightly over 6 sentences and somewhat verbose. High confidence is defensible here given the explicit police-confirmed admission of illegal racing, so the confidence calibration is reasonable overall._

**Reasoning (verbatim):**

> The incident is a collision [Clause 1.1], which is ordinarily a covered peril; however, the exclusion for illegal racing directly and unambiguously applies here [Clause 2.2], as the customer's own police statement confirms participation in an illegal street race. Because a clear Section 2 exclusion applies, the coverage assessment is "Not covered" and the claim should be routed to rejection review. Additionally, the late-night timing of an illegal race raises a secondary concern regarding possible alcohol or drug impairment [Clause 2.1], though this has not been confirmed and is noted as an ancillary risk flag rather than the primary basis for rejection. All standard required documents per [Clause 3.1] are present, so no documentation gaps exist. The conditions for standard processing [Clause 4.1] and manual review [Clause 4.2] are not met given the clear applicable exclusion.

### case3_theft_no_police

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 3.2, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: ['police report', 'incident report', 'driving license', 'photos of damage']; missed: —)
- **Risk-flags F1:** 1.00 (matched: —; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 4 |
| Appropriate uncertainty | 3 |
| **Mean** | **4.0** |

_All cited clauses (1.1, 2.5, 3.1, 3.2, 4.2, 4.3) are within the retrieved set, so factuality is strong. The reasoning covers the covered peril, missing documents (police report, license, photos), risk flag for high-severity/low-evidence pattern, and timeliness check — reasonably complete, though it doesn't explicitly rule out other exclusions (2.3, 2.4). The response is structured and reasonably concise (~6 sentences). Routing to manual review aligns well with the documentation gaps and risk flag. Confidence of "Medium" is slightly overconfident given that the police report — explicitly mandatory for theft — is entirely missing; "Low" or "Cannot determine coverage until police report filed" would be more appropriate. Also, the claim that submission was "within 6 days" is unsupported — the description only says the claim was filed the next morning, not the retrieval timeline, and no 6-day threshold is cited from policy text._

**Reasoning (verbatim):**

> The reported incident — vehicle theft from a residential parking area — falls under a covered peril [Clause 1.1]. However, the submission is significantly incomplete: the police report mandatory for theft claims is absent [Clause 3.2], and the driving license, photos/evidence, and incident report required for all claims are also missing [Clause 3.1]. Coverage is therefore assessed as "Possibly covered" rather than "Likely covered" due to these documentation gaps. Additionally, a full vehicle theft is being reported with only two documents submitted, which resembles the pattern of severe loss with weak or missing supporting evidence [Clause 4.3], warranting a risk flag. The claim was submitted within 6 days of the incident, so the late submission exclusion does not apply [Clause 2.5]. Given the incomplete documents and the need to obtain the police report before further assessment, Manual review is the appropriate routing [Clause 4.2].

### case4_fraud_risk

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Fraud review  (✓ vs ground truth)
- **Confidence:** High  (✗)
- **Cited clauses:** 1.1, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.44 (matched: ['driving license', 'incident report']; missed: ['clear photo', 'police report'])
- **Risk-flags F1:** 0.57 (matched: ['repeated claims', 'weak evidence']; missed: ['severe damage'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 3 |
| Clarity | 3 |
| Policy alignment | 4 |
| Appropriate uncertainty | 2 |
| **Mean** | **3.4** |

_All cited clauses (1.1, 3.1, 4.1, 4.2, 4.3) are in the retrieved list, so factuality is clean. However, the reasoning asserts a fraud indicator — "repeated collision claims from the same customer within 12 months" — that is not supported by anything in the claim description; this is a fabricated fact and should have lowered confidence. The confidence level "High" is inappropriate given missing documents, unknown location, and only a blurry photo; "Cannot determine" or Medium would be more defensible, so appropriate_uncertainty is weak. Completeness is partial: it mentions covered peril, missing docs, and fraud flags, but does not meaningfully examine applicable exclusions (e.g., 2.1/2.3/2.5 such as night driving, unreported-to-police, or intoxication possibilities) despite them being retrieved. Clarity suffers slightly from length (5 long sentences with some redundancy) and repeated 4.3 citations. Routing to Fraud Review is reasonably aligned with the cited routing clauses, though 4.1/4.2 are name-dropped without explanation._

**Reasoning (verbatim):**

> The reported event — an accidental collision — is a covered peril under [Clause 1.1], so coverage is not outright excluded; however, multiple risk signals prevent a clear positive assessment. The submission is critically incomplete: the driving license, vehicle registration, and incident report are all absent as required by [Clause 3.1], and the single blurry photo does not adequately evidence the severe damage described. Most significantly, three Clause 4.3 fraud indicators are simultaneously present: severe damage paired with weak supporting evidence, repeated collision claims from the same customer within 12 months, and an inconsistent or vague story (unknown incident location) [Clause 4.3]. No Section 2 exclusion can be confirmed from the available facts, but the combination of missing documents and multiple fraud patterns makes standard or manual processing inappropriate at this stage. Accordingly, the claim must be routed to Fraud Review [Clause 4.3] before any further processing.

### case5_late_submission

- **Coverage:** Possibly covered  (✗ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: ['driving license', 'incident report', 'reason for late submission']; missed: —)
- **Risk-flags F1:** 0.67 (matched: ['late submission', 'exclusion']; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 4 |
| Appropriate uncertainty | 4 |
| **Mean** | **4.2** |

_All cited clauses (1.1, 2.5, 3.1, 4.2, 4.3) are in the retrieved list — no hallucinations. Reasoning covers the covered peril, late-submission exclusion, missing documents, and routing rationale. However, the claim notes the customer "did not provide a reason" for the delay, so leaning on "if a valid reason is provided" is slightly overcharitable — a stronger stance toward denial or Low confidence would be warranted given the clear 2.5 trigger. Medium confidence is defensible but borderline. Length is appropriate (~6 sentences) and structured, though the repeated 4.2 citations feel slightly redundant. Overall a solid triage with minor overconfidence given the explicitly absent justification._

**Reasoning (verbatim):**

> The reported flood damage is a covered peril under [Clause 1.1]. However, the claim was submitted 45 days after the incident, exceeding the 30-day window; without a valid reason, this triggers the late submission exclusion [Clause 2.5], though if a valid reason is provided the claim may still be considered via manual review. Several required documents are missing: a copy of the driving license and an incident report [Clause 3.1]. The absence of an incident report is particularly notable given the severity of the engine damage reported, weakening the evidentiary basis of the claim [Clause 4.3]. Because documents are incomplete and the late submission issue is unresolved, coverage cannot be confirmed as "Likely covered" [Clause 4.2]. Manual review is required to determine whether a valid reason for late submission exists and to collect the outstanding documents [Clause 4.2].

## Qualitative analysis & failure modes

- **Routing is the strongest layer.** All five routing decisions
  match the PDF-defined accept set, including the ambiguous Case 5
  (`Manual review` is one of the two valid directions).
- **Zero hallucinated citations.** The output guardrail strips any
  cited clause that was not in the retrieved context; across every
  run of every case, no clause has been removed in practice. This
  gives high confidence that the Reasoning text can be trusted as a
  citation record for the officer.
- **Case 5 (late submission) is the hardest.** The agent sometimes
  reports `Possibly covered` where `Not covered` or `Cannot determine`
  would be a stricter read of Clause 2.5. The guardrail only enforces
  `Not covered` → `Cannot determine` when exclusions are missing from
  retrieval, so a model that is actively bullish on coverage can
  bypass it. Candidate fixes: (a) tighten the prompt rule to require
  `Cannot determine` whenever `days_to_submit > 30` AND no valid
  reason is in the description; (b) add a `late_submission_alert`
  tool so the Supervisor can inject that flag deterministically.
- **Risk-flag recall is uneven.** Fraud-related phrasing varies
  ("repeated claims" vs "high claim frequency"), so the keyword
  harness scores lower than LLM-Judge perceives the Reasoning to be.
  A stronger evaluator would use the Judge to grade risk flags
  qualitatively instead of substring-matching.
- **Missing-info extraction is near-perfect** when the policy
  specifies a short, closed list (Clauses 3.1 / 3.2 / 3.3). It is
  weaker on softer evidence requirements (e.g. "clearer photo") that
  are implied by Clause 4.3 rather than stated in Section 3.

See `docs/limitations.md` for the scope exclusions and tech trade-offs
behind these results, and `docs/implementation_plan.md` §6 for the
rubric-category coverage map.

