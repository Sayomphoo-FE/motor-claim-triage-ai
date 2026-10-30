# Implementation Plan — Motor Claim Triage AI (Prototype)

> **Scope:** AI Engineer assignment — Motor Insurance Claim Triage Assistant
> **Duration:** 3 calendar days (~20 ชม. working time)
> **Based on:** [Assignment PDF] + [ai-insurance-claim-triage-assistant.md](./ai-insurance-claim-triage-assistant.md)
> **Branch:** `develop`
> **Last updated:** 2026-10-27

---

## 1. Guiding decisions (ล็อกแล้ว)

| หัวข้อ | ตัดสินใจ | เหตุผล |
|---|---|---|
| Scope ของ voice | **Text-first MVP**; voice-via-Twilio เลื่อนไป Phase 2 | Rubric 100 คะแนนไม่มีเสียง + Twilio Thailand number risk สูง |
| Voice bonus (ถ้ามีเวลา) | Streamlit mic input → Whisper → agent (ไม่ใช่ Twilio) | ได้ภาพ voice end-to-end โดย risk ต่ำ |
| Policy data | Policy rules จาก PDF §5.1 เป๊ะๆ ไม่สร้างเพิ่ม | Reviewer ตรวจง่าย + ไม่ outside scope |
| UI | Streamlit | เร็ว + chat input + mic slot + reviewer รันง่าย |
| Repo name | `motor-claim-triage-ai` (ตามโฟลเดอร์เดิม) | — |
| Package manager | `uv` + export `requirements.txt` ควบ | เร็วตอน dev + compat สำหรับ reviewer |

---

## 2. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Package manager | uv |
| LLM (reasoning) | Claude Sonnet 4.6 (`claude-sonnet-4-6`) |
| LLM (fast tasks) | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) |
| LLM (judge) | Claude Opus 4.7 (`claude-opus-4-7`) |
| Embeddings | BGE-M3 (via FastEmbed) |
| Vector store | Qdrant (docker-compose) |
| UI | Streamlit |
| Data validation | Pydantic v2 |
| Observability | JSON audit log (optional: Langfuse) |
| Container | Docker + docker-compose |

### Trade-offs & rationale
- **ไม่ใช้ LangGraph ใน MVP:** overkill สำหรับ workflow 1-2 ขั้น เขียน FSM เองใน `src/graph/` ง่ายกว่า debug ถ้าเวลาเหลือค่อย refactor
- **ไม่ใช้ reranker ใน MVP:** policy rules สั้น (1 หน้า) top-k=5 ก็พอ ประหยัดเวลา
- **ไม่ใช้ Guardrails framework (NeMo/Llama Guard):** เขียน rule-based เองใน `src/guardrails/` คุมได้แม่น + lightweight

---

## 3. Repository structure

```
motor-claim-triage-ai/
├── README.md                    # วิธี setup/run
├── Dockerfile
├── docker-compose.yml           # Qdrant
├── pyproject.toml               # uv-managed
├── requirements.txt             # exported from uv สำหรับ reviewer
├── Makefile                     # make dev / make eval / make demo
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── cli.py                   # python -m src.cli
│   ├── schemas.py               # Pydantic TriageOutput, ClaimInput
│   ├── agents/
│   │   ├── triage.py            # Claim Triage Agent
│   │   └── supervisor.py        # Intent routing (optional day 2)
│   ├── rag/
│   │   ├── ingest.py            # policy → Qdrant
│   │   └── retriever.py         # top-k search + filter
│   ├── prompts/
│   │   ├── claim_triage.md
│   │   └── supervisor.md
│   ├── guardrails/
│   │   ├── input_filter.py      # PII mask, prompt injection
│   │   ├── mid_filter.py        # tool-call validation
│   │   └── output_filter.py     # clause verification, schema
│   ├── observability/
│   │   └── audit.py             # JSON audit log
│   └── ui/
│       └── app.py               # Streamlit
│
├── data/
│   ├── policies/
│   │   └── motor_policy.md      # From PDF §5.1
│   ├── test_cases/
│   │   ├── case1_parked_car.json
│   │   ├── case2_illegal_racing.json
│   │   ├── case3_theft_no_police.json
│   │   ├── case4_fraud_risk.json
│   │   └── case5_late_submission.json
│   └── eval/
│       └── ground_truth.json
│
├── scripts/
│   ├── ingest_policy.py
│   ├── evaluate.py              # Run all cases + LLM-judge
│   └── demo.py
│
├── tests/
│   └── test_schemas.py
│
└── docs/
    ├── implementation_plan.md   # (ไฟล์นี้)
    ├── eval_report.md           # ผล 5 เคส + LLM-judge
    ├── prompts.md               # Prompt docs + rationale
    ├── limitations.md
    └── slides/                  # Presentation
```

---

## 4. Day-by-day plan

### Day 1 — Foundation + Single case end-to-end

**Goal:** `python -m src.cli --case case1` → ได้ TriageOutput ครบ cite clause

#### AM (3-4 ชม.) — Scaffold
- [ ] `uv init` + `pyproject.toml` (deps: anthropic, qdrant-client, fastembed, pydantic, streamlit, python-dotenv)
- [ ] `.env.example` (ANTHROPIC_API_KEY, QDRANT_URL)
- [ ] `.gitignore` (Python standard + .env + __pycache__)
- [ ] `Dockerfile` + `docker-compose.yml` (Qdrant service)
- [ ] `Makefile` (dev, ingest, eval, demo, test, up, down)
- [ ] Smoke test: `anthropic.Anthropic().messages.create(...)` ping + Qdrant up
- [ ] Commit: `chore: scaffold project structure`

#### PM (3-4 ชม.) — Core triage
- [ ] `data/policies/motor_policy.md` — copy PDF §5.1 แยก sections (Covered Events / Exclusions / Required Documents / Routing Rules)
- [ ] `src/rag/ingest.py`: section-aware chunking + BGE-M3 embedding + Qdrant upsert with metadata `{section, clause_id}`
- [ ] `scripts/ingest_policy.py` → `make ingest`
- [ ] `src/rag/retriever.py`: `search(query, filter=None, top_k=5)`
- [ ] `src/schemas.py`: `TriageOutput`, `ClaimInput` (Pydantic v2 with Literal types)
- [ ] `src/prompts/claim_triage.md` (ตาม §8.2 ของ design doc)
- [ ] `src/agents/triage.py`: build context → call Sonnet 4.6 with structured output
- [ ] `src/cli.py`: argparse — load case JSON → run agent → print output
- [ ] `data/test_cases/case1_parked_car.json`
- [ ] **Milestone:** `make demo CASE=case1` → output valid + cites `[Clause X.Y]`
- [ ] Commit: `feat: policy RAG + triage agent working end-to-end`

### Day 2 — Full prototype + evaluation

**Goal:** `make eval` → รายงาน markdown ครบ 5 เคส + Streamlit UI รัน

#### AM (3-4 ชม.) — Evaluation harness
- [ ] `data/test_cases/case2..case5.json` (ครบ 5 เคสตาม PDF §7)
- [ ] `data/eval/ground_truth.json` (expected coverage, routing, missing docs, risk flags per case)
- [ ] `scripts/evaluate.py`:
  - [ ] Metric: coverage match (exact)
  - [ ] Metric: routing confusion matrix + F1
  - [ ] Metric: missing docs Precision/Recall
  - [ ] Metric: risk flags Precision/Recall
  - [ ] LLM-Judge rubric 5-dim (Opus 4.7): Factuality, Completeness, Clarity, Policy alignment, Appropriate uncertainty
  - [ ] Output `docs/eval_report.md` + `data/eval/results.json`
- [ ] **Milestone:** `make eval` → รายงานครบ 5 เคส
- [ ] Commit: `feat: evaluation harness with LLM-judge`

#### PM (3-4 ชม.) — Guardrails + UI + Audit
- [ ] `src/guardrails/input_filter.py`: PII mask (regex phone/ID/plate), prompt injection patterns
- [ ] `src/guardrails/output_filter.py`: verify cited clauses exist in retrieved context; demote "Not covered" → "Cannot determine" if no exclusion match
- [ ] `src/observability/audit.py`: JSON log per session (§11.4 schema)
- [ ] `src/ui/app.py` Streamlit:
  - [ ] Case form (text fields matching PDF §5.2)
  - [ ] "Run triage" button
  - [ ] Display: structured output cards + citations expandable + confidence badge
  - [ ] Audit log viewer (JSON pretty-print)
  - [ ] Sample case loader (dropdown 5 cases)
- [ ] **Milestone:** `streamlit run src/ui/app.py` → run 5 cases through UI
- [ ] Commit: `feat: guardrails + Streamlit UI + audit log`

### Day 3 — Polish + Deliverables + Voice bonus

**Goal:** repo submission-ready + slides + optional voice demo

#### AM (3-4 ชม.) — Deliverables
- [ ] `README.md`:
  - [ ] Setup (uv install, docker-compose up, make ingest)
  - [ ] Run (make demo, streamlit run)
  - [ ] Assumptions (policy = PDF §5.1 only, no voice, mocked history)
  - [ ] Limitations (list from design doc §9.3)
  - [ ] Model/API used + cost estimate
- [ ] `docs/eval_report.md` polish (narrative + failure analysis for each case)
- [ ] `docs/limitations.md`
- [ ] `docs/prompts.md` (prompts + why they work)
- [ ] Clean run test: `git clone` → setup → `make demo` works on clean env
- [ ] `uv pip freeze > requirements.txt`
- [ ] Commit: `docs: README + eval report + limitations`

#### PM (3-4 ชม.) — Slides + optional voice
- [ ] `docs/slides/` — 10-slide deck ตาม §13.1 of design doc:
  1. ปัญหา (เรื่องเล่าจริง)
  2. Pain → feature mapping
  3. User journey
  4. Architecture overview
  5. Model & technique selection
  6. RAG + Guardrails detail
  7. Demo screenshots
  8. Evaluation results
  9. Risk & governance
  10. Roadmap + close
- [ ] Record demo video (3 case walkthroughs)
- [ ] **If time ≥ 2 ชม.:** Streamlit mic input → Whisper API → agent → display
- [ ] Final: tag release, push `develop`, open PR to `main`
- [ ] Commit: `docs: slides + demo recording`

---

## 5. Rubric mapping (ensure 100% coverage)

| Rubric category | Points | How we score |
|---|---|---|
| Business Understanding | 15 | Slides 1-2 + design doc §1 (real stories, pain table, P1-P6 → feature → metric) |
| AI Solution Design | 25 | Design doc §4-7 + Slides 4-6 (architecture, hybrid approach, data flows) |
| Implementation Quality | 25 | Working Streamlit app + structured prompts + RAG grounding + Pydantic schemas |
| Evaluation & Testing | 15 | `docs/eval_report.md` 5 cases + LLM-judge + failure analysis |
| AI Risk & Governance | 15 | Guardrails 3-layer + audit log + HITL framing + privacy mask |
| Communication Quality | 5 | Design doc clarity + README + slides |

---

## 6. Risk register (prototype-specific)

| Risk | Prob | Impact | Mitigation |
|---|---|---|---|
| Anthropic API rate limit during eval | M | H | Add backoff + batch judge calls |
| Qdrant Docker issues on reviewer machine | L | M | Document fallback: `qdrant-client` with in-memory mode |
| Streamlit port conflict | L | L | Document `--server.port` override |
| BGE-M3 download size (~2GB) | M | L | Pre-cache in Dockerfile layer |
| LLM-judge cost explosion | L | M | Budget cap: 5 cases × 1 judge call = $0.50 max |
| Time overrun on guardrails | M | M | Day 2 PM is flexible — skip Supervisor if needed |

---

## 7. What's explicitly OUT of scope (document in limitations.md)

- Voice ingestion via Twilio (Phase 2)
- Multi-brand router / Supervisor agent (nice-to-have Day 2 PM)
- MCP SharePoint integration (Phase 2)
- Vision / damage photo analysis (Phase 3)
- Multi-agent orchestration beyond Supervisor + Triage
- Real customer DB integration — mocked JSON
- NeMo Guardrails / Llama Guard — rule-based only
- Langfuse — JSON audit log only
- Production authentication / SSO
- Load testing / performance tuning

---

## 8. Pre-flight checklist (ก่อนเริ่ม Day 1)

- [ ] Anthropic API key พร้อม (`console.anthropic.com`)
- [ ] Python 3.11+ installed (`python --version`)
- [ ] Docker Desktop running (`docker ps`)
- [ ] uv installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [ ] Branch `develop` checked out ✅
- [ ] Design doc + assignment PDF reviewed ✅

---

## 9. Submission package (final)

- [ ] GitHub repo link (private invite to reviewer)
- [ ] `README.md` with setup+run instructions
- [ ] `docs/implementation_plan.md` (this file)
- [ ] `docs/eval_report.md`
- [ ] `docs/limitations.md`
- [ ] `docs/slides/` (PDF export)
- [ ] Demo video link (YouTube unlisted or Loom)
- [ ] NO API keys committed
