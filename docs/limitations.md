# Known Limitations & Trade-offs

This document records the deliberate scope exclusions and technical
trade-offs behind the prototype. It is written to make the reviewer's
job easier — nothing here is hidden; everything we chose not to build,
or had to work around, is listed.

---

## 1. Scope exclusions (by design)

| Area | Why it's out of scope | How we'd approach it next |
|---|---|---|
| Voice **via Twilio telephony** | Thailand phone numbers require regulatory approval; costs real money per demo call | Phase 2 per solution-design §12.2: Twilio Media Streams → Whisper streaming → agent → ElevenLabs streaming. Note: the prototype **does** ship an end-to-end browser voice loop (Streamlit mic → faster-whisper → agent → Edge-TTS), so the pipeline is proven; only the telephony edge is deferred |
| Multi-brand router / Supervisor agent | Single-intent prototype; the assignment only requires the triage path | Add a Supervisor LangGraph node once a second specialist (sales / inquiry) exists |
| MCP SharePoint integration for live announcements | No live corpus to point at in a POC | Phase 2 — a local-folder MCP stub is already sketched in the design doc |
| Vision / damage photo analysis | Would require Claude vision pricing budget and sample images beyond PDF scope | Phase 3 — Sonnet 4.6 vision call attached as a tool on the agent |
| Fine-tuned fraud model | Needs real claim history data; forbidden by assignment §10 (no real customer data) | Not before data access is established with the client |
| SSO / RBAC on the UI | Prototype UX only | Reverse-proxy Streamlit behind SSO (e.g. OIDC) |
| Load testing & auto-scaling | Not meaningful for a 5-case eval | Add k6 scripts + autoscaled container platform |

The solution-design document (`ai-insurance-claim-voice-triage-assistant.md`)
treats the Voice/MCP/Multi-agent pieces as roadmap items (§12.2 - §12.4);
this prototype intentionally delivers the §12.1 MVP.

---

## 2. Technical trade-offs forced by the environment

### 2.1 Embedding model

- The solution design proposes `BAAI/bge-m3` (1024-dim, multilingual).
- `fastembed` 0.4.x does not ship `bge-m3`; the prototype uses
  `intfloat/multilingual-e5-large` (1024-dim, ~2.24 GB) instead.
  Verified Thai retrieval quality: "แข่งรถผิดกฎหมาย" → Clause 2.2
  at 0.794; English regression check: "illegal street race" →
  Clause 2.2 at 0.836 (actually stronger than the prior
  `bge-small-en-v1.5` baseline).
- e5 models expect `"query: "` and `"passage: "` prefixes on queries
  and documents respectively; both ingest and retriever apply these
  automatically when the model name contains "e5".
- `EMBEDDING_MODEL` env var still allows swapping in a smaller model
  for low-resource environments.

### 2.2 Anthropic SDK — no `temperature`

The Anthropic Python SDK 2.3 (what we're pinned to) removed
`temperature` from `messages.create()`. This surprised us during
Day 1 — see the Day 1 PM commit.

Our substitute for determinism is **forced tool-use**: the model is
required to call `submit_triage`, whose JSON schema is derived from
Pydantic. This guarantees shape, enum validity, and absence of
free-form prose that could drift on rerun. Observed run-to-run
variance is in the free-text `claim_summary` and `reasoning` fields,
which we accept as inherent model behaviour.

### 2.3 Qdrant client / server version mismatch

The `qdrant-client` 1.20 library emits a warning against the pinned
server (1.12.4). All operations we use (collection create, upsert,
query_points with filter) are supported on both sides, and the
retriever constructs the client with `check_compatibility=False` to
silence the warning. For production, pin both ends to the same minor
version.

### 2.4 PLATE regex false positives

The licence-plate regex `[A-Z]{1,2}[-\s]?\d{1,4}` is intentionally
loose because real Thai plates are often transliterated inconsistently.
It will match tokens like `P4` (parking spot) or `A1` (building code)
when they occur in free-text. The guardrail only masks the text
**going to the LLM**; the audit log stores the trigger, and the
officer-facing UI shows the original claim description, so no
information is lost. Tighten by requiring plate context ("plate",
"ทะเบียน") or a more specific pattern once real data is available.

### 2.5 Voice I/O (STT + TTS) caveats

**STT — `faster-whisper large-v3-turbo`**

- First recording in the UI triggers a ~1.5 GB model download, which
  blocks the Streamlit event loop. Mitigation: pre-warm by running
  `uv run python -m scripts.transcribe <any-wav>` once offline.
- Thai Word Error Rate is ~8-12% on clean studio audio and higher on
  noisy phone-call audio. For production, consider domain adaptation
  (fine-tuning on insurance-vocabulary audio) or Typhoon-ASR for a
  Thai-tuned Whisper variant.
- Numeric license-plate pronunciations (e.g. "ทะเบียน กก1234")
  transcribe inconsistently — downstream, this interacts with the
  PLATE regex false-positive described in §2.4.

**TTS — Edge-TTS**

- Uses Microsoft's internal Edge browser endpoint, not a formal
  public API. Microsoft could change or block it without notice.
  Fallback: swap in `gTTS` (lower quality) or OpenAI TTS (paid).
- Corporate proxies occasionally block the Edge-TTS endpoint —
  `app/voice/tts.py` surfaces the error back to the UI rather than
  crashing the triage result.
- The `th-TH-PremwadeeNeural` voice is Thai-native but reads
  loan-words with a strong Thai accent — unavoidable for Neural TTS.

**Bilingual prompt behaviour**

- The prompt detects Thai characters and switches free-text output
  to Thai, keeping Clause IDs and enum values English. Edge case:
  a mixed Thai/English description may produce code-switched output
  which is still useful but inconsistent for downstream workflows.

### 2.6 Streamlit stateful behaviour

Streamlit reruns on every widget change. We store form state in
`st.session_state` and re-render only when the user clicks
"Run triage". Any accidental double-click will trigger a second
Claude call. Mitigation: use the sidebar sample loader for
reproducible demos, and watch for latency badges in the output area
before clicking again.

---

## 3. Evaluation caveats

- **5 cases is a small sample.** Headline accuracies (80% / 100%) have
  very wide confidence intervals. Real validation requires ≥ 50 cases
  with inter-annotator agreement on ground truth.
- **LLM-Judge is non-deterministic.** Opus 4.7 scores can vary by
  0.1-0.3 run-to-run on the same output. For publishable numbers
  we would average across ≥ 3 judging runs. The committed
  `data/eval/results.json` is a single snapshot.
- **Ground truth is author-written.** We selected accept-any-of lists
  that match the PDF-stated expected directions, but reasonable people
  could argue a different set — especially for Case 5. We mitigated
  this by making ground truth explicit JSON (see
  `data/eval/ground_truth.json`), so reviewers can inspect our
  interpretation.
- **Judge bias.** Although we use a different model family (Opus vs
  Sonnet), both are Anthropic models. For a production evaluation
  we would also benchmark with a GPT or Gemini judge and report
  cross-vendor agreement.

---

## 4. Security & privacy caveats

- **PII masking is pattern-based**, not semantic. It will miss
  names, addresses, or anything that doesn't match the four regexes
  (Thai ID, phone, email, plate). A production system should use a
  named-entity model (e.g., Presidio) with Thai language support.
- **Audit logs are plaintext JSON** on local disk. Production should
  encrypt at rest and use an append-only, time-stamped store (e.g.,
  S3 object-lock or an audit database with WORM semantics).
- **No consent capture.** A real voice product must play a PDPA
  consent prompt and store the acceptance alongside the session.
  Design doc §11.1 covers this.
- **Prompt-injection detection is advisory.** We surface likely
  injection attempts in the audit log but do not block the call —
  false positives hurt real customers. A production control plane
  should rate-limit by customer and route repeated injections to
  a human.

---

## 5. What would change for productionisation

1. **Observability:** send OpenTelemetry traces to Langfuse (planned in
   design doc §5), expose metrics via `/metrics`, hook into on-call
   paging on error-rate or citation-validity drops.
2. **Guardrails:** replace rule-based input filter with NeMo Guardrails
   or Llama Guard for a layered defence (regex catches the easy stuff,
   LLM-based filter catches the subtle stuff).
3. **Human workflow:** the UI should post the recommendation into an
   officer queue with override controls, audit, and reroute buttons,
   not just display the recommendation.
4. **Cost control:** add prompt caching (Anthropic cache_control) on
   the policy context — the entire policy fits in the cache, giving
   roughly 90% input-token discount after first call.
5. **Model governance:** version-tag every prompt, log the exact
   model + prompt-version pair into the audit record, and run a
   shadow comparison when either changes.

---

## 6. Rubric honesty check

| Rubric category | Coverage in this prototype | What's missing |
|---|---|---|
| Business Understanding | Design doc §1-2 (Thai pain-point stories + table) | — |
| AI Solution Design | Design doc §4-7 + implementation plan + README §6 | Supervisor & MCP are documented but not implemented |
| Implementation Quality | Working end-to-end CLI + UI + eval + guardrails + audit | No test suite beyond smoke / eval |
| Evaluation & Testing | 5 cases + LLM-Judge + per-case failure analysis | No unit tests on metrics calculations |
| AI Risk & Governance | 3-layer guardrails, audit log, HITL framing | No formal threat model doc |
| Communication Quality | README + solution design + implementation plan + this file | — |
