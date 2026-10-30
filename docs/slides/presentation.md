---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    font-family: 'Sarabun', 'Noto Sans Thai', 'Helvetica Neue', sans-serif;
    font-size: 22px;
    padding: 48px 56px;
    line-height: 1.5;
  }
  h1 { font-size: 40px; margin-bottom: 0.2em; }
  h2 {
    font-size: 30px;
    color: #0f766e;
    margin: 0 0 0.4em 0;
    padding-bottom: 0.3em;
    border-bottom: 3px solid #0f766e;
  }
  h3 { font-size: 22px; color: #334155; margin: 0.6em 0 0.3em 0; }
  h4 { font-size: 20px; color: #0f766e; margin: 0.4em 0 0.2em 0; }
  code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre { font-size: 15px; line-height: 1.3; }
  pre code { background: transparent; padding: 0; }
  table { font-size: 18px; margin: 0.4em 0; }
  th { background: #f1f5f9; }
  td, th { padding: 6px 10px; }
  ul, ol { margin: 0.3em 0; padding-left: 1.3em; }
  li { margin-bottom: 0.15em; }
  blockquote {
    border-left: 4px solid #0f766e;
    padding: 0.4em 0.9em;
    margin: 0.5em 0;
    color: #334155;
    font-size: 20px;
    background: #f8fafc;
  }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 1.8em; }
  .cols-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.2em; }
  .accent { color: #0f766e; font-weight: 700; }
  .muted { color: #64748b; }
  .pill {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 16px; font-weight: 600; margin-right: 6px;
  }
  .pill-red { background: #fee2e2; color: #991b1b; }
  .pill-green { background: #dcfce7; color: #166534; }
  .pill-blue { background: #dbeafe; color: #1e40af; }
  .section-divider {
    height: 2px; background: #e2e8f0; margin: 0.6em 0 0.8em 0;
  }
  .big-stat {
    font-size: 36px; font-weight: 700; color: #0f766e;
    line-height: 1.1; margin: 0.2em 0;
  }
  .card {
    background: #f8fafc; border-left: 4px solid #0f766e;
    padding: 10px 14px; border-radius: 6px; margin: 0.4em 0;
  }
  .card-red { background: #fef2f2; border-left-color: #dc2626; }
  .card-blue { background: #eff6ff; border-left-color: #2563eb; }
---

<!-- _paginate: false -->

# 🚗 Motor Insurance Claim Triage Assistant

### AI ผู้ช่วยพนักงานประเมินเคสเคลมประกันรถยนต์

<br>

**ผู้พัฒนา:** Sayomphoo
**งาน:** AI Engineer Technical Assignment · 2026-10

<br>

<span class="muted">10 นาที · scope ตรงกับ Assignment PDF — Officer-facing text triage</span>

---

## 1. ปัญหาที่พนักงานรับเคลมเจอทุกวัน

#### 📋 กระบวนการเดิม — manual review ทุกเคส

<div class="card">

ลูกค้าแจ้งเคลม → พนักงานต้อง: **อ่าน claim** · **เปิดเล่ม policy** · **ตรวจเอกสาร** · **ดูประวัติเคลม** · **ตัดสินใจ routing** · **สรุปใน CRM**

</div>

<div class="big-stat">⏱ ใช้เวลา 10-30 นาที/เคส</div>

<div class="section-divider"></div>

#### 🔴 ผลที่ตามมา

<div class="cols">

- ตีความ policy ไม่เท่ากัน
- จับฉ้อโกง / exclusion ช้า
- เอกสารขาด → ส่งไป-กลับ loop

<!-- col 2 -->

- Audit trail ไม่ชัด
- ตอบ regulator ยาก
- เคสง่าย/ยากปน · คิวช้า

</div>

---

## 2. Pain → Feature → Metric

| Pain | AI ทำยังไง | ตัววัด |
|---|---|---|
| **P1** manual review นาน | สรุป + ประเมิน + cite clause อัตโนมัติ | AHT ↓ 30-40% |
| **P2** ประเมินไม่เท่ากัน | prompt + guardrails เดียวกันทุกเคส | consistency ≥ 0.75 |
| **P3** จับฉ้อโกงช้า | ตรวจ pattern Clause 4.3 | fraud recall ↑ 15% |
| **P4** เอกสารขาด loop | ชี้ missing docs ตั้งแต่ครั้งแรก | incomplete loops ↓ 50% |
| **P5** ไม่มี audit | ทุก decision cite + JSON audit | **100% coverage ⭐** |
| **P6** route ผิดทีม | AI auto-route 4 ทีม | **routing acc 100% ⭐** |

<span class="muted">⭐ = measured today บน 5 PDF cases · อื่นๆ projected · validate ใน Phase 2</span>

---

## 3. User Journey (Officer-facing)

#### 👥 Stakeholders

<div class="cols">

- **พนักงานรับเคลม (ผู้ใช้หลัก)** · กรอก + รีวิว
- **หัวหน้าทีม** · ดู audit + spot-check

<!-- col 2 -->

- **Compliance** · ตรวจ decision cite clause
- **ลูกค้า** · ไม่คุยกับ AI โดยตรง

</div>

<div class="section-divider"></div>

#### 🎯 Decision boundary (ตาม PDF §4)

<div class="cols">

<div class="card card-red">

**AI ไม่ทำ**
- ตัดสิน approve/reject
- คำนวณเงิน
- สื่อสารลูกค้าตรง

</div>

<div class="card">

**AI ทำ**
- สรุปเคส + cite clause
- Low conf → auto Manual
- "Not covered" ต้องมี Section-2

</div>

</div>

```
[Officer] → [Streamlit form] → [AI triage ~10s] → [Officer decides]
```

---

## 4. สถาปัตยกรรมเบื้องหลัง

```
┌───────────────────────────────────────────────┐
│  Streamlit UI / CLI  — officer-facing          │
└──────────────────┬────────────────────────────┘
                   │ ClaimInput (Pydantic)
                   ▼
┌──────────────────────────┐   ┌───────────────────┐
│ 🧹 Input Guardrail        │   │ 📚 RAG retriever   │
│  PII mask + injection    │─▶│  Qdrant · bge-small│
└──────────────────────────┘   │  4 section queries │
                               └────────┬──────────┘
                                        ▼
                               ┌───────────────────┐
                               │ 🤖 Claude Sonnet 4.6│
                               │  forced tool-use   │
                               └────────┬──────────┘
                                        ▼
                               ┌───────────────────┐
                               │ ✅ Output Guardrail │
                               │  cite + safety     │
                               └────────┬──────────┘
                                        ▼
                               ┌───────────────────┐
                               │ 📝 TriageOutput    │
                               │   + Audit JSON     │
                               └───────────────────┘
```

<div class="card">

**กฎทอง:** ใช้ AI เฉพาะงานตัดสินใจตายตัวไม่ได้ · ส่วนที่กฎชัด (ตรวจ cite) = rule-based

</div>

---

## 5. Model + Technique — เลือกใช้แต่ละตัวเพราะอะไร

| งาน | เลือก | ทำไม |
|---|---|---|
| สมอง AI (reasoning) | **Claude Sonnet 4.6** | เก่ง reasoning + tool-use + ภาษาไทย |
| กรรมการประเมิน | **Claude Opus 4.7** | คนละ family ลด self-grading bias |
| Embeddings | `bge-small-en-v1.5` 384d | 33 MB · พอสำหรับ 13 clauses |
| Vector store | **Qdrant** | metadata filter per-section · docker-friendly |
| Structured output | tool-use + Pydantic | shape + enum validation ชัวร์ |

<div class="card card-blue">

**ไม่ใช้ LLM กับทุกอย่าง** — Guardrail output verify cite = `set membership check` = rule-based · ประหยัดและไม่มั่ว

</div>

---

## 6. RAG + Guardrails Detail

<div class="cols">

<div>

#### 📚 RAG (grounding)

1. Policy ตัดเป็น clause-level chunks
2. Metadata: `section_num`, `clause_id`
3. **4 sub-queries ต่อ claim** — section-filtered
4. top-k=5 ต่อ query → dedupe
5. Chunks ทั้งหมด → "single source of truth"

</div>

<div>

#### 🛡 Guardrails (3 ชั้น)

1. **Input:** mask PII · flag injection
2. **Mid:** Pydantic schema + tool_choice ล็อก
3. **Output:**
   - ลบ clause ที่ไม่ได้ retrieve
   - "Not covered" ต้องมี Section-2
   - Low conf → ห้าม Standard

</div>

</div>

<div class="card">

**ผลลัพธ์:** Citation validity **100%** บน 5 cases · zero hallucinated clauses

</div>

---

## 7. Live Demo — Case 2: Illegal Street Racing

> Customer crashed into a concrete barrier while participating in an illegal street race on Rama 9 road around 02:00 AM. Police attended. Customer confirmed racing.

#### AI Output (forced tool-use)

| Field | Value |
|---|---|
| Coverage | <span class="pill pill-red">🔴 Not covered</span> |
| Routing | <span class="pill" style="background:#e9d5ff;color:#6b21a8">🟣 Rejection review</span> |
| Confidence | <span class="pill pill-blue">High</span> |
| Cited clauses | `[1.1, 2.2, 3.1, 4.1]` ✅ all in retrieved context |
| Reasoning | "...damage from illegal racing is excluded [Clause 2.2]..." |

<span class="muted">📝 Audit log: `data/audit_logs/sess_abc.json` — model · clauses · latency · guard triggers</span>

---

## 8. Evaluation — ตัวเลขจริง (5 PDF cases)

<div class="cols">

<div>

#### 🎯 Headline

<div class="big-stat">100% routing ⭐</div>
<div class="big-stat">100% citation ⭐</div>
<div class="big-stat">4.00 / 5 judge</div>

</div>

<div>

#### 📊 Full metrics

| Metric | Value |
|---|---|
| Coverage acc | 80% (4/5) |
| Routing acc | **100%** (5/5) |
| Confidence acc | 80% |
| Missing-info F1 | 0.87 |
| Risk-flags F1 | 0.75 |
| Citation validity | **1.00** |

</div>

</div>

<div class="card card-red">

**1 miss** = Case 5 late submission 45d · documented · fix candidate: `days_to_submit > 30 → Cannot determine`

</div>

---

## 9. Risk & Governance

<div class="cols">

<div>

#### 🔴 ความเสี่ยงหนัก

- AI มั่ว coverage ไม่มีจริง
- PII รั่วเข้า log
- Prompt injection

</div>

<div>

#### 🟢 วิธีกัน (บน prototype)

- Forced cite + output guard verify
- Regex mask + hash customer ใน audit
- Injection filter + tool_choice lock
- Low conf → auto Manual review
- Append-only audit per session

</div>

</div>

<div class="card">

**ตอบ regulator ได้:** audit JSON · cite clauses · model version · latency · guard triggers · **100% citation validity verifiable**

</div>

---

## 10. Roadmap + ปิดสาร

<div class="cols-3">

<div class="card card-blue">

#### Phase 1 · develop (shipped)

- Text triage · RAG
- 5 PDF cases
- Guardrails + audit
- Streamlit + CLI

</div>

<div class="card">

#### Phase 2 · extensions

- SupervisorAgent + conv
- Voice (Whisper + TTS)
- Bilingual TH/EN
- 14 bilingual cases

</div>

<div class="card">

#### Phase 3+ · roadmap

- Twilio telephony
- Vision รูปความเสียหาย
- Fraud model
- A/B test manual baseline

</div>

</div>

<br>

> **AI ตัวนี้ทำให้พนักงานประเมินเคสได้เร็ว · สม่ำเสมอ · ตรวจย้อนได้ — ตรงกับ PDF scope ครบทุกข้อ · ไม่แตะ out-of-scope**
