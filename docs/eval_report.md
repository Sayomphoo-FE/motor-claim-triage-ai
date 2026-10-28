# Evaluation Report — Motor Claim Triage Assistant

**Cases:** 14  **Triage model:** `claude-sonnet-4-6`  **Judge model:** `claude-opus-4-7`

## Executive summary

Across 14 test cases the triage agent achieves **86% coverage accuracy**, **100% routing accuracy**, and **100% citation validity**. LLM-Judge gives a mean of **4.04 / 5** on the 5-dimension reasoning rubric. Headline findings: perfect routing accuracy (14/14); zero hallucinated clause citations; 2/14 coverage calls diverged from ground truth.

## Aggregate metrics

| Metric | Value |
|---|---|
| Coverage accuracy | 86% |
| Routing accuracy | 100% |
| Confidence accuracy | 86% |
| Missing-info F1 (avg) | 0.61 |
| Risk-flags F1 (avg) | 0.72 |
| Cited-clause coverage (avg) | 0.88 |
| Citation validity (avg) | 1.00 |
| LLM-Judge mean score (0-5) | 4.04 |

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

### case1_en_parked_car

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 3.3, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.67 (matched: ['driving license', 'incident report', 'third-party contact', 'third-party evidence']; missed: ['ใบขับขี่', 'ใบรายงาน', 'ข้อมูลคู่กรณี', 'หลักฐานคู่กรณี'])
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

_All cited clauses (1.1, 2.5, 3.1, 3.3, 4.2, 4.3) are in the retrieved list, so factuality is clean. Reasoning covers covered peril, exclusions check, missing docs, and risk flags (missing third-party details, no CCTV/security report), aligning with manual review routing. Minor issues: slightly long (~6 sentences, borderline), and treating clause 2.5 as a timeliness/30-day limit is an assumption since the clause is labeled "Exclusions" — the semantic mapping may be off. Medium confidence with manual review is reasonable given missing documents, though "Low" might be more apt given absent third-party evidence. Overall a solid, well-structured triage._

**Reasoning (verbatim):**

> The incident — a third-party driver backing into a parked vehicle — falls under third-party property damage, a covered peril [Clause 1.1]. The claim was submitted within 2 days, well within the 30-day limit [Clause 2.5], and no Section 2 exclusions appear to directly apply. However, required standard documents are incomplete: the driving license copy and incident report are missing [Clause 3.1]. Additionally, third-party contact information and third-party evidence are absent, both mandatory for third-party damage claims [Clause 3.3]. The alleged note left by the at-fault driver has not been submitted, and no security report or CCTV reference is provided, representing weak supporting evidence [Clause 4.3]. Given the incomplete documentation and the need to verify third-party details, manual review is appropriate [Clause 4.2].

### case1_th_parked_car

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 3.3, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.57 (matched: ['driving license', 'incident report', 'third-party contact', 'third-party evidence']; missed: ['ใบขับขี่', 'ใบรายงาน', 'ข้อมูลคู่กรณี', 'หลักฐานคู่กรณี'])
- **Risk-flags F1:** 1.00 (matched: —; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 5 |
| Clarity | 4 |
| Policy alignment | 4 |
| Appropriate uncertainty | 3 |
| **Mean** | **4.2** |

_All six cited clauses (1.1, 2.5, 3.1, 3.3, 4.2, 4.3) are within the retrieved set, so factuality is solid. The reasoning covers the covered peril, exclusion check, missing documents, routing rationale, and fraud-flag consideration — a complete picture for the officer. Structure is logical but slightly long (~6-7 sentences, somewhat dense). Routing to manual review aligns well with the cited routing clauses, though the claim that the 2-day filing avoids Clause 2.5 is asserted without the claim description actually stating when the claim was filed — a minor alignment issue. Confidence is marked "Medium" despite significant missing facts (no filing date given, no driver identification, no CCTV, uncorroborated note); "Low" or "Cannot determine" would be more appropriate given the weak evidence base._

**Reasoning (verbatim):**

> เหตุการณ์นี้มีลักษณะเป็น Third-party property damage / Accidental collision ซึ่งเป็นความเสี่ยงที่คุ้มครองตาม [Clause 1.1] และยื่นเคลมภายใน 2 วัน จึงไม่เข้าข่ายข้อยกเว้น [Clause 2.5] อย่างไรก็ตาม เอกสารที่ยื่นมาไม่ครบตามที่กำหนด โดยขาดใบอนุญาตขับขี่และรายงานเหตุการณ์ตาม [Clause 3.1] และขาดข้อมูลติดต่อคู่กรณีและหลักฐานจากคู่กรณีตาม [Clause 3.3] เนื่องจากลูกค้าไม่ได้อยู่ในเหตุการณ์และคู่กรณีไม่อยู่ที่เกิดเหตุ มีเพียงโน้ตที่ไม่ได้แนบมา ทำให้ข้อเท็จจริงยังไม่ชัดเจนเพียงพอ ซึ่งอาจเข้าข่าย "severe damage reported with weak or missing supporting evidence" ตาม [Clause 4.3] แต่ยังไม่มีข้อมูลเพียงพอที่จะส่ง Fraud review ได้อย่างแน่ชัด ดังนั้น การส่งเรื่องไปยัง Manual review ตาม [Clause 4.2] จึงเหมาะสมที่สุด เพื่อให้เจ้าหน้าที่รวบรวมเอกสารเพิ่มเติมและตรวจสอบหลักฐานจากกล้องวงจรปิดหรือ รปภ. ของห้างก่อนตัดสินใจ

### case2_en_illegal_racing

- **Coverage:** Not covered  (✓ vs ground truth)
- **Routing:** Rejection review  (✓ vs ground truth)
- **Confidence:** High  (✓)
- **Cited clauses:** 1.1, 2.2, 3.1, 3.2, 4.1, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: —; missed: —)
- **Risk-flags F1:** 0.29 (matched: ['exclusion']; missed: ['illegal racing', 'แข่งรถ', 'ข้อยกเว้น'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 3 |
| Policy alignment | 5 |
| Appropriate uncertainty | 5 |
| **Mean** | **4.4** |

_All cited clauses (1.1, 2.2, 3.1, 3.2, 4.1, 4.3) are in the retrieved list, so factuality is clean. The reasoning correctly identifies the covered peril, applies the illegal-racing exclusion, confirms documents, and routes to Rejection review — well aligned with policy. High confidence is justified given the explicit admission to police. Minor issues: the reasoning is slightly verbose and contains filler (e.g., the parenthetical on 4.2 which wasn't even cited in the citation list but is mentioned in prose, and the fraud comment on 4.3 is thin). Completeness is good but could more explicitly flag the admission-of-illegal-activity as a potential legal/subrogation risk. Overall a solid, well-grounded triage._

**Reasoning (verbatim):**

> The incident is a collision, which is ordinarily a covered peril [Clause 1.1]; however, the customer's own statement to police explicitly confirms participation in an illegal street race at the time of the crash. This directly and unambiguously triggers the exclusion for damage arising from illegal racing [Clause 2.2], rendering the claim not covered. All standard required documents are present [Clause 3.1], and the police report further corroborates the excluded activity [Clause 3.2]. Because a clear Section 2 exclusion applies, routing to Rejection review is appropriate per the routing rules [Clause 4.1 conditions not met; Clause 4.2 not applicable as coverage is not merely unclear but excluded]. No prior claims history is noted, so no additional fraud pattern is flagged beyond the exclusion itself [Clause 4.3].

### case2_th_illegal_racing

- **Coverage:** Not covered  (✓ vs ground truth)
- **Routing:** Rejection review  (✓ vs ground truth)
- **Confidence:** High  (✓)
- **Cited clauses:** 1.1, 2.2, 3.1
- **Citation validity:** 1.00
- **Missing-info F1:** 1.00 (matched: —; missed: —)
- **Risk-flags F1:** 0.67 (matched: ['แข่งรถ', 'ข้อยกเว้น']; missed: ['illegal racing', 'exclusion'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 5 |
| Appropriate uncertainty | 5 |
| **Mean** | **4.6** |

_All cited clauses (1.1, 2.2, 3.1) are within the retrieved list. The reasoning correctly identifies the illegal street racing exclusion (2.2) overriding the accidental collision coverage (1.1) and routes to Rejection review — consistent with the facts (customer admitted racing to police). High confidence is appropriate given the explicit police confession. Minor gaps: could have noted a specific routing clause (4.1/4.2/4.3) to justify Rejection review path, and the document completeness claim under 3.1 is asserted without evidence that all docs were actually submitted. Otherwise concise and well-structured._

**Reasoning (verbatim):**

> เหตุการณ์ที่เกิดขึ้นเป็นการชนแบริเออร์คอนกรีต ซึ่งโดยทั่วไปอาจถือเป็น accidental collision ตาม [Clause 1.1] อย่างไรก็ตาม ลูกค้าได้ให้การยืนยันกับเจ้าหน้าที่ตำรวจที่เกิดเหตุอย่างชัดเจนว่ากำลังร่วมแข่งรถผิดกฎหมายขณะเกิดเหตุ ซึ่งทำให้ข้อยกเว้น [Clause 2.2] มีผลบังคับใช้โดยตรง เนื่องจากความเสียหายเกิดจากการมีส่วนร่วมในการแข่งรถผิดกฎหมาย การประกันจึงไม่คุ้มครองความเสียหายนี้ตาม [Clause 2.2] เอกสารที่ยื่นมาครบถ้วนตาม [Clause 3.1] แต่ข้อยกเว้นมีผลบังคับอย่างชัดเจนจึงไม่มีผลต่อการตัดสินใจ ควรส่งเรื่องไปยัง Rejection review เนื่องจากข้อยกเว้นในมาตรา Section 2 มีผลบังคับใช้อย่างชัดเจน

### case3_en_theft_no_police

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 3.2, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.67 (matched: ['police report', 'incident report', 'driving license', 'photos of damage']; missed: ['ใบแจ้งความ', 'ใบรายงาน', 'ใบขับขี่', 'รูปถ่าย'])
- **Risk-flags F1:** 1.00 (matched: —; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 4 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 4 |
| Appropriate uncertainty | 4 |
| **Mean** | **4.0** |

_All cited clauses (1.1, 2.5, 3.1, 3.2, 4.2, 4.3) are within the retrieved set, so factuality holds — though 4.3 is listed in the citation header but never actually referenced in the reasoning body, a minor inconsistency. Completeness is good: covers peril, documents, police report, timing, and routing rationale, though risk flags (overnight theft window, condo parking) could have been mentioned explicitly. Clarity is solid and within the sentence budget. Routing to Manual review with Medium confidence is well-aligned with cited clauses and appropriately cautious given the missing police report, which is a key gating fact. Minor overconfidence in asserting "no exclusions...clearly apply" without having checked unlisted exclusion clauses (2.2, 2.4) that were retrieved but not evaluated._

**Reasoning (verbatim):**

> The reported incident (vehicle theft) is a covered peril under [Clause 1.1]. However, the claim cannot be assessed as "Likely covered" because required documents are substantially incomplete [Clause 3.1]: the driving license, photos, and incident report are missing. Critically, a police report — mandatory for all theft claims — has not been filed or submitted [Clause 3.2]. The claim was submitted within 30 days of the incident (6 days), so no late-submission exclusion applies [Clause 2.5]. No exclusions under Section 2 appear to clearly apply based on the facts provided. Per [Clause 4.2], the combination of incomplete required documents and the missing police report warrants routing to Manual review until all outstanding documents are obtained.

### case3_th_theft_no_police

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.4, 2.5, 3.1, 3.2, 4.1, 4.2
- **Citation validity:** 1.00
- **Missing-info F1:** 0.62 (matched: ['police report', 'incident report', 'ใบขับขี่', 'รูปถ่าย']; missed: ['driving license', 'photos of damage', 'ใบแจ้งความ', 'ใบรายงาน'])
- **Risk-flags F1:** 1.00 (matched: —; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 4 |
| Completeness | 3 |
| Clarity | 4 |
| Policy alignment | 3 |
| Appropriate uncertainty | 3 |
| **Mean** | **3.4** |

_Reasoning cites Clauses 1.1, 2.4, 2.5, 3.1, 3.2, 4.1, 4.2. All appear in the retrieved list, so no outright hallucinated clause IDs — however, Clause 2.5 is labeled "Exclusions" in the retrieval list, but the AI uses it as a filing-deadline rule (30 days), which likely misrepresents what the clause actually says. Similarly 2.4 is listed as cited at the top but never actually discussed in the reasoning body. Completeness: covers covered peril, missing docs (police report), and routing, but does not meaningfully address applicable exclusions (2.2/2.4) such as whether leaving car in a condo lot overnight triggers any exclusion, nor risk flags (delay in filing police report is a fraud indicator). Clarity is good — concise and structured within ~6 sentences. Policy alignment: routing to manual review pending police report is sensible, but the invocation of 2.5 as a deadline clause when it's labeled an exclusion weakens alignment. Uncertainty: "Medium" confidence is arguably too high given no police report exists yet to corroborate the theft — "Low" would be more appropriate; also no fraud/risk flag raised about the customer not yet filing a police report._

**Reasoning (verbatim):**

> เหตุการณ์รถถูกขโมยตรงกับกรณีที่กรมธรรม์คุ้มครอง (Theft) [Clause 1.1] และยื่นเคลมภายใน 6 วัน ซึ่งไม่เกินกำหนด 30 วัน [Clause 2.5] อย่างไรก็ตาม เอกสารที่ส่งมามีเพียงแบบฟอร์มเคลมและทะเบียนรถ ยังขาดสำเนาใบขับขี่ รูปถ่าย รายงานเหตุการณ์ [Clause 3.1] และรายงานตำรวจซึ่งบังคับสำหรับเคลมประเภทการโจรกรรม [Clause 3.2] การที่ลูกค้ายังไม่ได้แจ้งความถือเป็นเอกสารสำคัญที่ขาดหายไปและอาจทำให้ไม่สามารถยืนยันข้อเท็จจริงของเหตุการณ์ได้ เนื่องจากเอกสารไม่ครบถ้วน จึงไม่สามารถผ่านเงื่อนไขของ [Clause 4.1] ได้ และควรส่งเรื่องเข้า Manual review ตาม [Clause 4.2] เพื่อให้เจ้าหน้าที่ติดตามเอกสารที่ขาดหาย โดยเฉพาะรายงานตำรวจ ก่อนดำเนินการต่อ

### case4_en_fraud_risk

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Fraud review  (✓ vs ground truth)
- **Confidence:** High  (✗)
- **Cited clauses:** 1.1, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.29 (matched: ['driving license', 'incident report']; missed: ['clear photo', 'police report', 'ใบขับขี่', 'ใบรายงาน', 'รูปถ่ายชัด', 'ใบแจ้งความ'])
- **Risk-flags F1:** 0.18 (matched: ['repeated claims']; missed: ['weak evidence', 'severe damage', 'เคลมซ้ำ', 'หลักฐานอ่อน', 'ความเสียหายรุนแรง'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 4 |
| Completeness | 3 |
| Clarity | 3 |
| Policy alignment | 4 |
| Appropriate uncertainty | 2 |
| **Mean** | **3.2** |

_All cited clauses (1.1, 3.1, 4.1, 4.2, 4.3) are within the retrieved set, so factuality is largely fine — though the reasoning asserts a specific claims history ("4 claims within 12 months — 3 collision") that is not present in the claim description, which is a factual fabrication that undermines this dimension. Completeness is partial: it covers covered peril, missing documents, and risk flags, but does not address potentially relevant exclusions (e.g., 2.2/2.4/2.5, such as night-time/unreported-to-police scenarios) that were retrieved. Clarity is borderline — the reasoning runs ~6 sentences but is dense and somewhat repetitive on Clause 4.3. Policy alignment to Fraud Review is reasonable given weak evidence and inconsistent story, consistent with 4.3. The biggest weakness is appropriate uncertainty: confidence is marked "High" despite missing location, missing documents, and a fabricated claims-history fact — this should be Low or "Cannot determine." Overall the output is directionally sensible but overconfident and partially hallucinated._

**Reasoning (verbatim):**

> The reported event (accidental collision) is a covered peril under [Clause 1.1], so coverage is not categorically excluded; however, the submission is critically incomplete, missing the driving license, vehicle registration, incident report, and adequate damage photos required by [Clause 3.1]. The single blurry photo constitutes weak supporting evidence for severe front-end damage, triggering the "severe damage with weak or missing supporting evidence" pattern under [Clause 4.3]. Additionally, the customer has filed 4 claims within 12 months — 3 of which are collision claims — satisfying the "repeated claims from the same customer over a short period" flag under [Clause 4.3]. The customer's inability to provide the exact incident location further raises story consistency concerns consistent with [Clause 4.3]. At least two independent Clause 4.3 fraud patterns are present, making Fraud Review the appropriate routing ahead of any Manual Review consideration under [Clause 4.2]. Standard processing under [Clause 4.1] is not applicable given the missing documents and multiple risk flags.

### case4_th_fraud_risk

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Fraud review  (✓ vs ground truth)
- **Confidence:** High  (✗)
- **Cited clauses:** 1.1, 2.1, 2.4, 2.5, 3.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.29 (matched: ['incident report', 'ใบขับขี่']; missed: ['driving license', 'clear photo', 'police report', 'ใบรายงาน', 'รูปถ่ายชัด', 'ใบแจ้งความ'])
- **Risk-flags F1:** 0.44 (matched: ['severe damage', 'เคลมซ้ำ', 'ความเสียหายรุนแรง']; missed: ['repeated claims', 'weak evidence', 'หลักฐานอ่อน'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 3 |
| Policy alignment | 4 |
| Appropriate uncertainty | 2 |
| **Mean** | **3.6** |

_All cited clauses (1.1, 2.1, 2.4, 2.5, 3.1, 4.2, 4.3) appear in the retrieved list, so factuality is clean. The response covers covered peril, missing documents, risk flags, and exclusions reasonably well. However, it fabricates a fact not in the claim description — "ประวัติการเคลม 4 ครั้งในรอบ 12 เดือน" was never stated, which is a significant hallucination of case facts (even if the clause citation itself is valid) and undermines appropriate uncertainty. Confidence is marked "High" despite blurry photo, unknown location, and unknown driver condition — this should have been Low/Cannot determine. Reasoning is also slightly long and dense (~6+ sentences packed together). Routing to Fraud review is defensible given weak evidence, so policy alignment is largely sound._

**Reasoning (verbatim):**

> เหตุการณ์ชนเสาไฟเข้าข่ายอุบัติเหตุที่คุ้มครองตาม [Clause 1.1] และยื่นเคลมภายในกำหนด จึงไม่มีปัญหาตาม [Clause 2.5] อย่างไรก็ตาม เอกสารที่ยื่นมายังขาดอีกหลายรายการตาม [Clause 3.1] ได้แก่ สำเนาใบขับขี่ ทะเบียนรถ และรายงานเหตุการณ์ ทำให้ยังไม่ครบถ้วน อีกทั้งรูปถ่ายเพียง 1 รูปที่เบลอและระบุสถานที่ไม่ได้ถือเป็นหลักฐานที่อ่อนมากสำหรับความเสียหายรุนแรง ซึ่งเข้าข่ายรูปแบบ "Severe damage with weak or missing supporting evidence" ตาม [Clause 4.3] นอกจากนี้ประวัติการเคลม 4 ครั้งในรอบ 12 เดือนยังเข้าข่าย "Repeated claims from the same customer over a short period" ตาม [Clause 4.3] อีกด้วย ยังไม่สามารถยืนยันพื้นที่เกิดเหตุตาม [Clause 2.4] และสภาพผู้ขับขี่ตาม [Clause 2.1] ได้ ด้วยสัญญาณเสี่ยงหลายข้อตาม [Clause 4.3] จึงแนะนำให้ส่งเรื่องไปที่ Fraud review ก่อนดำเนินการใดๆ

### case5_en_late_submission

- **Coverage:** Possibly covered  (✗ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.67 (matched: ['driving license', 'incident report', 'reason for late submission']; missed: ['ใบขับขี่', 'ใบรายงาน', 'เหตุผลที่แจ้งล่าช้า'])
- **Risk-flags F1:** 0.50 (matched: ['late submission', 'exclusion']; missed: ['แจ้งล่าช้า', 'ข้อยกเว้น'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 5 |
| Clarity | 4 |
| Policy alignment | 5 |
| Appropriate uncertainty | 4 |
| **Mean** | **4.6** |

_All cited clauses (1.1, 2.5, 3.1, 4.1, 4.2, 4.3) are within the retrieved set — no hallucinations. The reasoning covers the covered peril (flood), the key exclusion risk (late submission beyond 30 days with no reason), missing documents (license, incident report), and a severity/evidence risk flag, which is comprehensive for the officer. Routing to manual review with Medium confidence is well-aligned with the cited clauses given the unresolved late-submission issue and documentation gaps. Clarity is good and structured, though slightly over the ~6 sentence target and a touch wordy. Uncertainty is reasonable (Medium), though given the hard 30-day deadline breach with no justification, "Likely not covered" or Low confidence might have been more calibrated than "Possibly covered / Medium."_

**Reasoning (verbatim):**

> The reported event (flood damage while the vehicle was parked) matches the covered peril of flood under [Clause 1.1]. However, required documents are incomplete: a driving license copy and incident report are missing as mandated by [Clause 3.1], triggering manual review under [Clause 4.2]. More critically, the claim was submitted 45 days after the incident, exceeding the 30-day deadline under [Clause 2.5], and no valid reason has been offered for the delay — this may result in the claim not being covered unless a valid reason is subsequently provided. Severe engine damage is reported with only partial supporting evidence (photos and registration), which also raises a concern under [Clause 4.3]. Because documents are incomplete and a potential late-submission exclusion is unresolved, standard processing is not appropriate per [Clause 4.1]. Manual review is warranted to allow the officer to evaluate whether a valid reason for late submission exists and to collect the missing documents.

### case5_th_late_submission

- **Coverage:** Possibly covered  (✗ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 4.2
- **Citation validity:** 1.00
- **Missing-info F1:** 0.57 (matched: ['driving license', 'incident report', 'ใบขับขี่']; missed: ['reason for late submission', 'ใบรายงาน', 'เหตุผลที่แจ้งล่าช้า'])
- **Risk-flags F1:** 0.00 (matched: —; missed: ['late submission', 'exclusion', 'แจ้งล่าช้า', 'ข้อยกเว้น'])

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 4 |
| Appropriate uncertainty | 3 |
| **Mean** | **4.0** |

_All cited clauses (1.1, 2.5, 3.1, 4.2) are in the retrieved list, so factuality is solid. The reasoning covers the covered peril (flood), the late-filing exclusion, missing documents, and routing — a reasonably complete picture, though it doesn't explicitly flag risk concerns like parked-on-street or potential engine-damage sub-exclusions. Writing is concise and structured within ~5 sentences. Routing to Manual review is consistent with the late filing + missing docs scenario. However, the claim description says the customer did NOT provide a reason for late filing, yet the reasoning invents a "45 days late" figure not present in the input — this is an unsupported factual assumption that should have warranted Low confidence rather than Medium. Appropriate uncertainty is therefore weak._

**Reasoning (verbatim):**

> เหตุการณ์น้ำท่วมรถตรงกับความเสี่ยงที่ได้รับความคุ้มครองตาม [Clause 1.1] (Flood) อย่างไรก็ตาม ลูกค้ายื่นเคลมล่าช้า 45 วัน ซึ่งเกินกำหนด 30 วันโดยไม่มีเหตุผลประกอบ ซึ่งอาจเป็นเหตุยกเว้นความคุ้มครองตาม [Clause 2.5] แต่หากมีเหตุผลที่ถูกต้อง สามารถพิจารณาผ่าน Manual review ได้ตาม [Clause 2.5] เช่นกัน นอกจากนี้ เอกสารที่ยื่นมายังไม่ครบถ้วนตาม [Clause 3.1] เนื่องจากขาดใบขับขี่และรายงานเหตุการณ์ ด้วยเหตุที่เอกสารไม่ครบและมีประเด็นเรื่องการยื่นล่าช้าที่ยังไม่ได้รับการชี้แจง การส่ง Manual review จึงเป็นเส้นทางที่เหมาะสมตาม [Clause 4.2]

### case6_en_gear_cable

- **Coverage:** Cannot determine  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Low  (✓)
- **Cited clauses:** 1.1, 3.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.44 (matched: ['incident report', 'driving license']; missed: ['mechanic report', 'ใบรายงาน', 'ใบขับขี่', 'ใบตรวจสภาพ'])
- **Risk-flags F1:** 1.00 (matched: —; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 3 |
| Clarity | 4 |
| Policy alignment | 4 |
| Appropriate uncertainty | 5 |
| **Mean** | **4.2** |

_All cited clauses (1.1, 3.1, 4.2, 4.3) are within the retrieved set, so factuality is clean. Uncertainty is handled well with "Cannot determine" and Low confidence given ambiguous facts. However, completeness is weak: the retrieved set includes multiple Exclusions clauses (2.3, 2.4, 2.5) that likely cover mechanical/wear-and-tear failures — a gear cable snap is a textbook mechanical breakdown exclusion, and the reasoning fails to address or even consider any exclusion clause. It also omits mention of other required-document clauses (3.2, 3.3). Routing to Manual review is reasonable and consistent with cited rules, though a stronger analysis might have supported denial via exclusions. Clarity is good — structured and roughly within the length limit, with only minor fluff._

**Reasoning (verbatim):**

> The incident involves a gear cable failure during a routine driveway manoeuvre; this does not clearly map to any covered peril under [Clause 1.1] (accidental collision, theft, fire, flood, or third-party property damage), making coverage ambiguous. It is possible the cable snapped due to an accidental collision impact or sudden mechanical event, but the description alone is insufficient to confirm this. Required documents are incomplete — a driving license copy and an incident report are missing [Clause 3.1]. Because coverage is unclear and required documents are incomplete, [Clause 4.2] directs this claim to Manual review. Additionally, a vehicle rendered fully immobile with only photos as supporting evidence is a mild flag under [Clause 4.3], though the customer's clean 24-month claim history reduces fraud concern. The claim officer should seek a mechanical inspection report and clarification on whether any external accidental force caused the cable failure.

### case6_th_gear_cable

- **Coverage:** Cannot determine  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Low  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.50 (matched: ['incident report', 'driving license', 'ใบขับขี่']; missed: ['mechanic report', 'ใบรายงาน', 'ใบตรวจสภาพ'])
- **Risk-flags F1:** 1.00 (matched: —; missed: —)

**LLM-Judge:**

| Dim | Score |
|---|---|
| Factuality | 5 |
| Completeness | 4 |
| Clarity | 4 |
| Policy alignment | 4 |
| Appropriate uncertainty | 5 |
| **Mean** | **4.4** |

_All cited clauses (1.1, 2.5, 3.1, 4.2, 4.3) are within the retrieved list, so factuality is clean. The reasoning identifies the key issue (mechanical failure vs accidental collision), missing documents, timing, and fraud flags, though it could have more directly addressed Clause 2.4/2.2 which likely contain the mechanical-failure/wear-and-tear exclusion most relevant here — a notable gap in completeness and policy alignment. Uncertainty is handled well with "Cannot determine" and Low confidence given the ambiguity. Clarity is good but slightly verbose and the mention of 2.5 (likely a late-reporting exclusion) feels tangential. Overall a solid but not perfect triage._

**Reasoning (verbatim):**

> เหตุการณ์ที่ลูกค้าอธิบายคือสายเกียร์ขาดขณะเปลี่ยนเกียร์ ซึ่งยังไม่ชัดเจนว่าเข้าข่าย "Accidental collision" ตาม [Clause 1.1] หรือเป็นความเสียหายเชิงกลไก (Mechanical Failure) ที่อาจไม่อยู่ในความคุ้มครอง จึงไม่สามารถระบุความคุ้มครองได้อย่างมั่นใจ เอกสารที่ส่งมายังไม่ครบถ้วนตาม [Clause 3.1] โดยขาดใบขับขี่และรายงานเหตุการณ์ (Incident Report) การยื่นเคลมภายใน 1 วันไม่ถือว่าล่าช้า จึงไม่มีประเด็นตาม [Clause 2.5] และลูกค้าไม่มีประวัติเคลมซ้ำในรอบ 24 เดือน จึงยังไม่มีสัญญาณฉ้อโกงตาม [Clause 4.3] อย่างไรก็ตาม เนื่องจากความคุ้มครองยังไม่ชัดเจนและเอกสารไม่ครบ จึงควรส่งเรื่องเข้า Manual review ตาม [Clause 4.2] พร้อมขอรายงานจากช่างเพื่อยืนยันสาเหตุของความเสียหาย

### case7_en_skirt_crack

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.67 (matched: ['incident report']; missed: ['ใบรายงาน'])
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

_All cited clauses (1.1, 2.5, 3.1, 4.1, 4.2, 4.3) exist in the retrieved set, so factuality is clean. Completeness is good: covers peril (pothole as accidental collision), exclusion check, missing incident report, claim-history risk flag — though it doesn't explicitly consider other exclusion clauses (2.3, 2.4) that were retrieved and could be relevant (e.g., wear/tear or road-hazard exclusions). Clarity suffers slightly — the reasoning runs ~6 sentences but is dense and includes some fluff (e.g., forward-looking re-routing statement). Policy alignment is reasonable: routing to manual review due to missing documents aligns with 4.2, and "Possibly covered" is a defensible call. Uncertainty is only partially appropriate — classifying a pothole impact as a clear "accidental collision" under 1.1 without seeing the clause text is somewhat overconfident, and "Medium" confidence may be slightly high given the missing incident report and unverified peril classification; "Low" might be more suitable._

**Reasoning (verbatim):**

> The incident of hitting a pothole and sustaining accidental damage to the front skirt qualifies as an accidental collision under [Clause 1.1]. The claim was submitted within 4 days, well within the 30-day window, so [Clause 2.5] does not apply, and no other exclusions under Section 2 appear directly applicable. However, the submitted documents (Claim form, Vehicle registration, Photos of damage, Copy of driving license) are missing the Incident report, which is a mandatory requirement for all claims under [Clause 3.1]. Because required documents are incomplete, coverage is assessed as "Possibly covered" rather than "Likely covered," and the claim must be routed to Manual review per [Clause 4.2]. The customer's claim history (1 claim in 24 months for an unrelated windshield replacement) does not trigger any fraud patterns under [Clause 4.3]. Once the incident report is submitted and verified, the claim may be re-routed to Standard processing if all [Clause 4.1] conditions are met.

### case7_th_skirt_crack

- **Coverage:** Possibly covered  (✓ vs ground truth)
- **Routing:** Manual review  (✓ vs ground truth)
- **Confidence:** Medium  (✓)
- **Cited clauses:** 1.1, 2.5, 3.1, 4.1, 4.2, 4.3
- **Citation validity:** 1.00
- **Missing-info F1:** 0.67 (matched: ['incident report']; missed: ['ใบรายงาน'])
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

_All cited clauses (1.1, 2.5, 3.1, 4.1, 4.2, 4.3) are within the retrieved list, so factuality is clean. The reasoning covers peril (collision with pothole → 1.1), exclusions check (2.5 timing), missing document (incident report per 3.1), and routing logic (4.1 → 4.2). However, it does not explicitly check other retrieved exclusions (2.2, 2.4) before concluding "no exclusion applies," which weakens completeness and policy alignment slightly. Clarity is good—structured and within length. Confidence is marked Medium, which is reasonable, but asserting the event is Accidental collision without seeing scene photos / incident report is somewhat overconfident given the missing documentation; "Cannot determine" or Low might be more appropriate until the incident report is received. The 4-day vs 30-day framing is helpful but assumes 2.5 is specifically a notification deadline, which is plausible but not verified in the snippet._

**Reasoning (verbatim):**

> เหตุการณ์ที่รายงาน (รถชนหลุมบนถนนจนชิ้นส่วนเสียหาย) เข้าข่ายเป็น Accidental collision ซึ่งเป็นเหตุการณ์ที่ได้รับความคุ้มครอง [Clause 1.1] และไม่ปรากฏว่ามีข้อยกเว้นใดใน Section 2 ที่ใช้บังคับได้อย่างชัดเจน การยื่นเคลมภายใน 4 วันถือว่าอยู่ภายในกรอบ 30 วัน จึงไม่ขัดกับ [Clause 2.5] อย่างไรก็ตาม เอกสารที่ยื่นมาขาด Incident report ซึ่งเป็นเอกสารบังคับตาม [Clause 3.1] ทำให้เอกสารไม่ครบถ้วน เนื่องจากเงื่อนไขของ [Clause 4.1] กำหนดให้เอกสารต้องครบถ้วนจึงจะเข้าสู่ Standard processing ได้ กรณีนี้จึงต้องถูกส่งไปยัง Manual review ตาม [Clause 4.2] เพื่อให้เจ้าหน้าที่ขอเอกสารที่ขาดหายก่อนดำเนินการต่อ

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

