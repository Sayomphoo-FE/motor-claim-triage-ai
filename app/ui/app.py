"""Streamlit UI — officer-facing claim triage demo.

Layout:
  Sidebar     : sample case loader + model info
  Main left   : claim form (editable) + "Run triage" button
  Main right  : triage output cards, retrieved clauses, guardrails,
                audit JSON.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

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

            with st.spinner("Retrieving policy and calling Claude Sonnet..."):
                agent = TriageAgent()
                result = agent.run(claim)
            _render_result(result)
        else:
            st.info(
                "Load a sample from the sidebar or fill in the form on the left, "
                "then click **Run triage**."
            )


if __name__ == "__main__":
    main()
