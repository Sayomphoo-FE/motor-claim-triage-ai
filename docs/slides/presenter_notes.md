# 🎤 Presenter Notes — 10-minute Presentation Playbook

Companion to `docs/slides/presentation.pdf` **(reworked layout, 2026-10-30)**.
Deck is now **11 slides** = title + 10 sections (Risk and Roadmap split
into 2 slides). Each note below has: target duration · rubric category ·
Thai monologue suggestion · the one hard number to say out loud · the
visual element on the slide to point at.

Total: **10 minutes**. Pacing is tight — if you run over, cut the next
slide to a single sentence, don't skip entirely.

---

## Pre-flight (5 min before you start)

```bash
# 1. Both terminals in the repo root
cd /Users/sayomphoo/Documents/motor-claim-triage-ai/motor-claim-triage-ai

# 2. Services up (verify green before you walk on stage)
docker ps | grep motor-claim-qdrant             # should be healthy
curl -s http://localhost:6333/healthz            # "healthz check passed"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/   # 200

# 3. Pre-open in browser tabs (in this order so Cmd+1..4 jumps):
#    tab 1 — http://localhost:8501                            Streamlit UI
#    tab 2 — docs/eval_report.md on GitHub or VS Code         eval numbers
#    tab 3 — github.com/.../tree/develop                      code tour
#    tab 4 — docs/slides/presentation.pdf                     your deck

# 4. Pre-load Case 2 (illegal racing) in the UI so demo is 1 click away
#    sidebar → "case2_illegal_racing" → Load into form

# 5. One warm-up `make demo CASE=case2_illegal_racing` so Qdrant +
#    Claude are hot; first query of the day can take ~15s.
```

**On-stage mantra:** ตรง scope PDF · มีตัวเลข eval สนับสนุน · AI ไม่ตัดสินแทนคน

---

## Slide 1 — Title · 0:00 – 0:15

**Rubric:** Communication Quality · **Visual to point at:** subtitle `scope ตรงกับ Assignment PDF — Officer-facing text triage`

> "สวัสดีครับผม Sayomphoo วันนี้จะนำเสนอโปรเจค **AI ผู้ช่วยพนักงานประเมินเคสเคลมประกันรถยนต์**
>  งาน AI Engineer Technical Assignment · scope ตรงกับ PDF เป๊ะ · 10 นาที"

**One line to leave:** "Officer-facing · text triage · PDF strict"

---

## Slide 2 — ปัญหาที่พนักงานเจอทุกวัน · 0:15 – 1:15

**Rubric:** 🎯 **Business Understanding (15 pts)**
**Visual:** 📋 card (6 steps of manual review) → ⏱ big-stat **10-30 นาที/เคส** → 2-column consequences

> "ลองนึกภาพพนักงานรับเคลมที่ต้องทำทุกเคสเหมือนกัน:
>  **อ่าน claim · เปิดเล่ม policy · ตรวจเอกสาร · ดูประวัติเคลม · ตัดสินใจ routing · สรุปใน CRM**
>
>  ตัวเลขที่น่าสนใจคือ **ชี้ที่ 10-30 นาที/เคส** — manual review ใช้เวลาเท่านี้ทั้งที่งานซ้ำได้หมด
>
>  ผลที่ตามมา 6 ข้อ · ชี้ที่ 2 columns · **ตีความไม่เท่ากัน · จับฉ้อโกงช้า · เอกสาร loop · audit ไม่ชัด · ตอบ regulator ยาก · เคสง่าย/ยากปนคิว**"

**One number:** **"10-30 นาที/เคส"**

---

## Slide 3 — Pain → Feature → Metric · 1:15 – 2:10

**Rubric:** 🎯 **Business Understanding** (continued)
**Visual:** 6-row table + ⭐ caveat line ใต้ตาราง

> "ทุก pain มี feature แก้ตรงๆ และ **วัดได้**
>
>  P1-P4 เป็น industry benchmark projections — ต้อง A/B test ตอน production
>  **P5 กับ P6 มีดาวครับ** — ชี้ที่ **100% audit coverage** และ **100% routing accuracy** ⭐
>  เราได้ **ตัวเลขนี้วันนี้** บน 5 PDF cases · ตรวจซ้ำได้ที่ `docs/eval_report.md`"

**One phrase:** "projection + measured · โปร่งใสแยกให้ชัด"

---

## Slide 4 — User Journey (Officer-facing) · 2:10 – 3:10

**Rubric:** 🎯 Business Understanding + PDF §4 compliance
**Visual:** 2-card decision boundary — **แดง (ไม่ทำ)** vs **เทา (ทำ)**

> "**AI ตัวนี้คุยกับพนักงาน ไม่ใช่ลูกค้า** — officer-facing ตรงนี้ย้ำ
>  เพราะ PDF §4 บอก 'Automated customer communication without officer approval' เป็น **Out of Scope** → ไม่แตะ
>
>  Decision boundary ชัด · ชี้ที่ card แดง · AI **ไม่** approve/reject · ไม่คำนวณเงิน · ไม่สื่อสารลูกค้าตรง
>  ชี้ที่ card เทา · AI สรุปเคส · cite clause · Low confidence → Manual review อัตโนมัติ · 'Not covered' ต้องมี Section-2 clause จริง"

**One sentence:** "AI = ผู้ช่วย · officer = decision maker ตลอดทาง"

---

## Slide 5 — สถาปัตยกรรม · 3:10 – 4:30

**Rubric:** 🎯 **AI Solution Design (25 pts)** + **Implementation Quality (25 pts)**
**Visual:** flowchart 6 stages + กฎทอง card

> "**6 ขั้นตอน linear flow:**
>
>  ชี้ที่ diagram · ClaimInput → **Input Guardrail** (PII mask + injection) → **RAG** (4 sub-queries · section-filtered) → **Claude Sonnet 4.6** (forced tool-use) → **Output Guardrail** (ตรวจ cite + safety) → **TriageOutput + Audit JSON**
>
>  **Key design choice:** ไม่ใช้ LangGraph · ไม่ใช้ Supervisor · ทุก step เป็น linear function
>  → debug ง่าย · reviewer อ่านโค้ดเข้าใจใน 15 นาที
>
>  **กฎทอง:** ใช้ AI เฉพาะงานตัดสินใจตายตัวไม่ได้ · ส่วนที่กฎชัด (ตรวจ cite) = rule-based ชัวร์กว่า"

**One number:** "6 linear stages · ~10-15s/case · $0.015/triage"

---

## Slide 6 — Model + Technique · 4:30 – 5:25

**Rubric:** 🎯 **AI Solution Design** (continued)
**Visual:** 5-row justification table + blue callout card

> "เลือกแบบ **justified** ไม่ใช่ by default · ชี้ที่ตาราง:
>
>  - **Sonnet 4.6** = reasoning + tool-use adherence สูง + Thai ดี
>  - **Opus 4.7 เป็น Judge** = คนละ family กับ Sonnet → ลด self-grading bias
>  - **BGE-small-en-v1.5** (384-dim, 33 MB) = พอสำหรับ 13 clauses · ไม่ overkill
>  - **Qdrant** = metadata filter per-section · docker-friendly
>  - **Structured output** = tool-use + Pydantic = enum ผิดไม่ได้
>
>  ชี้ที่ blue card · **'ไม่ใช้ LLM กับทุกอย่าง'** — Guardrail output = `set membership check` = rule-based ประหยัดและไม่มั่ว"

**One phrase:** "Hybrid LLM + rules — ไม่ใช่ pure AI stack"

---

## Slide 7 — RAG + Guardrails Detail · 5:25 – 6:25

**Rubric:** 🎯 **AI Solution Design** + **AI Risk & Governance (15 pts)**
**Visual:** 2-column numbered lists (5 vs 3 items) + bottom result card

> "RAG นี้พิเศษ · ชี้ที่คอลัมน์ซ้าย:
>  - **ไม่ใช้ 1 query** top-k=5 ธรรมดา เพราะเสี่ยงพลาด Section 2 (exclusions)
>  - **4 sub-queries ต่อเคส · ต่อ 1 section · filter metadata** → ประกัน Section 2 + 3 + 4 ถูก consult ทุกเคส
>
>  ชี้ที่คอลัมน์ขวา · **Guardrails 3 ชั้น:**
>  - Input: PII mask + prompt injection
>  - Mid: Pydantic + tool_choice ลงเล็ม shape
>  - Output: **hallucination firewall** — ลบ cite ที่ไม่ใช่ retrieved · 'Not covered' ต้องมี Section-2 · Low → Manual
>
>  ชี้ที่ bottom card · **ผลลัพธ์:** Citation validity 100% บน 5 cases · zero hallucinated clauses"

**One number:** **"100% citation validity · 5/5 cases"**

---

## Slide 8 — Live Demo · 6:25 – 7:25

**Rubric:** 🎯 **Implementation Quality (25 pts)**
**Switch to Streamlit tab (http://localhost:8501).**

> "สลับไปตัวจริงเลยครับ · เลือก `case2_illegal_racing` ที่ sidebar · กด Load into form · กด **Run triage**"

**ขณะรอ (~10-15s):**
> "ดูที่ **ล่างสุดของหน้า** — Pipeline execution trace · 7 stages ไฟติดทีละขั้น realtime
>  Step 5 Claude Sonnet pulse ค้างนานสุด · เห็นชัดว่าเป็น ~95% ของ latency"

**หลัง result ขึ้น · ดูที่ pills บน slide:**
> "ตรงกับ slide pop-up ครับ · **Not covered · Rejection review · High confidence**
>  Cite `[1.1, 2.2, 3.1, 4.1]` · ครบทั้ง 4 clause ที่ตรงกับที่ AI อ้างใน reasoning
>  เปิด **Audit record** expander ให้ดู JSON — session_id, model version, clause scores, latency, guard triggers ครบ"

**One sentence:** "ทุก decision ตรวจย้อนได้ · nothing hidden"

---

## Slide 9 — Evaluation · 7:25 – 8:25

**Rubric:** 🎯 **Evaluation & Testing (15 pts)**
**Visual:** 3 big-stats ซ้าย + full metrics table ขวา + red card ล่าง (miss)

> "**5 PDF cases · ไม่ cherry-pick · 3 ชั้น metric:**
>  1. Deterministic match (coverage, routing enums)
>  2. Set-based P/R/F1 (missing docs, risk flags)
>  3. **LLM-as-Judge** · Opus 4.7 · 5-dim rubric (Factuality · Completeness · Clarity · Policy alignment · Appropriate uncertainty)
>
>  ชี้ที่ big-stats ซ้าย:
>  - **100% routing** ⭐
>  - **100% citation** ⭐
>  - **4.00 / 5 judge**
>
>  ชี้ที่ red card ล่าง · **1 miss =** Case 5 flood 45 วันแจ้งช้า — AI มองโลกสวยไป · เลือก 'Possibly covered' แทน 'Cannot determine'
>  **โปร่งใสยอมรับ** · documented ใน `docs/eval_report.md` · candidate fix รออยู่: `days_to_submit > 30 AND no valid reason → Cannot determine`"

**One sentence:** "ไม่หลบ failure · เขียนไว้ชัดใน eval report"

---

## Slide 10 — Risk & Governance · 8:25 – 9:15

**Rubric:** 🎯 **AI Risk, Governance & Production Readiness (15 pts)**
**Visual:** 2-column red (risks) vs green (mitigations) + bottom regulator card

> "ชี้ที่คอลัมน์แดง · **3 ความเสี่ยงหนัก:** AI มั่ว coverage · PII รั่ว · prompt injection
>
>  ชี้ที่คอลัมน์เขียว · **กันทุกข้อแล้ว:**
>  - Forced cite + output guard verify → **100% citation validity measured**
>  - Regex mask ก่อน LLM เห็น + hash customer ใน audit
>  - Injection filter + forced tool-use ล็อก shape
>  - Low confidence → auto Manual review
>  - Append-only audit per session
>
>  ชี้ที่ bottom card · **ตอบ regulator ได้** · audit JSON ครบ cite clauses · model version · latency · guard triggers · 100% citation validity verifiable"

**One phrase:** "Audit-ready · regulator-answerable"

---

## Slide 11 — Roadmap + ปิดสาร · 9:15 – 10:00

**Rubric:** 🎯 **AI Solution Design** (roadmap) + **Communication Quality**
**Visual:** 3 cards grid (Phase 1 blue · Phase 2 teal · Phase 3+ teal) + ปิด quote

> "ชี้ที่ 3 cards ตามลำดับ:
>
>  - **Phase 1 · develop (shipped)** = ที่คุณกำลังดูอยู่ · text triage · RAG · guardrails · 5 cases · UI
>  - **Phase 2 · extensions** = branch แยก · voice (Whisper + TTS) · SupervisorAgent · bilingual TH/EN · 14 cases
>  - **Phase 3+ · roadmap** = Twilio telephony · vision model · fraud model · A/B test manual baseline
>
>  ชี้ที่ปิด quote:
>  **'AI ตัวนี้ทำให้พนักงานประเมินเคสได้เร็ว · สม่ำเสมอ · ตรวจย้อนได้ — ตรงกับ PDF scope ครบทุกข้อ · ไม่แตะ out-of-scope'**
>
>  ขอบคุณครับ · มีคำถามไหมครับ"

**Mic-drop line:** "ตรง scope · มีตัวเลข · มี audit · พร้อม production"

---

# Q&A Playbook (เตรียมคำตอบไว้)

| คำถาม | คำตอบสั้น (≤ 20 วิ) |
|---|---|
| ทำไมไม่ใช้ GPT-4o / Gemini? | Sonnet 4.6 เด่น tool-use adherence + reasoning · cost reasonable · architecture decoupled เปลี่ยนได้ด้วย env var |
| AI มั่วแล้วใครรับผิด? | 1) ทุก coverage ต้อง cite 2) output guard post-check 3) **คนตัดสิน** 4) audit JSON ครบ 5) 100% citation validity ที่ **ตรวจซ้ำได้** |
| 10-15 วิต่อเคสยอมรับได้? | เทียบ manual 10-30 นาที/เคส → **ดีขึ้น ~100 เท่า** · ถ้าต้องเร็วกว่านี้ switch Haiku (trade accuracy) |
| Cost scale? | ~$0.015/triage × volume · ถ้าสูง → Haiku + prompt caching + batch |
| ถ้า Anthropic ล่ม? | SDK interface decoupled · swap OpenAI/Bedrock proxy ได้ |
| Policy เปลี่ยนบ่อยทำยังไง? | Edit `motor_policy.md` → `make ingest` → re-embed → ใช้ได้ทันที · ไม่ต้อง retrain |
| ทำไม 5 cases พอ? | PDF ขอ 3+ (strong = 5) · 5 cases × 5-dim judge = 25 data points · เพิ่มได้ง่าย |
| Voice ไม่มีเหรอ? | `extensions` branch มี POC — STT + TTS + Call UX + Supervisor · **ตั้งใจแยกเพื่อ scope strict** PDF |
| ภาษาไทยรองรับไหม? | develop = EN only (ตาม PDF) · `extensions` = bilingual TH/EN + multilingual embeddings |
| จะ scale เป็น production ยังไง? | `docs/limitations.md §5` list ไว้ 5 ข้อ: Langfuse tracing · NeMo Guardrails · officer workflow · prompt caching · model governance |
| Case 5 ทำไมพลาด? | Prompt rule บอก "late submission may be considered through manual review" → AI มองว่ายังสรุปไม่ได้ · candidate fix = add `days_to_submit > 30 AND no valid reason → Cannot determine` rule |
| Fine-tune Sonnet ไหม? | ไม่ใน prototype · prompt engineering + RAG + guardrails พอ · fine-tune คือ Phase 3+ หลังมี data real |
| ตัวเลข P1-P4 projection มายังไง? | Industry benchmark (McKinsey/Deloitte insurance AI reports) · P5+P6 measured today บน 5 cases · ตัวอื่น validate ใน Phase 2 A/B test |
| ทำไม 11 slides ไม่ใช่ 10? | Rework แล้วแยก Risk กับ Roadmap เป็น 2 slides เพื่อให้แต่ละ section ไม่ cramped · 10 นาทีเท่าเดิม · title ใช้แค่ 15s |

---

# 🔥 Tips ตอนพูดจริง

1. **อย่าอ่าน slide** — พูดด้วย voice ของตัวเอง · slide เป็น prop
2. **ชี้ที่หน้าจอ** — "ชี้ที่ big-stat ซ้าย" / "ชี้ที่ card แดง" · reviewer ตามง่ายขึ้น
3. **พูดตัวเลขเสมอ** — "100%", "80%", "5/5", "~10s", "4.00/5" ติดตัว · reviewer จำได้
4. **เรื่อง 'Out of scope'** — พูดเชิงรุก ไม่ใช่แก้ตัว: "เรา strict กับ PDF scope · ไม่แตะ customer communication · ไม่คำนวณเงิน · เพราะมันเป็น decision boundary ที่ควรให้คน"
5. **เรื่อง Case 5 miss** — **ยอมรับก่อน reviewer ถาม** · "เป็น weak spot ที่ documented · candidate fix รออยู่" → แปลง weakness เป็น rigor
6. **ปิดเสียง notification** iMessage/Slack ขณะ demo
7. **เผื่อ demo ล่ม** → เตรียม screenshot `docs/eval_report.md` ไว้สำรอง
8. **เวลาเหลือ → ไม่ต้องยืด** → "ขอบคุณครับ · มีคำถามไหมครับ"
9. **Pipeline trace** = **wow factor** ของ demo · อย่าลืมเลื่อนลงให้ reviewer เห็น 7 stages pulse

---

# Rubric score mapping — ตรวจก่อนขึ้นเวที

ทุก category ตีลงใน slide หนึ่งขั้นต่ำ:

| Rubric | Points | Primary slide | Secondary |
|---|---|---|---|
| Business Understanding | 15 | **2** (pain) · **3** (metric) | 4 |
| AI Solution Design | 25 | **5** (architecture) · **6** (model) | 7 · 11 |
| Implementation Quality | 25 | **8** (live demo + trace) | 5 · 7 |
| Evaluation & Testing | 15 | **9** (eval + miss) | — |
| AI Risk & Governance | 15 | **10** (risk + regulator) | 7 |
| Communication Quality | 5 | ตลอด (tone, pace, structure) | 1 · 11 |

**Total: 100 pts** · ถ้าเวลาน้อย **ห้ามตัด slide 8 (demo) และ 9 (eval)** เป็นอันขาด — เป็น rubric item ที่หนักที่สุด (25 + 15 = 40 คะแนน)

---

# 🧪 Dry-run checklist (ซ้อม 1-2 รอบด้วย timer)

- [ ] จับเวลาทั้ง deck · ควรจบใน **9:30 ± 15 sec** (เหลือเวลา Q&A warm-up)
- [ ] Slide 8 (demo) — Streamlit คลิกได้ไม่ติด · pipeline trace โชว์ pulse ครบ
- [ ] Slide 9 (eval) — เปิด `docs/eval_report.md` แยก tab · ชี้ตัวเลขได้
- [ ] Slide 10 — pronounce "regulator" ชัด · ไม่ติดตรงนี้
- [ ] ปิดเสียง notification · ลด brightness ถ้า demo
- [ ] เตรียม water bottle · ไม่ต้องกลัวดื่ม 1 ครั้งระหว่าง slide 5 → 6

ขอให้พูดได้ชื่น 🎤
