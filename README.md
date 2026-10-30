# Motor Insurance Claim Triage Assistant

> AI assistant that performs initial triage on a motor insurance claim and
> hands the claim officer a structured recommendation, with policy
> citations, missing-document checks, and risk flags. The officer
> remains the final decision maker.
>
> This repository is the deliverable for the AI Engineer technical
> assignment — see [`docs/implementation_plan.md`](docs/implementation_plan.md)
> for the 3-day build plan, [`docs/ai-insurance-claim-triage-assistant.md`](docs/ai-insurance-claim-triage-assistant.md)
> for the full solution design.

## 🧭 Branch guide

This project is organised across two branches to keep the assignment
submission tight while preserving the stretch work:

| Branch | Scope | What's in it |
|---|---|---|
| **`develop`** _(this branch)_ | **Strict PDF scope only** | Text-based claim triage, Form-tab Streamlit UI, 5 EN test cases from PDF §7, RAG with `bge-small-en-v1.5`, 3-layer guardrails, audit log, LLM-Judge evaluation. 100% of the assignment deliverables. |
| **`extensions`** | Beyond-PDF stretch work | Everything on `develop` **plus** voice I/O (STT + TTS), multi-turn Call-tab UX, SupervisorAgent routing, bilingual TH/EN with multilingual embeddings, 14 bilingual test cases, call transcript log, `.txt` export. Design-doc §12.2+ Phase-2 preview. |

If you are reviewing the assignment deliverable, read **this branch**.
If you want to see where the design doc's voice / multi-agent /
Thai-support vision was taken as a working prototype, check out
`git checkout extensions`.

---

## 1. What this prototype does

Given a claim case (claim ID, customer, vehicle, dates, free-text
description, documents submitted, claim history), the system:

1. **Masks PII** in the free-text (Thai phone / national ID / plate /
   email) before anything else sees it.
2. **Retrieves the most relevant policy clauses** from Qdrant using
   section-filtered semantic search.
3. **Calls Claude Sonnet 4.6** with a forced `submit_triage` tool
   call so the output is always validated.
4. **Verifies every cited clause** actually exists in the retrieved
   context (hallucination firewall) and enforces safety invariants
   (`Not covered` only when a Section-2 exclusion was retrieved and
   cited; `Low` confidence never routes to `Standard processing`).
5. **Writes an append-only audit log** per session.

Output follows the assignment §6 schema:

```
Claim Summary
Initial Coverage Assessment     — Likely covered / Possibly covered /
                                  Not covered / Cannot determine
Missing Information             — [list]
Risk Flags                      — [list]
Recommended Routing             — Standard processing / Manual review /
                                  Fraud review / Rejection review
Reasoning                       — concise, with [Clause X.Y] citations
Confidence Level                — High / Medium / Low
```

---

## 2. Prerequisites

| Tool | Minimum | Install |
|---|---|---|
| Python | 3.11+ | `brew install python@3.11` |
| Docker Desktop | running | https://docker.com |
| `uv` | 0.13+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Anthropic API key | — | https://console.anthropic.com → API Keys |

Approximate end-to-end cost on the Anthropic API:

| Workload | Cost |
|---|---|
| Dev iteration (Haiku) | ~$0.10 |
| 5-case eval (Sonnet) | ~$0.30 |
| 5-case LLM-Judge (Opus) | ~$1.50 |
| Buffer | ~$2.00 |
| **Total** | **~$3-5** |

The $5 Anthropic trial credit is sufficient to run everything in this
repo from scratch.

---

## 3. Setup

```bash
# 1. Clone and enter the repo
git clone <this-repo-url> motor-claim-triage-ai
cd motor-claim-triage-ai

# 2. Install Python deps into a local venv (via uv)
make install    # == uv sync

# 3. Configure secrets
cp .env.example .env
#  → open .env and paste your ANTHROPIC_API_KEY

# 4. Start Qdrant (vector store) in Docker
make up

# 5. Ingest policy rules into Qdrant
make ingest

# 6. Smoke-test API + Qdrant connectivity
make smoke
```

A successful smoke test prints `ALL CHECKS PASSED` and confirms
Qdrant and Claude are both reachable before you run the pipeline.

---

## 4. Run

### Single case via CLI

```bash
make demo CASE=case1_parked_car     # or case2..case5
```

CASE options: `case1_parked_car`, `case2_illegal_racing`,
`case3_theft_no_police`, `case4_fraud_risk`, `case5_late_submission`.

### Streamlit UI (recommended for review)

```bash
make ui
# → open http://localhost:8501
# → use the sidebar to "Load a sample" → "Load into form"
# → click "Run triage"
```

The UI shows the structured output, retrieved policy clauses,
guardrail triggers, and the full audit JSON for the session.

### Full evaluation

```bash
make eval
# → writes docs/eval_report.md and data/eval/results.json
```

Headline numbers from the committed report:

| Metric | Value |
|---|---|
| Coverage accuracy | 80% (4/5) |
| Routing accuracy | 100% (5/5) |
| Citation validity | 100% |
| LLM-Judge mean | ~4.0 / 5 |

Case 5 (late flood submission) is a documented failure mode discussed
in [`docs/eval_report.md`](docs/eval_report.md) and
[`docs/limitations.md`](docs/limitations.md).

---

## 5. Repository map

| Path | What it is |
|---|---|
| `docs/ai-insurance-claim-triage-assistant.md` | Full solution design (Part 1 deliverable, Thai) |
| `docs/implementation_plan.md` | 3-day build plan + rubric mapping |
| `docs/eval_report.md` | Per-case evaluation + LLM-Judge scores |
| `docs/limitations.md` | Known trade-offs and scope exclusions |
| `docs/prompts.md` | Prompt designs with rationale |
| `app/agents/triage.py` | Triage agent (retrieval + Claude + guardrails) |
| `app/rag/` | Policy ingestion + semantic retriever |
| `app/guardrails/` | Input (PII, injection) + output (citation, safety) |
| `app/observability/audit.py` | JSON audit log writer |
| `app/schemas.py` | Pydantic input/output schemas |
| `app/prompts/claim_triage.md` | Main agent prompt |
| `app/ui/main.py` | Streamlit UI |
| `app/eval/` | Deterministic metrics + LLM-Judge |
| `scripts/` | Ingest / evaluate / smoke-test entry points |
| `data/policies/` | Policy source (markdown, cite-able clauses) |
| `data/test_cases/` | 5 PDF §7 fixtures as JSON |
| `data/eval/` | Ground truth + machine-readable results |
| `tests/` | Pytest unit tests |

---

## 6. Design highlights

### Model and technique selection

| Task | Model / approach | Why |
|---|---|---|
| Triage reasoning | Claude Sonnet 4.6 | Strong structured reasoning + 100% tool-use adherence |
| LLM-as-Judge | Claude Opus 4.7 | Different model family from Sonnet → reduces grader bias |
| Smoke / intent | Claude Haiku 4.5 | Cheap and fast for diagnostics |
| Embeddings | `BAAI/bge-small-en-v1.5` | 384-dim, 33 MB, more than enough for 13 clauses |
| Vector store | Qdrant | Metadata filtering (`section_num`) + Docker-friendly |
| Structured output | Anthropic tool-use + Pydantic | Model cannot return invalid shape |

### Grounding and anti-hallucination

- Policy is split by `### Clause X.Y` headings → each chunk is one
  clause with a built-in `[Clause X.Y]` ID so citations round-trip.
- Four section-filtered sub-queries (one per policy section) are
  issued per claim so Section 2 exclusions and Section 3 required
  documents are always consulted.
- Output guardrail strips any citation that was not actually
  retrieved, and refuses `Not covered` without a cited exclusion.

### Human-in-the-loop

- The AI never approves/rejects or calculates payouts.
- `Low` confidence always routes to `Manual review`.
- The UI shows citations and the audit JSON side-by-side so the
  officer can override any recommendation with full context.

---

## 7. Known trade-offs and limitations

Full detail in [`docs/limitations.md`](docs/limitations.md). The short
list:

- Voice-via-Twilio is **out of scope** for this prototype; the design
  doc covers how it would be added (`§12.2 Phase 2`).
- `BAAI/bge-m3` from the design doc is not shipped by FastEmbed → the
  prototype uses `bge-small-en-v1.5`; swap to
  `intfloat/multilingual-e5-large` for Thai customer input.
- The licence-plate regex can match short IDs like "P4" (parking
  spot). The input guard only masks the text sent to the LLM; the
  audit log keeps the mask trigger so an officer can inspect.
- `temperature` is not a valid parameter on the Anthropic SDK v2.3+;
  tool-use enforcement provides determinism instead.
- Qdrant client (1.20) vs server (1.12) emits a version warning but
  queries work; the client is explicitly started with
  `check_compatibility=False`.

---

## 8. For reviewers

Suggested run order:

```bash
make install && cp .env.example .env   # paste API key
make up && make ingest
make smoke                             # confirms env
make demo CASE=case1_parked_car        # watch one case run
make eval                              # full report in docs/eval_report.md
make ui                                # explore interactively
```

Deliverables that correspond to the rubric categories in the
assignment PDF §9:

| Rubric | Where to look |
|---|---|
| Business Understanding | `docs/ai-insurance-claim-triage-assistant.md` §1-2 |
| AI Solution Design | same doc §3-7 + `docs/implementation_plan.md` §2-5 |
| Implementation Quality | `app/`, `make ui`, `make demo` |
| Evaluation & Testing | `docs/eval_report.md`, `make eval` |
| AI Risk & Governance | `app/guardrails/`, `app/observability/`, `docs/limitations.md` |
| Communication Quality | this README + solution design |

---

## 9. License

See [`LICENSE`](LICENSE).
