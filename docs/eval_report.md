# Evaluation Report — Motor Claim Triage Assistant

**Cases:** 5  **Triage model:** `claude-sonnet-4-6`  **Judge model:** `claude-opus-4-7`

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
| LLM-Judge mean score (0-5) | 4.20 |

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
| Factuality | 4 |
| Completeness | 5 |
| Clarity | 4 |
| Policy alignment | 5 |
| Appropriate uncertainty | 4 |
| **Mean** | **4.4** |

_The reasoning cites Clause 3.3 which is in the retrieved list, but all other citations (1.1, 2.3, 2.4, 2.5, 3.1, 4.1, 4.3) are valid. However, Clause 3.2 was retrieved but not used — not a factuality issue. No hallucinated clauses detected, so factuality is strong (minor deduction for not leveraging 3.2 which likely covers additional required docs). Completeness is excellent: covers peril, exclusions ruled out, missing documents enumerated, and risk flag identified. Clarity is good but slightly dense at 5-6 long sentences with heavy inline citations. Policy alignment is consistent — manual review follows from incomplete docs plus risk flag. Uncertainty is appropriately Medium given weak third-party evidence, though "Possibly covered" with Medium confidence is well-calibrated._

**Reasoning (verbatim):**

> The incident description — a parked vehicle struck by another driver — aligns with a covered peril (accidental collision / third-party property damage) [Clause 1.1]. No Section 2 exclusions appear to apply on the current facts: submission was within 30 days [Clause 2.5], there is no indication of intentional damage [Clause 2.3] or out-of-area use [Clause 2.4]. However, the claim is missing the driving license, an incident report, third-party contact information, and third-party evidence, all of which are required [Clause 3.1, Clause 3.3]. Because required documents are incomplete and the only third-party evidence is an unverified note from a driver who has since left the scene, this also raises a flag for damage reported with weak supporting evidence [Clause 4.3]. Standard processing cannot be applied as not all required documents are present and a risk flag exists [Clause 4.1]; Manual review is the appropriate route pending receipt and verification of the missing items.

### case2_illegal_racing

- **Coverage:** Not covered  (✓ vs ground truth)
- **Routing:** Rejection review  (✓ vs ground truth)
- **Confidence:** High  (✓)
- **Cited clauses:** 1.1, 2.2, 3.1, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: —; missed: —)
- **Risk-flags F1:** 0.40 (matched: ['exclusion']; missed: ['illegal racing'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 3 |
| Policy alignment | 5 |
| Appropriate uncertainty | 5 |
| **Mean** | **4.4** |

_All cited clauses (1.1, 2.2, 3.1, 4.3) are in the retrieved list, so factuality is clean. The reasoning correctly identifies illegal racing as an exclusion overriding the covered-collision event, confirms documents, and routes to rejection review — well aligned with the clauses. High confidence is justified given the customer's own admission and police attendance. Main weakness is clarity/conciseness: the response runs to ~6 fairly dense sentences with some redundancy (e.g., restating the routing conclusion twice, extra commentary on fraud review not strictly needed). Completeness is solid but could more explicitly note that no further risk flags apply; the fraud-review aside is useful but slightly tangential._

**Reasoning (verbatim):**

> The customer's own statement — recorded by attending police — confirms participation in an illegal street race at the time of the collision, which directly and unambiguously triggers [Clause 2.2], excluding coverage for damage arising from illegal racing. Although the underlying event (collision) would ordinarily qualify as an accidental collision under [Clause 1.1], the Clause 2.2 exclusion overrides coverage when the collision occurs during illegal racing. All standard required documents per [Clause 3.1] are present (claim form, driving license, vehicle registration, photos of damage, incident report), and a police report was also submitted, leaving no documentation gaps. There are no conflicting facts — the admission is consistent across the customer's statement and police attendance — so fraud review is not additionally warranted, but the clear exclusion makes rejection review the appropriate path. Per [Clause 4.3], severe damage with strong supporting evidence (police report, photos) does not independently elevate this to fraud review; the exclusion is the primary driver. The recommended routing is therefore Rejection review based on the clear applicability of [Clause 2.2].

### case3_theft_no_police

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 3.2, 4.1, 4.2, 4.3
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

_All cited clauses (1.1, 2.5, 3.1, 3.2, 4.1, 4.2, 4.3) appear in the retrieved list, so factuality is solid. The reasoning covers the covered peril, missing documents, risk flags, and routing. However, it does not explicitly check other exclusions retrieved (2.3, 2.4) that might be relevant to theft, which is a minor completeness gap. Clarity is good though slightly dense at ~6 sentences. The leap from "no police report yet" to a fraud signal under 4.3 is somewhat aggressive — the customer only discovered the theft that morning, so delay is not unusual; labeling this as "weak supporting evidence triggering fraud" overstates the risk, which also undermines appropriate uncertainty. Medium confidence is reasonable, but the fraud framing is overconfident given the facts. Routing to manual review is appropriate and well-aligned with cited routing clauses._

**Reasoning (verbatim):**

> Vehicle theft is a covered peril under [Clause 1.1], and the claim was submitted within the 30-day limit (6 days), so [Clause 2.5] does not apply. However, several mandatory documents are absent: a police report is specifically required for theft claims [Clause 3.2], and a driving license copy, photos, and incident report are universally required [Clause 3.1]. The absence of a police report — particularly given that the customer has not yet filed one — constitutes severe damage reported with weak supporting evidence, triggering a potential fraud signal [Clause 4.3]. Because required documents are incomplete and there is at least one risk flag, standard processing conditions are not met [Clause 4.1]. The claim is routed to manual review pending document completion and officer judgment on whether the missing police report warrants escalation to fraud review [Clause 4.2].

### case4_fraud_risk

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Fraud review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.1, 2.3, 2.5, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.44 (matched: ['driving license', 'incident report']; missed: ['clear photo', 'police report'])
- **Risk-flags F1:** 0.57 (matched: ['repeated claims', 'severe damage']; missed: ['weak evidence'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 3 |
| Policy alignment | 4 |
| Appropriate uncertainty | 3 |
| **Mean** | **3.8** |

_All cited clauses (1.1, 2.1, 2.3, 2.5, 3.1, 4.1, 4.2, 4.3) are within the retrieved set, so factuality is strong. Completeness is good: covers covered peril, missing docs, fraud flags, and acknowledges exclusions cannot be ruled out — though it doesn't explain why 4.1/4.2 were cited (they appear in the citation list but aren't discussed in the reasoning). Clarity suffers: the reasoning is 5 sentences but dense, and introduces facts not in the claim description (e.g., "4 claims in 12 months totalling a large sum" — this is not in the provided claim description and appears fabricated). Policy alignment to Fraud review is reasonable given the stated risk indicators, but partly rests on that unsupported claim-history assertion. Appropriate uncertainty is only "Medium" despite missing location, missing docs, blurry evidence, and unverified exclusions — "Low" would be more defensible; also asserting three fraud indicators with confidence while one (claims history) is unsupported by the input shows overconfidence._

**Reasoning (verbatim):**

> The reported event (accidental collision) is a covered peril under [Clause 1.1], and the claim was submitted within 30 days so [Clause 2.5] does not apply. However, coverage is only "Possibly covered" because several required documents are missing — driving license, vehicle registration, incident report, and adequate damage photos — making the submission materially incomplete per [Clause 3.1]. Three distinct fraud indicators under [Clause 4.3] are present: severe front-end damage supported only by a single blurry photo (weak evidence), a pattern of repeated collision claims (4 claims in 12 months totalling a large sum), and an inconsistent/vague account with no exact location and no police attendance. No exclusion under Section 2 can be definitively confirmed without further investigation (e.g., [Clause 2.1] alcohol/drug use is not addressed, [Clause 2.3] intentional damage cannot be ruled out). Per [Clause 4.3], the presence of multiple suspicious patterns mandates routing to Fraud review rather than Manual review.

### case5_late_submission

- **Coverage:** Possibly covered  (✗ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: ['driving license', 'incident report', 'reason for late submission']; missed: —)
- **Risk-flags F1:** 0.40 (matched: ['late submission']; missed: ['exclusion'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 5 |
| Appropriate uncertainty | 4 |
| **Mean** | **4.4** |

_All cited clauses (1.1, 2.5, 3.1, 4.1, 4.2, 4.3) are present in the retrieved list, so factuality is clean. The reasoning covers covered peril, late-submission exclusion, missing documents, and routing logic, and correctly notes absence of fraud indicators. Routing to manual review with Medium confidence is well-aligned with the cited rules. Minor issues: it is slightly long (6 sentences, borderline), and the claim description says "delayed submission" without specifying 45 days — the AI appears to have fabricated the exact "45 days" figure, which is a small factual overreach. Confidence level is reasonable though "Low" could also be defensible given missing docs._

**Reasoning (verbatim):**

> The reported flood damage is a covered peril under [Clause 1.1]; however, coverage cannot be confirmed as "likely" due to multiple outstanding issues. The claim was submitted 45 days after the incident, breaching the 30-day filing deadline [Clause 2.5]; as no valid reason has been provided, this alone requires manual review to determine whether an exception applies. Required documents are incomplete — the driving license copy and incident report are both absent [Clause 3.1] — meaning the conditions for standard processing under [Clause 4.1] are not met. The combination of missing documents and the unresolved late-submission issue constitutes conflicting/incomplete information, directing this claim to manual review [Clause 4.2]. No fraud indicators such as repeated claims or an inconsistent story are present, so fraud review is not warranted at this stage [Clause 4.3].

