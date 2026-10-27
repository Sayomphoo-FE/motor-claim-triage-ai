# Day 3 PM — Voice (STT + TTS) & Thai Language Support

> Extends the base MVP with multilingual RAG and a voice I/O prototype.
> This is additive — all existing EN flows keep working.

**Branch:** `develop`
**Timebox:** ~5 hours
**Last updated:** 2026-10-27

---

## Locked decisions

| Topic | Choice | Why |
|---|---|---|
| Thai language strategy | **Multilingual RAG** (swap embedding to `intfloat/multilingual-e5-large`, 1024-dim) | Thai customer queries embed in the same space as the EN policy — demonstrated bilingual capability without translating the policy source of truth |
| STT engine | **Local `faster-whisper` with `large-v3-turbo`** | Free, offline-capable, ~4× faster than vanilla large-v3, Thai WER ~8-12%, ~1.5 GB first-run download |
| TTS engine | **Edge-TTS** (Microsoft Neural voices via Edge's internal API) | Free, high-quality Thai Neural (`th-TH-PremwadeeNeural`, `th-TH-NiwatNeural`), no API key required |
| Slides | **Deferred** — do voice+Thai first, slides tonight | Voice+Thai is the differentiating wow factor; slides are safer and can be built from the final working artefact |

---

## Phase A — Thai language foundation (~2 h)

**Goal:** `make demo CASE=case6_th_สายเกียร์ขาด` returns a valid Thai-worded recommendation that still cites `[Clause X.Y]` IDs.

- [ ] Update default `EMBEDDING_MODEL` in `app/rag/ingest.py` and `.env.example` → `intfloat/multilingual-e5-large`
- [ ] Update `.env` locally (one line) → re-ingest
- [ ] Update `app/prompts/claim_triage.md` — add a bilingual rule:
  - Detect customer language in `claim_description`
  - If Thai → `claim_summary` and `reasoning` in Thai; keep `[Clause X.Y]` IDs in English (they're policy identifiers)
  - If English → everything in English (unchanged)
- [ ] Add `data/test_cases/case6_th_gear_cable.json` — "สายเกียร์ขาด" story from design doc §1.1
- [ ] Add `data/test_cases/case7_th_skirt_crack.json` — "สเกิตบิ่น" story
- [ ] Extend `data/eval/ground_truth.json` with case 6 and 7
- [ ] Extend `scripts/evaluate.py` CASE_FILES list
- [ ] **Milestone:** `make demo CASE=case6_th_gear_cable` returns coverage/routing + Thai reasoning with EN clause citations
- [ ] (Optional) `make eval` — verify EN cases don't regress; accept 1-2 extra API calls

**Risk:** multilingual-e5-large is ~2 GB → first `make ingest` after swap will be slow. Keep the English `bge-small-en-v1.5` configurable as a fallback via `EMBEDDING_MODEL` env.

---

## Phase B — Voice I/O prototype (~2.5 h)

**Goal:** `make ui` → user records voice → transcribed to Thai text → fed to agent → triage output read back in Thai.

### B1. STT utility — `app/voice/stt.py`

- [ ] Add `faster-whisper` to pyproject deps
- [ ] `class WhisperSTT` that lazily loads `large-v3-turbo` on CPU (int8 quantization)
- [ ] `transcribe(audio_bytes_or_path, language="th") -> TranscriptionResult(text, detected_language, duration_s)`
- [ ] CLI `scripts/transcribe.py` for standalone testing

### B2. TTS utility — `app/voice/tts.py`

- [ ] Add `edge-tts` to pyproject deps
- [ ] `synthesize(text, lang) -> bytes` picks voice by lang:
  - `th` → `th-TH-PremwadeeNeural`
  - `en` → `en-US-AriaNeural`
- [ ] Return MP3 bytes (edge-tts default) for direct Streamlit `st.audio()` playback
- [ ] CLI `scripts/speak.py` for standalone testing

### B3. Streamlit integration — `app/ui/main.py`

- [ ] Add a second **Voice tab** (keep existing form tab)
- [ ] `st.audio_input("🎙 Record claim description")` → raw audio bytes
- [ ] On submit: show spinner → STT → fill a minimal ClaimInput (claim_id auto-generated, dates = today, customer = anonymous) → run agent → display result → autoplay TTS of `claim_summary`
- [ ] "Download audio" button for the TTS output

### B4. End-to-end verification

- [ ] Record one Thai utterance ("ขับรถชนกำแพงเพราะเล่นเเข่งผิดกฎหมาย") → confirm `Not covered` / `Rejection review` with cite 2.2
- [ ] Record one English utterance → confirm EN path still works

**Risks:**
- First-run model download blocks UI → add a `scripts/warm_models.py` to pre-download Whisper + e5-large
- `edge-tts` uses Microsoft's internal endpoint → may be flaky on corporate networks; document gTTS as fallback in `docs/limitations.md`
- `faster-whisper` depends on ctranslate2 which may need brew-installed libomp on macOS

---

## Phase C — Docs + commit (~30 min)

- [ ] Update `README.md` — add Prereqs row for `ffmpeg` (brew install ffmpeg) + Voice section with the new UI tab
- [ ] Update `docs/limitations.md` — call out: Edge-TTS stability, Whisper first-run download, multilingual model size, Thai STT WER caveats
- [ ] Update `docs/prompts.md` — document the bilingual rule added to `claim_triage.md`
- [ ] Update `docs/implementation_plan.md` — mark Day 3 PM done, link to this doc
- [ ] 3 commits:
  1. `feat(rag): multilingual embeddings + Thai test cases`
  2. `feat(voice): STT + TTS utilities (faster-whisper + edge-tts)`
  3. `feat(ui): voice tab for end-to-end Thai voice triage`

---

## Dependency additions

```toml
# pyproject.toml
"faster-whisper>=1.0.0",
"edge-tts>=6.1.0",
```

System-level: `ffmpeg` (for audio decoding in faster-whisper).

---

## What this unlocks for the pitch

| Rubric category | Points | What voice+Thai adds |
|---|---|---|
| Business Understanding | 15 | The Thai stories from the design doc §1.1 (สายเกียร์ขาด, สเกิตบิ่น) now have *runnable* evidence |
| AI Solution Design | 25 | Multilingual RAG is the "data not in English" bullet point in rubric 5.3 "Standard" items |
| Implementation Quality | 25 | Working voice loop — the single most memorable demo moment |
| Communication Quality | 5 | Reviewer can literally hear the system — stronger than any slide |

Twilio remains deferred to Phase 2 in the solution doc — the voice tab is the local-first demonstration that shows the pipeline works end-to-end without the regulatory complexity.
