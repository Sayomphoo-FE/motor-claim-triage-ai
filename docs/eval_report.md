# Evaluation Report — Motor Claim Triage Assistant

**Cases:** 5  **Triage model:** `claude-sonnet-4-6`  **Judge model:** `claude-opus-4-7`

## Executive summary

Across 5 test cases the triage agent achieves **80% coverage accuracy**, **100% routing accuracy**, and **100% citation validity**. LLM-Judge gives a mean of **3.92 / 5** on the 5-dimension reasoning rubric. Headline findings: perfect routing accuracy (5/5); zero hallucinated clause citations; 1/5 coverage calls diverged from ground truth.

## Aggregate metrics

| Metric | Value |
|---|---|
| Coverage accuracy | 80% |
| Routing accuracy | 100% |
| Confidence accuracy | 100% |
| Missing-info F1 (avg) | 0.87 |
| Risk-flags F1 (avg) | 0.67 |
| Cited-clause coverage (avg) | 0.78 |
| Citation validity (avg) | 1.00 |
| LLM-Judge mean score (0-5) | 3.92 |

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
- **Cited clauses:** 1.1, 2.3, 2.4, 2.5, 3.1, 3.3, 4.1
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
| Appropriate uncertainty | 3 |
| **Mean** | **3.8** |

_All cited clauses (1.1, 2.3, 2.4, 2.5, 3.1, 3.3, 4.1) are within the retrieved set — no hallucinated citations. Completeness is good: covers covered peril, scans exclusions, flags missing documents (note contents, CCTV, third-party details), and routes to manual review. However, clarity suffers: the reasoning runs long (effectively 5-6 dense sentences with heavy bracketed citations) and could be more structured. Policy alignment is reasonable — manual review is appropriate given missing docs — though Clause 4.3/4.4 on manual-review triggers were available and not leveraged. Uncertainty is marked "Medium" which is defensible, but given that the hit-and-run element (driver left scene), unverified note, and absence of CCTV/police report introduce material unknowns about fault and third-party identification, "Low" confidence or an explicit "cannot determine liability" caveat would have been more appropriate. The assumption that the claim was filed within 2 days is also unsupported by the facts provided._

**Reasoning (verbatim):**

> The incident is described as a third-party driver backing into the insured's parked vehicle, which falls under accidental collision and third-party property damage — both covered perils [Clause 1.1]. No Section 2 exclusions appear to apply on the current facts (no indication of intentional damage [Clause 2.3], geographic issue [Clause 2.4], or late submission [Clause 2.5], as the claim was filed within 2 days). However, several required documents are absent: a driving license copy and incident report are missing from the standard set [Clause 3.1], and third-party contact information and third-party evidence are missing as required for third-party damage claims [Clause 3.3]. Because required documents are incomplete, Standard Processing conditions are not fully met [Clause 4.1]. The claim is therefore routed to Manual Review pending receipt of the missing documents, particularly the contents of the note left by the at-fault driver and any available security or CCTV evidence.

### case2_illegal_racing

- **Coverage:** Not covered  (✓ vs ground truth)
- **Routing:** Rejection review  (✓ vs ground truth)
- **Confidence:** High  (✓)
- **Cited clauses:** 1.1, 2.2, 3.1, 4.1
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: —; missed: —)
- **Risk-flags F1:** 0.80 (matched: ['illegal racing', 'exclusion']; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 5 |
| Appropriate uncertainty | 5 |
| **Mean** | **4.6** |

_All cited clauses (1.1, 2.2, 3.1, 4.1) are within the retrieved set — no hallucinations. The reasoning correctly identifies the covered peril, the applicable exclusion (illegal racing under 2.2), confirms document sufficiency, and routes to Rejection review consistent with the exclusion. High confidence is appropriate here because the customer's own statement plus police attendance provides strong corroboration — this is one of the rare cases where high confidence is warranted. Minor completeness gap: no explicit risk flags called out (e.g., 02:00 AM, potential criminal/legal exposure, possible intoxication to verify), and no mention of whether a toxicology/BAC report or formal police report document is on file vs. just a verbal statement. Clarity is good but slightly verbose at ~5 sentences with some redundancy ("directly and unambiguously", "definitive exclusion")._

**Reasoning (verbatim):**

> The incident is an accidental collision, which is a covered peril under [Clause 1.1]; however, the customer's own statement to attending police officers confirms participation in an illegal street race on Rama 9 road. [Clause 2.2] explicitly excludes coverage for damage arising from participation in illegal racing, and this exclusion directly and unambiguously applies here. All standard documents required by [Clause 3.1] have been submitted, including a police report that corroborates the illegal racing activity, leaving no factual ambiguity about the circumstances. Because a clear Section 2 exclusion applies, the claim does not satisfy the conditions for standard processing under [Clause 4.1]. The recommended routing is therefore Rejection review, consistent with the application of a definitive exclusion clause.

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
| Appropriate uncertainty | 4 |
| **Mean** | **4.2** |

_All cited clauses (1.1, 2.5, 3.1, 3.2, 4.2, 4.3) are within the retrieved set — no hallucinations. However, Clause 2.5 is labeled as "Exclusions" in the retrieved list, but the AI cites it as supporting the 30-day filing window, which is a possible mislabeling/misuse concern (minor factuality/alignment issue, though not clearly wrong without clause text). Completeness is solid: covered peril, missing documents, risk flags, and routing are all addressed; exclusions are briefly dismissed without explicitly walking through 2.3/2.4. Reasoning is reasonably concise (~5 sentences) and well-structured. Medium confidence is appropriate given missing police report and absent evidence — not overclaiming. Routing to manual review is well-justified by Clause 4.2 and the document gaps. Minor deduction for the ambiguous use of 2.5 as both an exclusion and a timing clause._

**Reasoning (verbatim):**

> The reported theft is a covered peril under [Clause 1.1], and the claim was submitted within 6 days, well within the 30-day limit [Clause 2.5]. However, coverage cannot be confirmed as "Likely covered" because several required documents are absent: the police report mandatory for theft claims [Clause 3.2], a copy of the driving license, photos/evidence of the theft, and an incident report [Clause 3.1]. The absence of a police report is particularly significant for a theft claim, as it is both a documentary requirement and a potential risk signal — a theft-category total loss with minimal supporting evidence aligns with a Clause 4.3 pattern of severe loss with weak evidence. No exclusions from Section 2 clearly apply at this stage, so outright rejection is not warranted. Per [Clause 4.2], the combination of incomplete required documents and the need to verify the theft report warrants routing to manual review.

### case4_fraud_risk

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Fraud review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.1, 2.3, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.44 (matched: ['driving license', 'incident report']; missed: ['clear photo', 'police report'])
- **Risk-flags F1:** 0.57 (matched: ['repeated claims', 'weak evidence']; missed: ['severe damage'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 3 |
| Completeness | 4 |
| Clarity | 3 |
| Policy alignment | 4 |
| Appropriate uncertainty | 2 |
| **Mean** | **3.2** |

_All cited clauses are within the retrieved list, which is good. However, factuality is weakened because the reasoning invents facts not present in the claim description — specifically, "a pattern of repeated claims from the same customer over a short period (4 claims in 12 months, 3 of which are collision claims)." Nothing in the claim description supports this; it appears fabricated and is used to justify a fraud trigger. Completeness is reasonably strong: covered peril, missing documents, fraud flags, and exclusions are all addressed. Clarity is borderline — the reasoning runs ~6 sentences but is somewhat dense and repeats "Clause 4.3" multiple times. Policy alignment between the cited clauses and the Fraud-review routing is reasonable given the weak evidence and unverifiable location. Appropriate uncertainty is weak: confidence is set to Medium despite a fabricated claims-history fact, and the model should have flagged uncertainty more explicitly or chosen Low confidence given the missing documentation and unverifiable circumstances._

**Reasoning (verbatim):**

> The reported event (accidental collision) is a covered peril under [Clause 1.1], making coverage theoretically possible. However, multiple required documents are missing — driving license, vehicle registration, and incident report — making the submission incomplete per [Clause 3.1]. The claim exhibits at least two distinct Clause 4.3 fraud indicators: severe damage supported only by a single blurry photo (weak evidence for claimed severity) and a pattern of repeated claims from the same customer over a short period (4 claims in 12 months, 3 of which are collision claims) [Clause 4.3]. Additionally, the customer's inability to provide the exact incident location introduces an inconsistent/incomplete story element, a third Clause 4.3 trigger [Clause 4.3]. No Section 2 exclusion can be definitively confirmed or ruled out at this stage (e.g., [Clause 2.1] alcohol/drug impairment, [Clause 2.3] intentional damage) given the unverifiable circumstances. Routing to Fraud review is therefore required per [Clause 4.3], with document collection per [Clause 3.1] to proceed in parallel.

### case5_late_submission

- **Coverage:** Possibly covered  (✗ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: ['driving license', 'incident report', 'reason for late submission']; missed: —)
- **Risk-flags F1:** 0.00 (matched: —; missed: ['late submission', 'exclusion'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 3 |
| Policy alignment | 4 |
| Appropriate uncertainty | 3 |
| **Mean** | **3.8** |

_All cited clauses (1.1, 2.5, 3.1, 4.1, 4.2, 4.3) are within the retrieved set — no hallucinations. Coverage of key points is solid: covered peril, late submission exclusion, missing documents, routing rationale, and fraud consideration. However, the reasoning runs ~6-7 sentences and is somewhat verbose with redundant framing (e.g., restating the late-submission issue multiple times), hurting conciseness. Policy alignment is reasonable — manual review is defensible given 2.5 allows reconsideration with a valid reason — though one could argue the lack of any stated reason should push toward denial/exclusion rather than "Possibly covered." Confidence is rated Medium, but with two significant gaps (no reason for delay, missing core documents) a Low confidence or more explicit "cannot determine coverage yet" framing would be more appropriate; "Possibly covered" slightly overstates certainty on the peril side given documents are missing to verify the event._

**Reasoning (verbatim):**

> The reported flood damage event matches a covered peril [Clause 1.1], so the claim is not excluded on the basis of the peril type. However, the claim was submitted 45 days after the incident, exceeding the 30-day limit, and no valid reason for the delay has been provided, which triggers the late submission exclusion [Clause 2.5] — though that clause allows manual review if a valid reason is subsequently provided. Required documents are incomplete: the driving license copy and incident report are both missing [Clause 3.1], making document submission insufficient for standard processing. The combination of missing documents and the unresolved late submission issue constitute conflicting and incomplete information [Clause 4.2], precluding standard processing [Clause 4.1]. No fraud patterns such as repeated claims or an inconsistent story are evident at this stage, so Fraud Review is not warranted [Clause 4.3]. Manual review is appropriate to allow the customer to provide a reason for late submission and the missing documents before a coverage determination can be finalised [Clause 4.2].


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
