"""Streamlit UI — officer-facing claim triage demo.

Layout:
  Sidebar     : sample case loader + model info
  Main left   : claim form (editable) + "Run triage" button
  Main right  : triage output cards, retrieved clauses, guardrails,
                audit JSON.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Streamlit launches this file as a script, which puts app/ui on sys.path
# instead of the project root. Add the project root so `import app.*` works.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import json  # noqa: E402
import uuid  # noqa: E402
from datetime import date, datetime  # noqa: E402

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app.agents.triage import TRIAGE_MODEL, TriageAgent, TriageResult
from app.schemas import ClaimInput

load_dotenv()

ROOT = Path(__file__).parent.parent.parent
CASES_DIR = ROOT / "data" / "test_cases"

ROUTING_COLORS = {
    "Standard processing": "#2e7d32",
    "Manual review": "#ef6c00",
    "Fraud review": "#c62828",
    "Rejection review": "#6a1b9a",
}

COVERAGE_COLORS = {
    "Likely covered": "#2e7d32",
    "Possibly covered": "#558b2f",
    "Not covered": "#c62828",
    "Cannot determine": "#616161",
}


def _load_sample_cases() -> dict[str, dict]:
    out = {}
    if not CASES_DIR.exists():
        return out
    for path in sorted(CASES_DIR.glob("*.json")):
        try:
            out[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return out


def _init_form_state(data: dict | None) -> None:
    if data is None:
        return
    st.session_state.update(
        {
            "claim_id": data.get("claim_id", ""),
            "customer": data.get("customer", ""),
            "vehicle": data.get("vehicle", ""),
            "incident_date": date.fromisoformat(data["incident_date"])
            if data.get("incident_date")
            else date.today(),
            "claim_submitted_date": date.fromisoformat(data["claim_submitted_date"])
            if data.get("claim_submitted_date")
            else date.today(),
            "claim_description": data.get("claim_description", ""),
            "documents_submitted": "\n".join(data.get("documents_submitted", [])),
            "customer_claim_history": data.get("customer_claim_history", ""),
        }
    )


def _badge(label: str, value: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:white;padding:4px 10px;'
        f'border-radius:12px;font-size:0.85rem;font-weight:600">'
        f'{label}: {value}</span>'
    )


def _render_result(result: TriageResult) -> None:
    o = result.output

    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            _badge("Coverage", o.coverage_assessment, COVERAGE_COLORS[o.coverage_assessment]),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            _badge("Routing", o.recommended_routing, ROUTING_COLORS[o.recommended_routing]),
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            _badge("Confidence", o.confidence_level, "#1565c0"),
            unsafe_allow_html=True,
        )

    st.markdown("### Claim summary")
    st.info(o.claim_summary)

    st.markdown("### Reasoning")
    st.write(o.reasoning)
    if o.cited_clauses:
        st.caption("Cited: " + ", ".join(f"Clause {c}" for c in o.cited_clauses))

    cols = st.columns(2)
    with cols[0]:
        st.markdown("### Missing information")
        if o.missing_information:
            for item in o.missing_information:
                st.markdown(f"- {item}")
        else:
            st.markdown("_(none)_")
    with cols[1]:
        st.markdown("### Risk flags")
        if o.risk_flags:
            for item in o.risk_flags:
                st.markdown(f"- {item}")
        else:
            st.markdown("_(none)_")

    with st.expander(f"Retrieved policy clauses ({len(result.retrieved)})"):
        for c in result.retrieved:
            st.markdown(f"**[Clause {c.clause_id}]** · {c.section} · score {c.score:.2f}")
            st.code(c.text, language="markdown")

    with st.expander(
        f"Guardrail triggers "
        f"(input: {len(result.input_guard.pii_triggers) + len(result.input_guard.injection_triggers)}, "
        f"output: {len(result.output_guard_triggers)})"
    ):
        st.markdown("**Input guard**")
        st.json(
            {
                "pii": result.input_guard.pii_triggers,
                "injection": result.input_guard.injection_triggers,
            }
        )
        st.markdown("**Output guard**")
        st.json(result.output_guard_triggers)

    with st.expander(f"Audit record — {result.audit.session_id}"):
        st.caption(f"Latency: {result.latency_ms} ms")
        st.json(result.audit.to_dict())


def main() -> None:
    st.set_page_config(page_title="Motor Claim Triage", page_icon="🚗", layout="wide")
    st.title("🚗 Motor Insurance Claim Triage Assistant")
    st.caption(
        "AI assistant that supports claim officers with an initial triage "
        "recommendation. The officer makes the final decision."
    )

    # ---- Sidebar ----
    with st.sidebar:
        st.subheader("Sample cases")
        samples = _load_sample_cases()
        choice = st.selectbox(
            "Load a sample",
            options=["(none)"] + list(samples.keys()),
            index=0,
        )
        if st.button("Load into form", use_container_width=True) and choice != "(none)":
            _init_form_state(samples[choice])
            st.rerun()

        st.divider()
        st.caption(f"**Triage model:** `{TRIAGE_MODEL}`")
        st.caption("**Judge model:** `claude-opus-4-7`")
        st.caption("**Vector store:** Qdrant · multilingual-e5-large")
        st.caption("**STT:** faster-whisper · large-v3-turbo")
        st.caption("**TTS:** Edge-TTS · Microsoft Neural")

    # ---- Tabs: form vs call ----
    tab_form, tab_call = st.tabs(["📝  Form input", "📞  Call insurance"])
    with tab_form:
        _render_form_tab()
    with tab_call:
        _render_call_tab()


def _render_form_tab() -> None:
    left, right = st.columns([1, 1.2])
    with left:
        st.subheader("Claim case")
        st.text_input("Claim ID", key="claim_id", value=st.session_state.get("claim_id", ""))
        st.text_input("Customer", key="customer", value=st.session_state.get("customer", ""))
        st.text_input("Vehicle", key="vehicle", value=st.session_state.get("vehicle", ""))
        cols = st.columns(2)
        with cols[0]:
            st.date_input(
                "Incident date",
                key="incident_date",
                value=st.session_state.get("incident_date", date.today()),
            )
        with cols[1]:
            st.date_input(
                "Claim submitted",
                key="claim_submitted_date",
                value=st.session_state.get("claim_submitted_date", date.today()),
            )
        st.text_area(
            "Claim description",
            key="claim_description",
            height=150,
            value=st.session_state.get("claim_description", ""),
        )
        st.text_area(
            "Documents submitted (one per line)",
            key="documents_submitted",
            height=100,
            value=st.session_state.get("documents_submitted", ""),
        )
        st.text_input(
            "Customer claim history",
            key="customer_claim_history",
            value=st.session_state.get("customer_claim_history", ""),
        )

        st.radio(
            "Response language",
            options=["auto", "th", "en"],
            format_func=lambda x: {
                "auto": "Auto-detect from description",
                "th": "Force Thai 🇹🇭",
                "en": "Force English 🇬🇧",
            }[x],
            key="response_language",
            index=0,
            horizontal=True,
        )

        run_clicked = st.button("Run triage", type="primary", use_container_width=True)

    with right:
        st.subheader("Triage recommendation")
        if run_clicked:
            if not st.session_state.get("claim_id") or not st.session_state.get("claim_description"):
                st.error("Claim ID and description are required.")
                return
            try:
                claim = ClaimInput(
                    claim_id=st.session_state["claim_id"],
                    customer=st.session_state["customer"],
                    vehicle=st.session_state["vehicle"],
                    incident_date=st.session_state["incident_date"],
                    claim_submitted_date=st.session_state["claim_submitted_date"],
                    claim_description=st.session_state["claim_description"],
                    documents_submitted=[
                        d.strip()
                        for d in st.session_state["documents_submitted"].splitlines()
                        if d.strip()
                    ],
                    customer_claim_history=st.session_state["customer_claim_history"],
                    response_language=st.session_state.get("response_language", "auto"),
                )
            except Exception as e:
                st.error(f"Invalid claim input: {e}")
                return

            with st.spinner("Retrieving policy and calling Claude Sonnet..."):
                agent = TriageAgent()
                result = agent.run(claim)
            _render_result(result)
        else:
            st.info(
                "Load a sample from the sidebar or fill in the form on the left, "
                "then click **Run triage**."
            )


def _render_call_tab() -> None:
    """Multi-turn phone-style intake routed through the SupervisorAgent."""
    from app.agents.conversation import ConversationState
    from app.agents.supervisor import SupervisorAgent

    # --- Initial state: just the "Call" button -----------------------
    if "call_state" not in st.session_state:
        st.markdown(
            "### 📞 Call ABC Insurance\n"
            "Press the button to start a voice intake call. The AI will greet "
            "you in Thai and English, you choose your preferred language, and "
            "then we talk through your claim one question at a time."
        )
        if st.button(
            "📞  Call ABC Insurance",
            type="primary",
            use_container_width=True,
            key="call_start_btn",
        ):
            supervisor = SupervisorAgent()
            state = supervisor.start()
            st.session_state["call_state"] = state
            st.rerun()
        return

    # --- Call in progress --------------------------------------------
    state: ConversationState = st.session_state["call_state"]
    supervisor = SupervisorAgent()

    _render_chat_messages(state)

    # If we are between user-send and AI-response, show a "thinking" bubble
    # and perform the LLM call in this same rerun.
    if state.processing:
        _render_processing_bubble(state)
        _run_pending_llm_turn(supervisor, state)
        st.rerun()

    # Supervisor log — show which specialist handled each turn
    with st.expander(f"🧭 Supervisor log ({len(state.supervisor_log)} decisions)"):
        for d in state.supervisor_log:
            st.markdown(
                f"- **turn {d.turn_index}** · `{d.specialist}` · "
                f"action = `{d.action}` · {d.note}"
            )

    # If we already ran triage, show it and stop here
    if state.triage is not None:
        st.divider()
        st.markdown("### 🧾 Triage recommendation")
        _render_result(state.triage)
        if st.button("☎️  End call and start a new one", use_container_width=True):
            del st.session_state["call_state"]
            st.rerun()
        return

    # If language is still unset, require the caller to pick before anything else
    if state.language is None:
        st.divider()
        st.markdown("#### Please choose your language / กรุณาเลือกภาษา")
        cols = st.columns(2)
        with cols[0]:
            if st.button(
                "🇹🇭  ภาษาไทย",
                use_container_width=True,
                type="primary",
                key="call_pick_th",
            ):
                supervisor.set_language(state, "th")
                st.rerun()
        with cols[1]:
            if st.button(
                "🇬🇧  English",
                use_container_width=True,
                type="primary",
                key="call_pick_en",
            ):
                supervisor.set_language(state, "en")
                st.rerun()
        return

    # Otherwise collect the next customer turn
    st.divider()
    st.markdown("#### 🎙 Your turn")
    audio_blob = st.audio_input(
        "Press to record, press again to stop.",
        key=f"call_audio_{len(state.turns)}",
    )
    if audio_blob is None:
        return

    if st.button(
        "➡️  Send",
        type="primary",
        use_container_width=True,
        key=f"call_send_{len(state.turns)}",
    ):
        _begin_customer_turn(state, audio_blob.getvalue())
        st.rerun()


def _render_chat_messages(state) -> None:
    """Render the conversation + autoplay TTS for the latest AI message only."""
    from app.voice.tts import synthesize

    cached: dict[int, bytes] = st.session_state.setdefault("call_tts_cache", {})
    last_autoplay = st.session_state.get("call_last_tts_idx", -1)

    for i, turn in enumerate(state.turns):
        _render_bubble(turn.role, turn.text)
        if turn.role != "assistant":
            continue
        if i not in cached:
            try:
                cached[i] = synthesize(turn.text, lang=turn.lang)
            except Exception as e:  # noqa: BLE001
                st.caption(f"(TTS unavailable for this message: {e})")
                cached[i] = b""
        if cached[i]:
            autoplay = (i == len(state.turns) - 1) and i > last_autoplay
            st.audio(cached[i], format="audio/mp3", autoplay=autoplay)
            if autoplay:
                st.session_state["call_last_tts_idx"] = i


def _render_bubble(role: str, text: str) -> None:
    role_label = "🤖 AI" if role == "assistant" else "🧑 You"
    bg = "#2d2d33" if role == "assistant" else "#1c3a5e"
    align = "flex-start" if role == "assistant" else "flex-end"
    st.markdown(
        f"""<div style="display:flex;justify-content:{align};margin:6px 0">
          <div style="background:{bg};color:#f0f0f0;padding:10px 14px;
                      border-radius:14px;max-width:72%;font-size:0.95rem;">
            <div style="opacity:0.6;font-size:0.75rem;margin-bottom:4px">{role_label}</div>
            {text}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_processing_bubble(state) -> None:
    """Show an animated placeholder while the LLM is thinking."""
    hint = {
        "th": "⋯ ดิฉันกำลังคิดสักครู่นะคะ",
        "en": "⋯ Let me think for a moment…",
        None: "⋯ Thinking…",
    }[state.language]
    st.markdown(
        f"""<div style="display:flex;justify-content:flex-start;margin:6px 0">
          <div style="background:#2d2d33;color:#aaa;padding:10px 14px;
                      border-radius:14px;max-width:72%;font-size:0.95rem;
                      font-style:italic">
            <div style="opacity:0.6;font-size:0.75rem;margin-bottom:4px">🤖 AI</div>
            <span class="dots">{hint}</span>
          </div>
        </div>
        <style>
          @keyframes dots {{ 0% {{opacity:0.4}} 50% {{opacity:1}} 100% {{opacity:0.4}} }}
          .dots {{ animation: dots 1.4s infinite ease-in-out; }}
        </style>""",
        unsafe_allow_html=True,
    )


def _begin_customer_turn(state, audio_bytes: bytes) -> None:
    """Transcribe the customer's audio, stash it, and flip `processing`
    so the next rerun shows a loader AND runs the supervisor turn.

    We only transcribe here; the user turn is appended inside the
    supervisor on the next rerun so the supervisor_log order matches
    the chat order.
    """
    from app.voice.stt import transcribe

    with st.spinner("Transcribing…"):
        try:
            transcript = transcribe(audio_bytes, language=state.language)
        except Exception as e:  # noqa: BLE001
            st.error(f"Transcription failed: {e}")
            return

    if not transcript.text.strip():
        st.warning("No speech detected — please try again.")
        return

    st.session_state["call_pending_user_text"] = transcript.text
    state.processing = True


def _run_pending_llm_turn(supervisor, state) -> None:
    """Second half of a user turn: delegate to SupervisorAgent."""
    import uuid as _uuid
    from datetime import datetime as _dt

    user_text = st.session_state.pop("call_pending_user_text", "")
    if not user_text:
        state.processing = False
        return

    claim_id = (
        f"CLM-CALL-{_dt.now().strftime('%Y%m%d-%H%M%S')}-{_uuid.uuid4().hex[:4]}"
    )

    try:
        supervisor.handle_user_turn(state, user_text, claim_id=claim_id)
    except Exception as e:  # noqa: BLE001
        st.error(f"Supervisor turn failed: {e}")

    state.processing = False


if __name__ == "__main__":
    main()
