# 📋 Future Plan — Merge `develop` → `extensions` + Call-to-Form Handover

> Technical spec for the next iteration on the `extensions` branch.
> **Status:** not implemented · do when ready
> **Branch target:** `extensions`
> **Author drafted:** 2026-10-30

---

## 🎯 Goal

Bring the latest text-triage improvements from `develop` into
`extensions`, then change the Call-tab flow so that **the AI
conversation agent hands off collected info to the Form tab** instead
of auto-triaging. The officer reviews / edits the pre-filled form,
then clicks **Run triage** to run the main (develop-equivalent)
pipeline with the full `pipeline execution trace`.

### Why bother?

| Before (current `extensions`) | After (planned) |
|---|---|
| AI conversation → auto triage inside call | AI conversation → **populate form fields** → officer reviews → officer clicks **Run triage** |
| Officer sees only the triage card inside the call thread | Officer sees the full Form-tab result UI (trace panel, audit JSON, etc.) |
| No chance to edit what the AI extracted | Officer can tweak any field before triage runs |
| Different UIs for Call vs Form flows | Single unified "Run triage" path · less maintenance |

---

## 1. Merge `develop` → `extensions`

### What `develop` has that `extensions` doesn't

Since `extensions` was branched off before the develop scope cleanup,
these are the net-new items from `develop`:

- **`TraceStep` dataclass + `on_step` callback** in `TriageAgent.run`
- **Realtime pipeline trace panel** in the Form-tab UI (7-stage,
  pulse animation, bottom of page, `st.html` renderer)
- **`max_tokens` = 4000** fix on the Sonnet call (prevents Thai
  reasoning from truncating trailing enum fields)
- **Vertical pill badges** fix (`inline-block` + `white-space:nowrap`
  so "Possibly covered" never wraps mid-pill)
- **Updated docs:** `docs/eval_report.md` (5-case fresh run),
  `docs/limitations.md`, `docs/prompts.md`, `docs/call_agent_playbook.md`,
  presenter notes, stack explainer, slides deck + PDF rework
- **README branch guide** section
- **Solution Design** doc + PDF (renamed, no "voice" in filename)

### What `extensions` has that `develop` doesn't

Must be preserved during the merge:

- `app/agents/supervisor.py` (`SupervisorAgent`)
- `app/agents/conversation.py` (`ConversationAgent`, `ConversationState`,
  `SupervisorDecision`, scripted greetings)
- `app/voice/stt.py` + `app/voice/tts.py` (Whisper + Edge-TTS)
- `app/observability/call_log.py` (per-call JSON transcript)
- `app/prompts/conversation.md`
- Call tab block in `app/ui/main.py` (_render_call_tab,
  _render_chat_messages, _render_processing_bubble, _render_call_ended,
  _build_transcript_txt, etc.)
- `response_language` field in `ClaimInput`
- Multilingual embeddings default (`intfloat/multilingual-e5-large`)
  in `app/rag/ingest.py`
- Thai variants of test cases (14 total)
- `faster-whisper`, `edge-tts`, `pydub` deps in pyproject

### Expected conflict files

| File | Reason | Resolution strategy |
|---|---|---|
| `app/ui/main.py` | Both branches diverged heavily | Keep extensions' Call tab block; port develop's pipeline-trace helpers and vertical badges into the Form tab block |
| `app/agents/triage.py` | develop adds `TraceStep` + `on_step`; extensions has older `max_tokens` | Take develop's whole file (newer); extensions didn't modify the triage agent after branching |
| `app/schemas.py` | develop doesn't have `response_language` | Keep extensions' version (has the extra field) |
| `app/rag/ingest.py` | develop has `bge-small-en-v1.5` default; extensions has `multilingual-e5-large` | Keep extensions' version (bilingual needs it) |
| `README.md` | Both heavily changed | Hand-merge: start from develop's branch guide, add extensions-specific sections for voice + Call tab |
| `docs/eval_report.md` | develop has 5-case report (English); extensions had 14-case bilingual | Decide at merge time; probably re-run `make eval` on extensions after merge |
| `docs/implementation_plan.md`, `docs/limitations.md`, `docs/prompts.md` | Minor conflicts | Take develop version + splice in extensions' voice/Thai paragraphs |

### Merge commands (hand-driven, careful)

```bash
# Start from a clean working tree
git checkout extensions
git pull origin extensions
git status                              # must be clean

# Attempt the merge — expect conflicts
git merge develop

# If there are conflicts, resolve per the strategy table above,
# then:
git add -A
git merge --continue                    # or:  git commit

# Smoke-test both tabs end-to-end before pushing (see §4).
# Only push when the Form tab AND the Call tab both run clean.
git push origin extensions
```

---

## 2. Call-to-Form Handover Feature

### Flow (what the officer sees)

```
Call tab (initial)
┌───────────────────────────────┐
│   📞  Call ABC Insurance       │
└───────────────────────────────┘
             │ click
             ▼
┌───────────────────────────────┐
│  🤖 AI greeting (TH + EN mix)  │
│  ──────────────────────────── │
│  🎙 [mic] press to speak       │
└───────────────────────────────┘
             │ several turns of conversation
             ▼
┌───────────────────────────────┐
│  🤖 ขอบคุณค่ะ ส่งต่อข้อมูลให้... │     ← handover line (AI)
└───────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────┐
│  📋 ข้อมูลที่ได้จากลูกค้า                           │
│  Vehicle:            Honda Civic 2022              │
│  Incident date:      2026-10-28                    │
│  Description:        ...                           │
│  Documents:          Claim form, photos            │
│  Claim history:      No prior claims               │
│                                                    │
│  [ 📝  โอนข้อมูลไปแท็บ Form input ]                │
│  [ 📥  Export transcript (.txt) ]                  │
└──────────────────────────────────────────────────┘
             │ click "โอน"
             ▼
       Session_state hydrated with collected fields
             │
             ▼
┌──────────────────────────────────────────────────┐
│  ⬆️  ข้อมูลถูกเติมในแท็บ Form input แล้ว            │  ← banner (st.success)
│      กดแท็บ "📝 Form input" ด้านบน                 │
│      แล้วตรวจ/แก้ไข field ตามต้องการ               │
│      จากนั้นกด Run triage                          │
└──────────────────────────────────────────────────┘

Form tab (after officer clicks the tab)
┌───────────────────────────────┐
│  Form fields all pre-filled    │
│  Officer edits anything that    │
│  needs tweaking                 │
│                                 │
│  [ ▶  Run triage ]              │
└───────────────────────────────┘
             │ click
             ▼
   Normal develop pipeline (7-stage trace, output cards, audit JSON)
```

### State machine for the Call

Add to `ConversationState`:

```python
@dataclass
class ConversationState:
    ...
    handover_pending: bool = False      # AI finished collecting, awaiting transfer
    handover_transferred: bool = False  # officer clicked the transfer button
```

Transition rules:

```
AI collecting      → handover_pending=False, handover_transferred=False
AI finishes info   → handover_pending=True
Officer transfers  → handover_transferred=True
```

### Supervisor change (`app/agents/supervisor.py`)

Current behaviour inside `handle_user_turn`:

```python
if step.action == "triage":
    state.log_decision("triage", "run_triage", ...)
    state.triage = self._run_triage(state, claim_id)
```

**New behaviour:**

```python
if step.action == "triage":
    state.log_decision(
        "intake", "handover_pending",
        "all required fields collected; awaiting officer transfer"
    )
    state.handover_pending = True
    # DO NOT run triage here anymore — the officer will press
    # "Run triage" in the Form tab after reviewing.
```

The handover sentence that Claude generated in `step.message_to_customer`
("ขอบคุณค่ะ ส่งต่อข้อมูลให้เจ้าหน้าที่…") is still appended as the final
assistant turn — that part stays the same.

### UI change — Call-ended view (`app/ui/main.py::_render_call_ended`)

Current layout shows "Call ended" banner + collected info + triage
card + txt download + "Place another call" button.

**New layout** (replace triage card with handover block):

```python
def _render_call_ended(state) -> None:
    if state.handover_transferred:
        # Case B: officer already transferred — show thank-you banner
        st.success(
            "📝  ข้อมูลถูกส่งไปแท็บ **Form input** แล้ว · "
            "กดแท็บด้านบนเพื่อตรวจและกด **Run triage**"
        )
    else:
        # Case A: AI finished, awaiting transfer
        st.success(
            "📞 **Call ended** — the AI has collected the information "
            "needed. Review the summary below, then transfer it to the "
            "Form tab to run triage."
        )

    st.markdown("### 📋 ข้อมูลที่ได้จากลูกค้า")
    _render_collected_summary(state.collected)

    if not state.handover_transferred:
        if st.button(
            "📝  โอนข้อมูลไปแท็บ Form input",
            type="primary",
            use_container_width=True,
            key="handover_transfer_btn",
        ):
            _populate_form_from_call(state)
            state.handover_transferred = True
            st.rerun()

    _render_download_transcript_btn(state)
    st.divider()
    _render_place_another_call_btn()
```

### Form-state population helper

```python
def _populate_form_from_call(state) -> None:
    """Write the collected info into the session_state keys the Form
    tab reads from, so switching tabs shows a pre-filled form."""
    from datetime import datetime
    import uuid

    now = datetime.now()
    collected = state.collected

    # Session state keys match the ones _render_form_tab reads
    st.session_state["claim_id"] = (
        f"CLM-CALL-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
    )
    st.session_state["customer"] = "Voice caller (from Call tab)"
    st.session_state["vehicle"] = collected.vehicle or ""

    incident = _parse_iso_date(collected.incident_date)
    st.session_state["incident_date"] = incident
    st.session_state["claim_submitted_date"] = now.date()

    st.session_state["claim_description"] = collected.claim_description or ""
    st.session_state["documents_submitted"] = "\n".join(
        collected.documents_submitted or []
    )
    st.session_state["customer_claim_history"] = (
        collected.customer_claim_history or ""
    )
    # If response_language is used in the Form tab, carry it over too
    st.session_state["response_language"] = state.language or "auto"
```

### Minor helpers

```python
def _render_collected_summary(collected) -> None:
    """Officer-friendly readout of the collected info."""
    rows = [
        ("🚗 Vehicle",          collected.vehicle),
        ("📅 Incident date",    collected.incident_date),
        ("📝 Description",      collected.claim_description),
        ("📄 Documents",        ", ".join(collected.documents_submitted) or "—"),
        ("📜 Claim history",    collected.customer_claim_history),
    ]
    for label, value in rows:
        st.markdown(f"- **{label}:** {value or '_(not provided)_'}")
```

---

## 3. Test plan

Smoke-test both tabs after the merge + feature changes:

### Form tab (develop parity)

- [ ] `make demo CASE=case2_en_illegal_racing` from CLI returns
      `Not covered` / `Rejection review` · pipeline trace in CLI
- [ ] `make ui` → Form tab loads sample → **Run triage** → vertical
      pill badges + 7-stage realtime trace panel + full output

### Call tab (new handover flow)

- [ ] Click "Call ABC Insurance" → scripted greeting plays
- [ ] Speak once → AI asks follow-up (Thai or English, depending on
      caller's choice if gate still present, else Thai default)
- [ ] Continue until all required fields collected
- [ ] AI says handover line · Call-ended view appears with collected
      summary and **"📝 โอนไปแท็บ Form input"** button
- [ ] Click the button · banner changes to "ข้อมูลถูกส่งแล้ว" ·
      session_state verified in Streamlit's state inspector
- [ ] Switch to Form tab · all fields pre-filled correctly
- [ ] Edit vehicle (e.g. append year) · leave rest · click Run triage
- [ ] Pipeline trace runs · result card + audit JSON expand
- [ ] Transcript txt still downloadable from the Call-ended view

### Regression

- [ ] Place another call · state resets · old handover_transferred=False
- [ ] English flow still works · Thai flow still works
- [ ] `make eval` on `extensions` still produces the 14-case report
      (or 5-case if we accept the English-only fresh run as the eval
      source of truth)

---

## 4. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Merge conflict in `main.py` is huge and error-prone | Resolve in stages: first keep the file compiling; then port pipeline trace helpers one function at a time; smoke-test after each |
| `response_language` field breaks Form tab in Form-first flow | Default to `"auto"` on both Form and Call paths · populate explicitly after Call handover |
| Officer could click Run triage before transferring | Not a problem — Form tab always shows the latest session_state; if the officer manually types values they override the Call-populated ones |
| Officer loses context switching tabs | Banner in both tabs tells them where to go next · session_state persistence means field values survive across tab switches without data loss |
| Qdrant collection may hold old `bge-small-en` vectors on dev machine | After checking out extensions, run `docker compose down -v` to drop volumes, then `make up && make ingest` to rebuild with e5-large |

---

## 5. Rollback

If the merge goes sideways:

```bash
git merge --abort                            # mid-merge safety
# or, if already committed:
git reset --hard origin/extensions           # before pushing
# or, if pushed and we need to revert the merge:
git revert -m 1 <merge-commit-sha>
git push origin extensions
```

Keep the `extensions` branch pointer at its current commit before
starting the merge, as a safety anchor:

```bash
git branch extensions-before-merge extensions
```

---

## 6. Where this leaves the project

After this merge:

- `develop` stays the strict PDF-scope deliverable (unchanged)
- `extensions` becomes a **superset** — same strict triage flow as
  `develop` PLUS a voice intake front-end that funnels into it
- Reviewer story is clean: "Form tab = the assignment deliverable;
  Call tab = Phase 2 preview, same triage engine underneath"

The handover model also makes the Call tab honest about what it is: an
information-gathering UI that eventually calls the same triage pipeline
every other code path uses, not a parallel implementation that could
drift from the main one.
