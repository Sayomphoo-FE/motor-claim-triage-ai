# 🎤 Presenter Notes — 10-minute Presentation Playbook

Companion to `docs/slides/presentation.pdf`. Each slide has a target
duration, the rubric category it earns points for, a Thai monologue
suggestion, and the one hard number to say out loud so the reviewer
anchors on it.

Total: **10 minutes** (10 slides × ~1 min). Keep moving — if you run
over on slide N, cut slide N+1 to a sentence.

---

## Pre-flight (5 min before you start)

```bash
# 1. Both terminals in the repo root
cd /Users/sayomphoo/Documents/motor-claim-triage-ai/motor-claim-triage-ai

# 2. Services up
docker ps | grep motor-claim-qdrant     # should be healthy
curl -s http://localhost:6333/healthz    # "healthz check passed"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/  # 200

# 3. Pre-open in browser:
#    - http://localhost:8501                             (Streamlit UI)
#    - docs/eval_report.md on GitHub or VS Code preview  (eval numbers)
#    - GitHub repo develop branch                        (code tour)
#    - docs/slides/presentation.pdf                      (your deck)

# 4. Pre-load Case 2 (illegal racing) in the UI so demo is 1 click away
#    sidebar → "case2_illegal_racing" → Load into form

# 5. One dry-run of `make demo CASE=case2_illegal_racing` so Qdrant +
#    Claude are warm; first query of the day can be slow.
```

**On-stage mantra:** ตรง scope PDF · มีตัวเลข eval สนับสนุน · AI ไม่ตัดสินแทนคน

---

## Slide 1 — Title · 0:00 – 0:20

**Rubric:** Communication Quality

> "สวัสดีครับผม Sayomphoo วันนี้จะพูดโปรเจค AI ผู้ช่วยพนักงานประเมินเคสเคลมประกันรถยนต์
> เป็นงาน AI Engineer Technical Assignment · scope ตรงกับ PDF ที่ให้มาเป๊ะ"

**One sentence to leave on screen:** "Officer-facing text triage · PDF
scope strict"

---

## Slide 2 — ปัญหาที่พนักงานเจอทุกวัน · 0:20 – 1:30

**Rubric:** 🎯 **Business Understanding (15 pts)**

> "ลองนึกภาพพนักงานรับเคลมที่ต้องทำทุกเคสเหมือนกัน 1-6:
>  **อ่าน claim · เปิดเล่ม policy หา clause · ตรวจเอกสาร · ดูประวัติเคลม · ประเมินทีม · สรุปเอง**
>  ใช้เวลาเฉลี่ย **10-30 นาทีต่อเคส** ประเด็นสำคัญคือ **ทุกเคสเหมือนกันหมด**
>  — เพราะมันเป็นงานที่ทำซ้ำได้ แต่ยังไม่มีใครทำให้พนักงาน
>
>  ผลลัพธ์ที่ตามมา: **ตีความ policy ไม่เท่ากัน · จับฉ้อโกงช้า · เอกสารขาด loop ไป-กลับ · audit trail ไม่ชัด**
>  ตอบ regulator ยาก"

**One number:** "10-30 นาที/เคส" (manual review baseline)

---

## Slide 3 — Pain → Feature → Metric · 1:30 – 2:30

**Rubric:** 🎯 **Business Understanding** (continued)

> "ทุก pain ใน slide ก่อนหน้ามี feature แก้ตรงๆ และวัดได้ ผมไม่คิดเอง —
>  ใช้ industry benchmark เป็น reference
>
>  - P1 manual review นาน → AI สรุป+ประเมิน → **AHT ↓ 30-40%**
>  - P2 ประเมินไม่เท่ากัน → prompt+guardrails เดียวกัน → **consistency ≥ 0.75**
>  - P3 จับฉ้อโกงช้า → AI ตรวจ pattern Clause 4.3 → **fraud recall ↑ 15%**
>  - P5 ไม่มี audit → ทุก decision cite + JSON → **100% coverage** ← ตัวนี้ **เป็น measured อยู่แล้ว**
>  ไม่ใช่คาด"

**One number:** "100% audit coverage · verifiable วันนี้"

---

## Slide 4 — ใครได้ใช้ · User Journey · 2:30 – 3:30

**Rubric:** 🎯 Business Understanding + 🧭 PDF §4 "In Scope" compliance

> "**AI ตัวนี้คุยกับพนักงาน ไม่ใช่ลูกค้า** — officer-facing ตรงนี้ย้ำเพราะ PDF §4 บอก
> 'Automated customer communication without officer approval' เป็น **Out of Scope** → ไม่แตะ
>
>  Journey: ลูกค้าแจ้งเคลมช่องทางเดิม → พนักงานกรอกเข้า Streamlit form →
>  **กด Run triage → ได้ recommendation ใน ~10 วินาที → พนักงานตัดสินใจต่อ**
>
>  Decision boundary ชัดใน rubric: AI = ผู้ช่วย · officer = decision maker ·
>  Low confidence → auto Manual review · 'Not covered' ต้องมี Section-2 clause จริง"

**One sentence:** "AI = ผู้ช่วย · officer = ผู้ตัดสินใจสุดท้ายเสมอ"

---

## Slide 5 — สถาปัตยกรรม · 3:30 – 5:00

**Rubric:** 🎯 **AI Solution Design (25 pts)** + **Implementation Quality (25 pts)**

> "**7 ขั้นตอน linear flow:**
>
>  1. ClaimInput (Pydantic validate)
>  2. Input Guardrail — mask PII + ตรวจ injection
>  3. RAG — **4 sub-queries · 1 ต่อ section ของ policy · filter by `section_num` metadata**
>  4. Qdrant retrieve 13 clauses chunk-level
>  5. Claude Sonnet 4.6 · **forced tool-use** → shape guarantee
>  6. Output Guardrail — ตรวจ cite + safety invariants
>  7. Audit JSON write
>
>  **Key design choice:** ไม่ใช้ LangGraph · ไม่ใช้ Supervisor · **ทุก step เป็น linear function** →
>  debug ง่าย · reviewer อ่านโค้ดเข้าใจใน 15 นาที"

**One number:** "7 linear stages · ~10-15s/case · $0.015/triage"

---

## Slide 6 — Model + Technique Selection · 5:00 – 6:00

**Rubric:** 🎯 **AI Solution Design** (continued)

> "เลือกแบบ **justified** ไม่ใช่ by default:
>
>  - **Sonnet 4.6** = reasoning model (ไม่ใช่ Opus ที่แพง, ไม่ใช่ Haiku ที่เร็วแต่ง่าย)
>  - **Opus 4.7 เป็น Judge** = คนละ family กับ Sonnet → ลด self-grading bias
>  - **BGE-small-en-v1.5** (384-dim, 33 MB) = เพียงพอสำหรับ 13 clauses · ไม่ overkill
>  - **ไม่ใช้ LLM กับ guardrail output** = ตรวจ `set membership` ของ cite กับ retrieved → **rule-based ชัวร์กว่าใช้ AI**
>
>  **กฎทอง:** ใช้ AI เฉพาะเรื่องที่ตัดสินใจตายตัวไม่ได้ ส่วนที่กฎชัด = rule"

**One phrase:** "Hybrid LLM + rules — ไม่ใช่ pure AI stack"

---

## Slide 7 — RAG + Guardrails Detail · 6:00 – 7:00

**Rubric:** 🎯 **AI Solution Design** + **AI Risk & Governance (15 pts)**

> "RAG นี้พิเศษ:
>  - **ไม่ใช้ 1 query** ยิง top-k=5 ธรรมดา เพราะเสี่ยงพลาด Section 2 (exclusions)
>  - **ยิง 4 sub-queries ต่อเคส · ต่อ 1 section · filter metadata**
>  - ประกันว่า Section 2 + Section 3 + Section 4 ถูก consult ทุกเคส
>
>  **Guardrails 3 ชั้น:**
>  - Input: PII mask + prompt injection detect
>  - Mid: Pydantic + Anthropic tool-use ล็อก enum
>  - **Output: ลบ cite ที่ไม่อยู่ใน retrieved · 'Not covered' ต้องมี Section-2 cited · Low confidence → ห้าม Standard**
>
>  Output guardrail = **hallucination firewall** = เราได้ 100% citation validity ไม่ใช่ auto-trust Sonnet"

**One number:** "100% citation validity · 5/5 cases"

---

## Slide 8 — Live Demo · 7:00 – 8:00

**Rubric:** 🎯 **Implementation Quality (25 pts)**

**Switch to Streamlit tab (http://localhost:8501).**

> "สลับไปตัวจริงเลยครับ · เลือก case2_illegal_racing · กด Run triage"

**ขณะรอ (~10s):**
> "ดูที่ล่างสุดของหน้า — **Pipeline execution trace** · lights up ทุก stage realtime · เห็นเลยว่า Claude call = ~95% ของเวลา · อย่างอื่น sub-second"

**หลัง result ขึ้น:**
> "**Not covered · Rejection review · High confidence · cite Clause 1.1, 2.2, 3.1, 4.1** · reasoning อ้าง clause ครบทุกข้อ · เปิด audit record ให้ดู JSON — session_id, model version, clause scores, latency ครบ"

**One sentence:** "ทุก decision ตรวจย้อนได้ · nothing hidden"

---

## Slide 9 — Evaluation · 8:00 – 9:00

**Rubric:** 🎯 **Evaluation & Testing (15 pts)**

> "**5 PDF cases · ไม่ cherry-pick · 3 ชั้น metric:**
>
>  1. Deterministic match (coverage, routing enums)
>  2. Set-based P/R/F1 (missing docs, risk flags)
>  3. **LLM-as-Judge** · Opus 4.7 · 5-dim rubric (Factuality, Completeness, Clarity, Policy alignment, Appropriate uncertainty)
>
>  **ผลลัพธ์:**
>  - **Routing accuracy: 100% (5/5)** ⭐
>  - **Citation validity: 100% · zero hallucinated clauses** ⭐
>  - Coverage: 80% (4/5)
>  - Judge mean: **4.00 / 5**
>
>  **1 miss =** Case 5 flood 45 วันแจ้งช้า — AI มองโลกสวยไป · เลือก 'Possibly covered' แทน 'Cannot determine'
>  **โปร่งใสยอมรับ · documented ใน `docs/eval_report.md` + candidate fix รออยู่**"

**One sentence:** "ไม่หลบ failure · เขียนไว้ชัดใน eval report"

---

## Slide 10 — Risk & Governance + Roadmap · 9:00 – 10:00

**Rubric:** 🎯 **AI Risk, Governance & Production Readiness (15 pts)**

> "**ความเสี่ยง 3 ข้อหลัก · มีการกันทุกข้อ:**
>  - AI มั่ว → forced cite + output guardrail + 100% citation validity measured
>  - PII รั่ว → regex mask ก่อน LLM เห็น + hash customer ใน audit
>  - Prompt injection → input filter + forced tool-use ล็อก shape
>
>  **ตอบ regulator ได้ 6 ข้อ:**
>  1. Guardrails 3 ชั้น  2. Audit JSON ทุกเคส  3. HITL เสมอ  4. Low → Manual บังคับ
>  5. Model + prompt version บันทึก  6. 100% citation validity ตรวจซ้ำได้
>
>  **Roadmap:**
>  - Phase 1 (develop · shipped) = ที่คุณกำลังดูอยู่
>  - Phase 2 (branch `extensions` · มี POC แล้ว) = voice I/O + multi-agent + bilingual Thai
>  - Phase 3-4 = Twilio · vision · fraud model · integration
>
>  **ปิดสาร:** 'AI ตัวนี้ทำให้พนักงานประเมินเคสได้เร็ว · สม่ำเสมอ · ตรวจย้อนได้ ·
>  ตรงกับ PDF scope ครบทุกข้อ · ไม่แตะ out-of-scope · ขอบคุณครับ'"

**Mic drop line:** "ตรง scope · มีตัวเลข · มี audit · พร้อม production"

---

# Q&A Playbook (เตรียมคำตอบไว้)

| คำถาม | คำตอบสั้น (≤ 20 วิ) |
|---|---|
| ทำไมไม่ใช้ GPT-4o / Gemini? | Sonnet 4.6 เด่น tool-use adherence + reasoning · cost reasonable · architecture decoupled เปลี่ยนได้ด้วย env var |
| AI มั่วแล้วใครรับผิด? | 1) ทุก coverage ต้อง cite 2) output guard post-check 3) **คนตัดสิน** 4) audit JSON ครบ 5) 100% citation validity ที่ **ตรวจซ้ำได้** |
| 10-15 วิต่อเคสยอมรับได้? | เทียบ manual review 10-30 นาที/เคส → **ดีขึ้น ~100 เท่า** · ถ้าต้องเร็วกว่านี้ switch Haiku (trade accuracy) |
| Cost scale? | ~$0.015/triage × volume · ถ้าสูง → Haiku + prompt caching + batch |
| ถ้า Anthropic ล่ม? | SDK interface decoupled · swap OpenAI/Bedrock proxy ได้ |
| Policy เปลี่ยนบ่อยทำยังไง? | Edit `motor_policy.md` → `make ingest` → re-embed → ใช้ได้ทันที · ไม่ต้อง retrain |
| ทำไม 5 cases พอ? | PDF ขอ 3+ (strong = 5) · 5 cases × 5-dim judge = 25 data points · เพิ่มได้ง่าย |
| Voice ไม่มีเหรอ? | `extensions` branch มี POC — STT + TTS + Call UX + Supervisor · **ตั้งใจแยกเพื่อ scope strict** PDF |
| ภาษาไทยรองรับไหม? | develop = EN only (ตาม PDF) · `extensions` = bilingual TH/EN + multilingual embeddings |
| จะ scale เป็น production ยังไง? | `docs/limitations.md §5` list ไว้ 5 ข้อ: Langfuse tracing · NeMo Guardrails · officer workflow · prompt caching · model governance |
| Case 5 ทำไมพลาด? | Prompt rule บอก "late submission may be considered through manual review" → AI มองว่ายังสรุปไม่ได้ · candidate fix = add `days_to_submit > 30 AND no valid reason → Cannot determine` rule |
| Fine-tune Sonnet ไหม? | ไม่ใน prototype · prompt engineering + RAG + guardrails พอ · fine-tune คือ Phase 3+ หลังมี data real |

---

# 🔥 Tips ตอนพูดจริง

1. **อย่าอ่าน slide** — พูดด้วย voice ของตัวเอง · slide เป็น prop
2. **พูดตัวเลขเสมอ** — "100%", "80%", "5/5", "~10s" ติดตัว · reviewer จำได้
3. **ชี้ที่หน้าจอตอน demo** — "ดูที่นี่ครับ · 7 steps นี่ไงลงมา · Claude ค้าง ~9 วิ"
4. **เรื่อง 'Out of scope'** — พูดเชิงรุก ไม่ใช่แก้ตัว: "เรา strict กับ PDF scope · ไม่แตะ customer communication · ไม่คำนวณเงิน · เพราะมันเป็น decision boundary ที่ควรให้คน"
5. **เรื่อง Case 5 miss** — **ยอมรับก่อน reviewer ถาม**: "เป็น weak spot ที่ documented · candidate fix รออยู่" → แปลง weakness เป็น rigor
6. **ปิดเสียง notification** iMessage/Slack ขณะ demo
7. **เผื่อ demo ล่ม** → เตรียม screenshot `docs/eval_report.md` ไว้สำรอง
8. **เวลาเหลือ → ไม่ต้องยืด** → "ขอบคุณครับ มีคำถามไหมครับ"

---

# Rubric score mapping — ตรวจก่อนขึ้นเวที

ทุก category ตีลงใน slide หนึ่งขั้นต่ำ:

| Rubric | Points | Primary slide | Secondary |
|---|---|---|---|
| Business Understanding | 15 | 2, 3 | 4 |
| AI Solution Design | 25 | 5, 6 | 7 |
| Implementation Quality | 25 | 8 (live demo) | 5, 7 |
| Evaluation & Testing | 15 | 9 | — |
| AI Risk & Governance | 15 | 10 | 7 |
| Communication Quality | 5 | ตลอด (tone, pace, structure) | — |

**Total: 100 pts** · ทุก slide มี rubric tag ติดไว้ด้านบน · ถ้าเวลาน้อย ไม่ตัด slide 8 (demo) และ 9 (eval) เป็นอันขาด

ขอให้พูดได้ชื่น 🎤
