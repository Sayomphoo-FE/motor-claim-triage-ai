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

### AI ผู้ช่วยรับเรื่องเคลมประกันรถยนต์

<br>

**ผู้พัฒนา:** Sayomphoo
**งาน:** AI Engineer Technical Assignment · 2026-10

<br>

<span class="muted">10 นาที · ภาษาไทย + EN technical terms</span>

---

## 1. เรื่องเล่า — ปัญหาที่พบด้วยตนเอง

<div class="cols">

**🚗 เคสที่ 1 — สายเกียร์ขาด**

ขับถอยออกจากบ้าน เปลี่ยนเกียร์ R → D
**สายเกียร์ขาด** · รถค้าง · เรียกสไลด์

โทร call center → **กด 1-2-3 หลายชั้น**
เสียเวลา 3-5 นาที กว่าจะถึงคน

**🚗 เคสที่ 2 — สเกิตบิ่น**

สเกิตหน้ารถชนหลุม · อยากเคลมเปลี่ยน

โทรไปอีก → **IVR เดิม** · เมนูเยอะ
เสี่ยงกดผิด → ต่อผิดทีม

</div>

<br>

> **เครียดอยู่แล้วตอนเพิ่งเกิดเหตุ ต้องมาจัดการ IVR อีก**

---

## 2. Pain → Feature → ตัววัดผล

| Pain | AI ทำยังไง | ตัววัด |
|---|---|---|
| **P1** เมนู IVR หลายชั้น | พูดได้เลย AI เข้าใจ | ลูกค้าถึงคำตอบใน 2 ขั้น (จากเดิม 5) |
| **P2** กดผิด → ต่อผิดทีม | AI ถามชัดก่อน แทนที่จะเดา | mis-routing < 5% |
| **P3** พนักงานถามซ้ำจากศูนย์ | AI รวบรวม + ส่งต่อพร้อมสรุป | AHT ↓ 30-40% |
| **P4** แต่ละคนประเมินไม่เท่ากัน | AI ใช้กฎเดียวกันทุกเคส | triage consistency ≥ 0.75 |
| **P5** จับฉ้อโกงช้า | AI ตรวจสัญญาณต้องสงสัย | fraud detection ↑ 15% |
| **P6** หลายแบรนด์ · สับสน | AI ดูเลขกรมธรรม์ ต่อถูกเสมอ | brand-routing accuracy > 95% |

---

## 3. ใครได้ใช้ · เส้นทางการโทร

<div class="cols">

**👥 Stakeholders**
- **ลูกค้า (คนหลัก)** · โทรเข้าตอนเครียด
- **พนักงานรับเคลม** · รับสายต่อ มีสรุปแล้ว
- **หัวหน้าทีม** · ดูแดชบอร์ด + เคสยาก
- **ฝ่าย Compliance** · ตรวจบันทึก · PDPA

**🎯 Decision boundary**
- AI = **ผู้ช่วย ไม่ใช่ผู้ตัดสิน**
- พนักงานตัดสินใจสุดท้ายเสมอ
- AI แนะนำตัวว่าเป็น AI ตั้งแต่เริ่ม
- Low confidence → auto Manual review

</div>

<br>

```
[ลูกค้า] → [AI greet] → [intake Q&A] → [RAG + triage]
                                              │
                                              ▼
                                   [handoff → พนักงาน]
                                   + สรุปเคสบนจอ
```

---

## 4. สถาปัตยกรรมเบื้องหลัง

```
                    ┌───────────────────┐
    ลูกค้า ────────▶│ Streamlit UI       │
                    │ Form (reviewer)    │
                    └──────┬────────────┘
                           │ ClaimInput (Pydantic)
                           ▼
                    ┌───────────────────┐
                    │ 3-layer guardrails │
                    │ in / mid / out     │
                    └──────┬────────────┘
                           ▼
                    ┌───────────────────┐
                    │ Claim Triage Agent │
                    │ Claude Sonnet 4.6  │
                    │ + forced tool-use  │
                    └──┬────────┬──────┘
                       │        │
            ┌──────────▼┐  ┌───▼──────────┐
            │ Qdrant RAG │  │ Audit log    │
            │ 13 clauses │  │ (JSON/sess)  │
            └───────────┘  └──────────────┘
```

**กฎทอง:** ใช้ AI เฉพาะงานที่ตัดสินใจตายตัวไม่ได้ · ส่วนที่กฎชัด = ใช้กฎ

---

## 5. Model + Technique — เลือกใช้แต่ละตัวเพราะอะไร

| งาน | เลือก | ทำไม |
|---|---|---|
| สมอง AI (reasoning) | **Claude Sonnet 4.6** | เก่ง reasoning + Thai + 100% tool-use adherence |
| กรรมการประเมิน | **Claude Opus 4.7** | คนละ model family ลด self-grading bias |
| Embeddings | `bge-small-en-v1.5` 384d | ขนาดเล็ก (33 MB) เพียงพอสำหรับ 13 clauses |
| Vector store | **Qdrant** | metadata filter per-section · docker-friendly |
| Structured output | tool-use + Pydantic | shape guarantee · enum validation |
| Vector dim swap-path | multilingual-e5-large | Phase 2 Thai: swap env var เดียว |

<br>

**ไม่ใช้ LLM กับทุกอย่าง — ส่วนที่ rules ชัด → rules เร็ว + ประหยัด**

---

## 6. RAG + Guardrails Detail

<div class="cols">

**📚 RAG (grounding)**

1. Policy ตัดเป็น clause-level chunks
2. เก็บ metadata: `section_num`, `clause_id`
3. **4 sub-queries ต่อ claim** — หนึ่งต่อ section
4. top-k=5 ต่อ query → dedupe + rank by score
5. Prompt ใส่ chunk ทั้งหมด → "single source of truth"

**🛡 Guardrails (3 ชั้น)**

1. **Input:** mask PII (phone/ID/plate/email) + flag prompt injection
2. **Mid:** schema validation + enum enforcement
3. **Output:**
   - ลบ clause ที่ cite แต่ไม่ได้ retrieve
   - "Not covered" ที่ไม่ใช้ Section-2 → downgrade เป็น Cannot determine
   - Low confidence → ห้ามไป Standard

</div>

---

## 7. Demo — Case 2: Illegal Street Racing

**Input:**
> ลูกค้าชนแบริเออร์ขณะร่วมแข่งผิดกฎหมายบนถนน Rama 9 ตอนตี 2 ตำรวจมาถึงที่เกิดเหตุ ลูกค้าให้ปากคำว่ากำลังแข่ง

<br>

**AI Output (forced tool-use):**

| Field | Value |
|---|---|
| Coverage | 🔴 **Not covered** |
| Routing | 🟣 **Rejection review** |
| Confidence | **High** |
| Cited clauses | `[1.1, 2.2, 3.1, 4.1]` ← all verified in retrieved context |
| Reasoning | "...damage from illegal racing is excluded [Clause 2.2]..." |

<br>

**Audit log:** `data/audit_logs/sess_abc.json` — model version, clauses, latency, guard triggers

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
Need `days_to_submit > 30` deterministic prompt rule ใน iteration ต่อไป

---

## 9. Risk & Governance

<div class="cols">

**🔴 ความเสี่ยงหนัก**

- AI มั่ว coverage ไม่มีจริง
- PII รั่ว
- Prompt injection

**🟢 วิธีกัน (บน prototype นี้)**

- **Cite ทุกข้อสรุป** + ตรวจกลับว่ามีจริง
- Pattern-mask PII ก่อน LLM เห็น
- Injection filter + "ignore previous" patterns
- Low confidence → auto Manual review
- Audit log append-only ต่อ session
- Pydantic structured output = ไม่มี free prose ที่ควบคุมไม่ได้

</div>

<br>

**ตอบ regulator ได้:** ทุก decision มี audit JSON · cite clauses · model version · latency · guard triggers

---

## 10. Roadmap + ปิดสาร

<div class="cols">

**Phase 1 — MVP (ส่งแล้ว)**
- Text-based triage · RAG · guardrails
- 5 PDF cases · LLM-Judge · audit log
- Streamlit UI + CLI

**Phase 2 — Voice (branch `extensions`)**
- Streamlit mic + Whisper STT
- Edge-TTS neural voices (TH + EN)
- Multi-turn Call UX + Supervisor pattern
- Bilingual RAG + 14 cases

**Phase 3+ — Production (roadmap)**
- Twilio real telephony
- MCP SharePoint (live policy updates)
- Vision model สำหรับรูปความเสียหาย
- Fine-tuned Thai STT + fraud model

</div>

<br>

> **AI ตัวนี้ไม่ใช่แค่ประหยัดเวลา — มันคือการบอกลูกค้าในวันที่เขาเครียดที่สุดว่า "เราพร้อมช่วย" โดยไม่ต้องกด 1-2-3 อีก**
