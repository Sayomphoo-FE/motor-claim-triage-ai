# Call Agent Playbook

> Operational rulebook for the AI assistant that runs the "📞 Call
> ABC Insurance" tab. This document is read by both humans (reviewers
> and anyone picking up the project) and the agent itself — the
> `<playbook>` block in `app/prompts/conversation.md` is sourced from
> §3 "Speaking rules" below.
>
> Version: 1.0 · Last updated: 2026-10-28

---

## 0. Multi-agent architecture

The Call tab is driven by a thin **SupervisorAgent** that owns the
conversation state and routes each turn to a specialist:

```
                     ┌────────────────────────┐
    UI (Call tab) ───▶ SupervisorAgent        │
                     │  • owns state           │
                     │  • logs every decision │
                     │  • routes per turn      │
                     └──┬────────────────────┬┘
                        │                    │
                        ▼                    ▼
                  ┌─────────────┐    ┌──────────────┐
                  │ IntakeSpec. │    │ TriageSpec.  │
                  │ (Conv.Agent)│    │ (TriageAgent)│
                  │ ask / collect│    │ policy + RAG │
                  │ one field at │    │ + guardrails │
                  │ a time       │    │ + audit JSON │
                  └─────────────┘    └──────────────┘
```

Why go through the Supervisor at all?

- The UI talks to **one** agent object regardless of which specialist
  is actually handling the turn. Adding `InquirySpecialist`,
  `SalesSpecialist`, `FraudEscalation`, or `MultiBrandRouter` later
  (per solution-design §5.1) is a single method change on the
  Supervisor and does not touch the UI.
- Every routing decision is appended to `state.supervisor_log`,
  which is rendered in the UI as a "🧭 Supervisor log" expander and
  stored alongside the audit JSON. Reviewers can replay *who did what
  at which turn*.
- The pre-intake decision point is a natural seam for future intent
  classification (claim vs inquiry vs sales).

The classes live in:
- `app/agents/supervisor.py` — `SupervisorAgent`
- `app/agents/conversation.py` — intake specialist (`ConversationAgent`)
- `app/agents/triage.py` — triage specialist (`TriageAgent`)

## 1. Who the agent is

- **Persona:** AI claim intake assistant for ABC Insurance.
- **Role:** Collects the information a human claim officer will need
  to triage a motor-insurance claim, then hands the case over.
- **Not allowed to:** approve, reject, or quote a payout; make a
  coverage call; invent facts the customer did not say; keep the
  caller on the line after triage runs.
- **Models backing it:**
  - Claude Sonnet 4.6 for dialogue turns and triage reasoning.
  - faster-whisper `large-v3-turbo` for speech-to-text.
  - Edge-TTS `th-TH-PremwadeeNeural` / `en-US-AriaNeural` at
    rate `-20%` for speech synthesis.

## 2. Required information checklist

The agent must gather these fields before it may hand the call to
the triage subsystem. See `REQUIRED_FIELDS` in
`app/agents/conversation.py` for the canonical list.

| Field | Required? | How the agent asks |
|---|---|---|
| Vehicle make / model / year | **Required** | "ยี่ห้อและรุ่นรถของท่านคืออะไรคะ" / "What's the make and model of your vehicle?" |
| Incident date | **Required** | "เหตุการณ์เกิดขึ้นเมื่อไหร่คะ" / "When did this happen?" |
| Claim description | **Required** | Usually captured in the first customer turn as a free-form story. |
| Documents submitted | Preferred | "ท่านได้ส่งเอกสารอะไรไปแล้วบ้างคะ" / "What documents have you already submitted?" |
| Claim history (12-24 months) | Preferred | "ในรอบ 12-24 เดือนที่ผ่านมา ท่านเคยเคลมบ้างไหมคะ" / "Any prior claims in the past 12-24 months?" |

"Preferred" fields may be filled with `"(unknown)"` if the customer
declines or does not know; the agent must not loop asking indefinitely.

## 3. Speaking rules

These rules govern every spoken turn the AI produces.

1. **Introduce once.** The scripted greeting ends the introduction
   phase. Never re-introduce the AI or ABC Insurance in later turns.
2. **One question at a time.** Each follow-up asks for exactly one
   missing field, phrased as a natural single sentence.
3. **Priority order when multiple fields are missing:**
   `claim_description` → `vehicle` → `incident_date` →
   `documents_submitted` → `customer_claim_history`.
4. **Mirror the caller's chosen language.** `message_to_customer`
   is always in the `conversation_language` the caller picked; it
   does **not** switch mid-call even if the caller code-switches.
5. **Polite register.** Thai turns end with `ค่ะ` / `นะคะ`; English
   turns use natural polite phrasing.
6. **No decisions.** The agent never says "you're covered",
   "we'll pay out", or "you've been rejected". The policy-grounded
   triage subsystem produces the recommendation; the human officer
   makes the call.
7. **No fabrication.** If the customer did not state X, X stays
   empty in `collected_info` and the agent asks for it.
8. **Hand-over line is scripted-feel.** When moving to triage, the
   agent must say a short handover sentence (one line, polite),
   e.g.
   - TH: "ขอบคุณค่ะ ดิฉันจะส่งต่อข้อมูลให้เจ้าหน้าที่ประเมินให้สักครู่นะคะ"
   - EN: "Thank you — I'll pass your case to a claim officer for review now."

## 4. End-to-end flow

```
┌───────────────────────────────────────────────────────────┐
│ Phase 0 — Idle                                            │
│   UI shows a single "📞 Call ABC Insurance" button.       │
│   No state yet.                                           │
└──────────────┬────────────────────────────────────────────┘
               │ user clicks the button
               ▼
┌───────────────────────────────────────────────────────────┐
│ Phase 1 — Scripted greeting                               │
│   Agent queues THREE assistant turns, in order:           │
│     (a) Thai greeting                                     │
│     (b) Bridge line (TH): "ขอเรียนภาษาอังกฤษต่อนะคะ"      │
│     (c) English greeting                                  │
│   Each turn plays its own TTS clip (TH voice for a-b,     │
│   EN voice for c), slowed to -20% with sentence pauses.   │
└──────────────┬────────────────────────────────────────────┘
               │ TTS clips finish playing
               ▼
┌───────────────────────────────────────────────────────────┐
│ Phase 2 — Language choice (required gate)                 │
│   UI shows two large buttons:                             │
│     🇹🇭  ภาษาไทย      🇬🇧  English                        │
│   Mic input is HIDDEN until the caller picks one.         │
│   state.language stays None until a button is pressed.    │
└──────────────┬────────────────────────────────────────────┘
               │ caller picks TH or EN
               ▼
┌───────────────────────────────────────────────────────────┐
│ Phase 3 — Information gathering loop                      │
│   Repeat until all required fields are filled:            │
│     1. Caller presses mic, speaks, presses stop, sends.   │
│     2. STT transcribes (language hint = state.language).  │
│     3. Loader bubble "⋯ ดิฉันกำลังคิดสักครู่นะคะ" shown.   │
│     4. LLM (Claude Sonnet 4.6) returns ONE of:            │
│          action="ask":  one follow-up question            │
│          action="triage": handover line                   │
│     5. New AI bubble appears, TTS auto-plays once.        │
└──────────────┬────────────────────────────────────────────┘
               │ action="triage" produced
               ▼
┌───────────────────────────────────────────────────────────┐
│ Phase 4 — Triage                                          │
│   TriageAgent.run(ClaimInput) is invoked with the         │
│   collected fields. All existing guardrails and the       │
│   audit log run exactly as in the Form tab.               │
└──────────────┬────────────────────────────────────────────┘
               │ TriageResult produced
               ▼
┌───────────────────────────────────────────────────────────┐
│ Phase 5 — Officer handoff view                            │
│   Chat remains visible above the fold.                    │
│   Below it: structured triage card (coverage, routing,    │
│   missing info, risk flags, cited clauses, audit JSON).   │
│   Button: "☎️  End call and start a new one" resets state.│
└───────────────────────────────────────────────────────────┘
```

## 5. Fallbacks

| Situation | Response |
|---|---|
| STT returns empty text | UI shows "No speech detected — please try again." No new turn is appended. |
| TTS fails for a message | The chat bubble still renders; a caption notes the TTS error. Call continues. |
| LLM returns malformed tool call | The forced `respond` tool schema prevents this at the API layer; if it ever happens the handler catches, flips `processing` back to False, surfaces an error, and keeps the chat intact. |
| Caller gets stuck on a required field after 2 attempts | **Future enhancement:** auto-escalate to Manual review with "customer could not provide X" noted. Not implemented in v1.0. |
| Caller asks the AI for a coverage opinion | AI must politely decline and refer them to the human officer (rule §3.6). |
| Caller switches language mid-call | AI keeps responding in the originally-chosen `state.language`. Switching is a Phase-2+ feature. |

## 6. Why not continuous "always-on" mic?

Reviewers often ask whether the mic can stay open so the caller
speaks whenever they like and the AI replies in real time, like a
real call. The honest answer is **no, not with the current stack**:

- `st.audio_input` is batch (returns a complete blob on stop), not
  streaming.
- `faster-whisper` decodes a full audio file; it is not a streaming
  recogniser.
- Edge-TTS plays the generated MP3 to completion; there is no
  "barge-in" primitive to let the caller interrupt.
- Each turn therefore costs about 5-15 seconds end-to-end (Whisper
  decode + Claude response + Edge-TTS synthesis), which is too slow
  to feel like a conversation.

To get a true always-on bidirectional call, replace the three
pieces above with streaming equivalents:

| Component | Current (batch) | Streaming replacement |
|---|---|---|
| Audio capture | `st.audio_input` | WebRTC into a FastAPI backend |
| STT | `faster-whisper large-v3-turbo` | OpenAI Realtime API, Deepgram, or `faster-whisper` with its streaming interface + VAD |
| LLM | Claude Sonnet 4.6 (single response) | Server-sent streaming of partial tokens |
| TTS | Edge-TTS synth-then-play | Streaming TTS (ElevenLabs, OpenAI Realtime, Azure) |
| Interruption | none | VAD-driven barge-in; stop TTS when user speech is detected |

A pragmatic path, in order of effort:

1. **OpenAI Realtime API** — single bidirectional WebSocket, 200ms
   latency, roughly $0.06-0.24 per minute. Lowest-code option.
2. **Pipecat / LiveKit Agents** — open-source orchestration you can
   point at ElevenLabs + Deepgram + Claude; more control, more ops.
3. **Custom WebRTC + VAD + Claude streaming + ElevenLabs** — most
   flexible, 1-2 weeks of development.

All three require moving the UI off Streamlit (which cannot host a
WebRTC audio stream) to a FastAPI backend with a browser frontend.
This is a Phase-2+ architectural change, out of scope for the
3-day prototype. The current press-to-talk flow is the honest
compromise: it demonstrates the pipeline end-to-end in Streamlit
without pretending to be real-time.

## 7. Observability

Every call produces, in addition to the normal triage audit log:

- `state.turns` — full conversation transcript, both roles.
- `state.collected` — final `CollectedInfo` snapshot before triage.
- The downstream `TriageAgent` writes its usual audit JSON into
  `data/audit_logs/sess_*.json` with `claim_id` prefixed `CLM-CALL-`.

A reviewer can therefore reconstruct what the caller said, what the
agent heard, what fields it extracted, and what triage it produced,
without replaying the audio.
