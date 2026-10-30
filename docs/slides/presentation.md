---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    font-family: 'Sarabun', 'Noto Sans Thai', 'Helvetica Neue', sans-serif;
    font-size: 24px;
  }
  h1 { font-size: 44px; }
  h2 { font-size: 34px; color: #0f766e; }
  h3 { font-size: 26px; color: #334155; }
  code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
  table { font-size: 20px; }
  th { background: #f1f5f9; }
  blockquote { border-left: 4px solid #0f766e; padding-left: 1em; color: #475569; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 2em; }
  .accent { color: #0f766e; font-weight: 700; }
  .muted { color: #64748b; }
---

# 🚗 Motor Insurance Claim Triage Assistant

### AI ผู้ช่วยพนักงานประเมินเคสเคลมประกันรถยนต์

<br>

**ผู้พัฒนา:** Sayomphoo
**งาน:** AI Engineer Technical Assignment · 2026-10

<br>

<span class="muted">10 นาที · scope ตรงกับ Assignment PDF — Officer-facing text triage</span>

---

## 1. ปัญหาที่พนักงานรับเคลมเจอทุกวัน

<div class="cols">

**📋 กระบวนการเดิม**

ลูกค้าแจ้งเคลม → พนักงาน:

1. อ่าน claim description
2. **เปิดเล่ม policy** หา clause ที่เกี่ยวข้อง
3. ตรวจเอกสารที่ส่งว่าครบไหม
4. ดูประวัติเคลมของลูกค้า
5. ประเมินว่าจะเข้าทีมไหน
6. สรุปเองใน note ของ CRM

**🔴 ผลที่ตามมา**

- **ใช้เวลา 10-30 นาที/เคส**
- ตีความ policy ไม่เท่ากัน
- จับฉ้อโกง / exclusion ช้า
- เอกสารขาด → ส่งไป-กลับหลายรอบ
- Audit trail ไม่ชัด · ตอบ regulator ยาก

</div>

---

## 2. Pain → Feature → Metric

| Pain | AI ทำยังไง | ตัววัด |
|---|---|---|
| **P1** manual review นาน | AI สรุป + ประเมิน + cite clause อัตโนมัติ | AHT ↓ 30-40% |
| **P2** ประเมินไม่เท่ากัน | prompt + guardrails เดียวกันทุกเคส | consistency ≥ 0.75 |
| **P3** จับฉ้อโกงช้า | AI ตรวจ pattern Clause 4.3 | fraud recall ↑ 15% |
| **P4** เอกสารขาด loop | AI ชี้ missing docs ตั้งแต่ครั้งแรก | incomplete loops ↓ 50% |
| **P5** ไม่มี audit | ทุก decision cite + JSON audit | 100% coverage |
| **P6** เคสง่าย/ยากปน | AI auto-route 4 ทีม | % เคส route ถูกเพิ่ม |

---

## 3. ใครได้ใช้ · User Journey (Officer-facing)

<div class="cols">

**👥 Stakeholders**
- **พนักงานรับเคลม (ผู้ใช้หลัก)** · กรอกข้อมูล + รีวิว recommendation
- **หัวหน้าทีม** · ดู audit log + spot-check
- **Compliance** · ตรวจทุก decision cite clause ไหน
- **ลูกค้า** · ไม่คุยกับ AI โดยตรง — ลูกค้าแจ้งเคลมตามช่องทางเดิม พนักงานป้อนข้อมูล

**🎯 Decision boundary (PDF §4)**
- AI = **ผู้ช่วย ไม่ใช่ผู้ตัดสิน**
- พนักงานตัดสินใจสุดท้ายเสมอ
- Low confidence → **auto Manual review**
- "Not covered" ต้องมี Section-2 clause cited

</div>

<br>

```
[Officer] → [Streamlit form] → [AI triage] → [Officer reviews + decides]
```

---

## 4. สถาปัตยกรรมเบื้องหลัง

```
┌────────────────────────────────────────────────┐
│  Streamlit Form UI  /  CLI  (officer-facing)    │
└──────────────┬─────────────────────────────────┘
               │ ClaimInput (Pydantic)
               ▼
┌────────────────────────────────────────────────┐
│  Guardrail — Input (PII mask + injection flag)  │
└──────────────┬─────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────┐
│  RAG retriever                                  │
│  Qdrant · BGE-small-en · 4 section-sub-queries  │
└──────────────┬─────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────┐
│  Claim Triage Agent · Claude Sonnet 4.6         │
│  forced tool-use = `submit_triage` schema       │
└──────────────┬─────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────┐
│  Guardrail — Output                             │
│  verify cites · "Not covered" needs exclusion   │
└──────────────┬─────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────┐
│  TriageOutput + Audit JSON (per session)        │
└────────────────────────────────────────────────┘
```

**กฎทอง:** ใช้ AI เฉพาะงานที่ตัดสินใจตายตัวไม่ได้ · ส่วนที่กฎชัด (เช่น ตรวจ cite) = ใช้กฎ

---

## 5. Model + Technique — เลือกใช้แต่ละตัวเพราะอะไร

| งาน | เลือก | ทำไม |
|---|---|---|
| สมอง AI (reasoning) | **Claude Sonnet 4.6** | เก่ง reasoning + tool-use adherence สูง + ภาษาไทยดี |
| กรรมการประเมิน | **Claude Opus 4.7** | คนละ model family ลด self-grading bias |
| Embeddings | `bge-small-en-v1.5` 384d | ขนาดเล็ก (33 MB) · เพียงพอสำหรับ 13 clauses |
| Vector store | **Qdrant** | metadata filter per-section · docker-friendly |
| Structured output | tool-use + Pydantic | shape guarantee · enum validation ชัวร์ |
| Audit observability | JSON append-only per session | ไม่พึ่ง SaaS · ตรวจย้อนตรง |

<br>

**ไม่ใช้ LLM กับทุกอย่าง** — Guardrail output verify cite = `set membership check` ด้วย rule-based ประหยัดและไม่มั่ว

---

## 6. RAG + Guardrails Detail

<div class="cols">

**📚 RAG (grounding)**

1. Policy ตัดเป็น **clause-level chunks** (ตาม `### Clause X.Y`)
2. เก็บ metadata: `section_num`, `clause_id`
3. **4 sub-queries ต่อ claim** — section-filtered
4. top-k=5 ต่อ query → dedupe + merge
5. Prompt ใส่ chunks ทั้งหมด → "single source of truth"

**🛡 Guardrails (3 ชั้น)**

1. **Input:** mask PII (phone/ID/plate/email) + flag prompt injection
2. **Mid:** Pydantic schema + Anthropic tool_choice ลงเล็ม
3. **Output:**
   - ลบ clause ที่ cite แต่ไม่ได้ retrieve
   - "Not covered" ไม่มี Section-2 → downgrade `Cannot determine`
   - Low confidence → ห้าม Standard processing

</div>

---

## 7. Live Demo — Case 2: Illegal Street Racing

**Input:**
> The customer crashed into a concrete barrier while participating in an illegal street race on Rama 9 road around 02:00 AM. Police attended the scene. The customer's statement confirmed they were racing. Front of the car severely damaged.

<br>

**AI Output (forced tool-use):**

| Field | Value |
|---|---|
| Coverage | 🔴 **Not covered** |
| Routing | 🟣 **Rejection review** |
| Confidence | **High** |
| Cited clauses | `[1.1, 2.2, 3.1, 4.1]` ← ✅ all in retrieved context |
| Reasoning | "...damage from illegal racing is excluded [Clause 2.2]..." |

<br>

**Audit log:** `data/audit_logs/sess_abc.json` — model version · clauses · latency · guard triggers

---

## 8. Evaluation — ตัวเลขจริง (5 PDF cases)

| Metric | Value |
|---|---|
| Coverage accuracy | **80%** (4/5) |
| **Routing accuracy** | **100%** (5/5) ⭐ |
| **Citation validity** | **100%** · zero hallucinated clauses ⭐ |
| Confidence accuracy | 80% |
| Missing-info F1 (avg) | 0.87 |
| Risk-flags F1 (avg) | 0.75 |
| Cited-clause coverage | 0.78 |
| **LLM-Judge mean (5-dim rubric)** | **4.00 / 5** |

<br>

**1 miss =** Case 5 late submission 45 วัน — documented weak spot
ควรเพิ่ม deterministic prompt rule: `days_to_submit > 30 AND no valid reason → Cannot determine`

---

## 9. Risk & Governance

<div class="cols">

**🔴 ความเสี่ยงหนัก**

- AI มั่ว coverage ไม่มีจริง
- PII รั่วเข้า log
- Prompt injection

**🟢 วิธีกัน (บน prototype นี้)**

- **Cite ทุกข้อสรุป** + output guardrail ตรวจกลับว่ามีจริง
- Pattern-mask PII ก่อน LLM เห็น + hash customer ใน audit
- Injection filter + forced tool-use ล็อก shape output
- Low confidence → auto Manual review
- Audit log append-only ต่อ session
- Pydantic + enum = ไม่มี free prose ที่คุมไม่ได้

</div>

<br>

**ตอบ regulator ได้:** ทุก decision มี audit JSON · cite clauses · model version · latency · guard triggers · **100% citation validity verifiable**

---

## 10. Roadmap + ปิดสาร

<div class="cols">

**Phase 1 — MVP (ส่งแล้ว · บน `develop`)**
- Text-based triage · RAG · guardrails
- 5 PDF cases · LLM-Judge · audit log
- Streamlit Form UI + CLI
- Solution Design + eval + limitations docs

**Phase 2 — Beyond PDF (บน `extensions`)**
- Multi-agent SupervisorAgent + conversation state
- Voice intake prototype (Whisper + Edge-TTS)
- Bilingual TH/EN · multilingual embeddings
- 14 bilingual test cases · call transcript log

**Phase 3+ — Production roadmap**
- Twilio real telephony
- Vision model (รูปความเสียหาย)
- Fine-tuned fraud model + MCP SharePoint
- A/B test เทียบ manual triage baseline

</div>

<br>

> **AI ตัวนี้ทำให้พนักงานประเมินเคสได้เร็ว · สม่ำเสมอ · ตรวจย้อนได้ — ตรงกับ PDF scope ครบทุกข้อ · ไม่แตะ out-of-scope**
