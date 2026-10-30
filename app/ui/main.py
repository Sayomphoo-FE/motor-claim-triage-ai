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
from datetime import date  # noqa: E402

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
    """One pill, sized to its content, on its own line.

    Wrapping the span in a block-level div with inline-block inside
    prevents the pill from stretching to column width AND prevents
    the label+value from wrapping onto a second line (e.g.
    'Possibly covered' used to break mid-pill when squeezed into a
    1/3 st.columns slot).
    """
    return (
        f'<div style="margin:0 0 10px 0;">'
        f'<span style="display:inline-block;background:{color};color:white;'
        f'padding:6px 14px;border-radius:14px;font-size:0.9rem;'
        f'font-weight:600;white-space:nowrap;">'
        f'{label}: {value}</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------
# Floating realtime pipeline trace
# ---------------------------------------------------------------------
#
# The whole pipeline is 7 named stages (see TriageAgent._emit). We
# pre-list all 7 up-front and let completed steps hydrate the panel as
# the agent's `on_step` callback fires. This gives a reviewer a proper
# "progress bar" feel instead of only seeing results after the fact.
#
# Positioning: inject raw HTML with `position: fixed; bottom; right;`.
# Streamlit renders Python-produced markdown into an iframe-free flow
# container, so fixed positioning on an inner <div> escapes layout and
# anchors to the viewport without disturbing the rest of the page.

PIPELINE_STAGES = [
    ("🧹", "Input Guardrail"),
    ("🔎", "RAG Query Generation"),
    ("📚", "Vector Retrieval"),
    ("✏️", "Prompt Build"),
    ("🤖", "Claude Sonnet"),
    ("✅", "Output Guardrail"),
    ("📝", "Audit Write"),
]

_STATUS_STYLE = {
    "ok":      {"bar": "#10b981", "pill_bg": "#064e3b", "pill_fg": "#6ee7b7", "label": "OK"},
    "warn":    {"bar": "#f59e0b", "pill_bg": "#78350f", "pill_fg": "#fcd34d", "label": "FIRED"},
    "info":    {"bar": "#60a5fa", "pill_bg": "#1e3a8a", "pill_fg": "#93c5fd", "label": "INFO"},
    "running": {"bar": "#f472b6", "pill_bg": "#831843", "pill_fg": "#fbcfe8", "label": "RUNNING"},
    "pending": {"bar": "#334155", "pill_bg": "#1e293b", "pill_fg": "#64748b", "label": "PENDING"},
}


def _inline_trace_html(completed: list, running: bool) -> str:
    """Produce the inline HTML for the pipeline trace panel.

    `completed` is a list of `TraceStep` the agent has already emitted;
    we render each of the pre-known 7 stages either as its completed
    state, as the currently-running stage (pulse), or as a greyed-out
    pending stage. Rendered as a normal inline block — the slot where
    it lives dictates its position, so the caller places it at the
    bottom of the page.
    """
    cards: list[str] = []
    total_ms = sum(s.duration_ms for s in completed) or 1
    max_ms = max((s.duration_ms for s in completed), default=1) or 1
    next_idx = len(completed) + 1  # 1-based

    for i, (icon, name) in enumerate(PIPELINE_STAGES, start=1):
        done = next((s for s in completed if s.index == i), None)
        if done is not None:
            style = _STATUS_STYLE.get(done.status, _STATUS_STYLE["ok"])
            bar_width = max(3, int(done.duration_ms / max_ms * 100))
            details = done.details
            time_label = f"{done.duration_ms:>5} ms"
            animation = ""
        elif running and i == next_idx:
            style = _STATUS_STYLE["running"]
            bar_width = 100
            details = "⏳ running…"
            time_label = ""
            animation = "animation: pulse 1.4s ease-in-out infinite;"
        else:
            style = _STATUS_STYLE["pending"]
            bar_width = 10
            details = "awaiting earlier stages"
            time_label = ""
            animation = ""

        cards.append(f"""
        <div style="margin:8px 0;padding:12px 14px;background:#0b1220;
                    border-left:4px solid {style['bar']};border-radius:8px;
                    font-size:0.88rem;{animation}">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
            <span style="font-size:1.3rem">{icon}</span>
            <span style="font-weight:600;color:#f1f5f9;flex:1">
              Step {i}. {name}
            </span>
            <span style="color:#94a3b8;font-family:monospace;font-size:0.82rem">
              {time_label}
            </span>
            <span style="background:{style['pill_bg']};color:{style['pill_fg']};
                         padding:2px 10px;border-radius:12px;font-size:0.68rem;
                         font-weight:600;letter-spacing:0.5px">
              {style['label']}
            </span>
          </div>
          <div style="color:#cbd5e1;font-size:0.82rem;margin-bottom:6px">
            {details}
          </div>
          <div style="height:4px;background:#1e293b;border-radius:2px;overflow:hidden">
            <div style="width:{bar_width}%;height:100%;background:{style['bar']}"></div>
          </div>
        </div>""")

    done_count = len(completed)
    status_header = (
        f"🔄 Pipeline execution · <b>running</b> · step {done_count}/{len(PIPELINE_STAGES)}"
        if running
        else f"✅ Pipeline execution · <b>complete</b> · total {total_ms:,} ms"
    )
    footer_caption = (
        "🧹 Input Guardrail → 🔎 Query Gen → 📚 Qdrant Retrieve → "
        "✏️ Prompt Build → 🤖 Claude Sonnet → ✅ Output Guardrail → "
        "📝 Audit Write"
    )

    html = f"""
    <style>
      @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.55; }}
      }}
    </style>
    <div style="margin-top:28px;padding:18px 20px;background:#0f172a;
                border:1px solid #334155;border-radius:14px;
                font-family:'Helvetica Neue',sans-serif">
      <div style="color:#f1f5f9;font-weight:600;margin-bottom:4px;font-size:1.05rem">
        {status_header}
      </div>
      <div style="color:#64748b;font-size:0.78rem;margin-bottom:14px">
        {footer_caption}
      </div>
      {''.join(cards)}
    </div>"""
    # Streamlit's markdown parser treats any line indented 4+ spaces as
    # a code block even inside `unsafe_allow_html=True`, which would
    # dump our literal HTML to the page. Strip the per-line indentation
    # before returning so every line starts flush-left.
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


def _render_pipeline_trace(result: TriageResult) -> None:
    """No-op in the main result area — the pipeline trace is rendered
    by the Run-triage handler into its own slot at the bottom of the
    page. The agent's `trace` is still available on
    `TriageResult.trace` for anyone who needs it outside the UI."""
    return


def _render_result(result: TriageResult) -> None:
    o = result.output

    _render_pipeline_trace(result)
    st.divider()

    # Stacked vertical pills — each on its own line, auto-fit to text
    # width, no wrap. Replaces the earlier 3-column layout that squeezed
    # long values like "Possibly covered" onto a second line.
    st.markdown(
        _badge("Coverage", o.coverage_assessment, COVERAGE_COLORS[o.coverage_assessment])
        + _badge("Routing", o.recommended_routing, ROUTING_COLORS[o.recommended_routing])
        + _badge("Confidence", o.confidence_level, "#1565c0"),
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
        st.caption("**Vector store:** Qdrant · bge-small-en-v1.5")

    # ---- Main form ----
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
                )
            except Exception as e:
                st.error(f"Invalid claim input: {e}")
                return

            # Reserve two slots in DOM order so the triage result cards
            # sit above the pipeline trace panel. Both slots can still
            # be filled from code that runs *after* this point — the
            # callback-driven updates during agent.run() will target the
            # already-reserved trace slot.
            result_container = st.container()
            trace_slot = st.empty()

            trace_slot.html(_inline_trace_html([], running=True))
            completed: list = []

            def _on_step(step) -> None:
                completed.append(step)
                trace_slot.html(_inline_trace_html(completed, running=True))

            with st.spinner("Retrieving policy and calling Claude Sonnet..."):
                agent = TriageAgent()
                result = agent.run(claim, on_step=_on_step)

            # Final trace — mark the panel complete; it stays visible
            trace_slot.html(_inline_trace_html(result.trace, running=False))
            # Fill the result container last so the badges, summary, and
            # cards render into the slot ABOVE the trace panel.
            with result_container:
                _render_result(result)
        else:
            st.info(
                "Load a sample from the sidebar or fill in the form on the left, "
                "then click **Run triage**."
            )


if __name__ == "__main__":
    main()
