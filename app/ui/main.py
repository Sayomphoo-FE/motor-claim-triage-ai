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
from pydantic import ValidationError  # noqa: E402

from app.agents.photo import analyze_damage_photos
from app.agents.triage import TRIAGE_MODEL, TriageAgent, TriageResult
from app.schemas import (
    CLAIM_TYPES,
    HISTORY_CLAIM_TYPES,
    HISTORY_FLAGS,
    ClaimInput,
)

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

DOC_TYPES: list[str] = [
    "Claim form",
    "Driving license",
    "Vehicle registration",
    "Incident report",
    "Police report",
    "Third-party contact info",
    "Third-party evidence",
]


def _parse_vehicle(vehicle_str: str) -> tuple[str, str, str]:
    """Split 'Toyota Camry 2.5G 2022' → ('Toyota', 'Camry 2.5G', '2022')."""
    parts = vehicle_str.strip().split()
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    if parts[-1].isdigit() and len(parts[-1]) == 4:
        return parts[0], " ".join(parts[1:-1]), parts[-1]
    return parts[0], " ".join(parts[1:]), ""


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
    submitted_lower = {s.lower() for s in data.get("documents_submitted", [])}
    for i, doc_name in enumerate(DOC_TYPES):
        st.session_state[f"doc_{i}"] = any(
            doc_name.lower() in s or s in doc_name.lower()
            for s in submitted_lower
        )
    st.session_state.pop("photo_analysis", None)
    st.session_state.pop("last_result", None)
    make, model, year = _parse_vehicle(data.get("vehicle", ""))
    claim_type = data.get("claim_type", "")
    st.session_state.update(
        {
            "claim_id": data.get("claim_id", ""),
            "policy_number": data.get("policy_number", ""),
            "claim_type": claim_type if claim_type in CLAIM_TYPES else CLAIM_TYPES[0],
            "customer": data.get("customer", ""),
            "vehicle_make": make,
            "vehicle_model": model,
            "vehicle_year": int(year) if year.isdigit() else date.today().year,
            "incident_date": date.fromisoformat(data["incident_date"])
            if data.get("incident_date")
            else date.today(),
            "incident_location": data.get("incident_location", ""),
            "claim_submitted_date": date.fromisoformat(data["claim_submitted_date"])
            if data.get("claim_submitted_date")
            else date.today(),
            "claim_description": data.get("claim_description", ""),
        }
    )
    # Structured history fields
    _count = int(data.get("prior_claims_count", 0))
    st.session_state["hist_has_claims_label"] = "Has prior claims" if _count > 0 else "No claims"
    st.session_state["hist_count_num"] = _count if _count > 0 else 1
    _period_str = data.get("prior_claims_period", "24 months")
    try:
        st.session_state["hist_period_months"] = int(_period_str.split()[0])
    except (ValueError, IndexError):
        st.session_state["hist_period_months"] = 24
    _types = set(data.get("prior_claim_types", []))
    for _i, _t in enumerate(HISTORY_CLAIM_TYPES):
        st.session_state[f"hist_type_{_i}"] = _t in _types
    _flags = set(data.get("history_flags", []))
    for _i, _f in enumerate(HISTORY_FLAGS):
        st.session_state[f"hist_flag_{_i}"] = _f in _flags


def _badge(label: str, value: str, color: str) -> str:
    """One pill, sized to its content, on its own line."""
    return (
        f'<div style="margin:0 0 10px 0;">'
        f'<span style="display:inline-block;background:{color};color:white;'
        f'padding:6px 14px;border-radius:14px;font-size:0.9rem;'
        f'font-weight:600;white-space:nowrap;">'
        f'{label}: {value}</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------
# Pipeline trace panel
# ---------------------------------------------------------------------

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
    cards: list[str] = []
    total_ms = sum(s.duration_ms for s in completed) or 1
    max_ms = max((s.duration_ms for s in completed), default=1) or 1
    next_idx = len(completed) + 1

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
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


def _governance_html(result: TriageResult) -> str:
    """Build the always-visible AI Governance panel HTML.

    Shows four metric tiles (citation audit, output guard, RAG grounding,
    input guard) so reviewers can see hallucination controls and RAG quality
    without opening any expander. If the output guardrail fired and modified
    the output, an explicit before→after block is rendered below the tiles.
    """
    # ── Citation audit ─────────────────────────────────────────────────
    # Compare what Claude originally cited (raw_output) vs what survived
    # the output guardrail (output). Any clause that was stripped was
    # hallucinated — it wasn't in the retrieved context.
    original_cited = set(result.raw_output.cited_clauses)
    final_cited = set(result.output.cited_clauses)
    stripped_clauses = original_cited - final_cited
    verified_count = len(final_cited)
    total_original = len(original_cited)
    citation_ok = len(stripped_clauses) == 0

    # ── Output guard modifications ─────────────────────────────────────
    guard_ok = len(result.output_guard_triggers) == 0
    guard_mods: list[str] = []
    for t in result.output_guard_triggers:
        if t.startswith("citation_invalid:"):
            clause = t.split(":", 1)[1]
            guard_mods.append(
                f'Clause <b>{clause}</b> hallucinated — not in retrieved context, '
                f'stripped from cited_clauses'
            )
        elif "not_covered_without_exclusion" in t:
            guard_mods.append(
                'Coverage: <b>"Not covered"</b> → <b>"Cannot determine"</b> — '
                'no Section&nbsp;2 exclusion was retrieved, so "Not covered" verdict blocked'
            )
        elif "low_confidence_standard_routing" in t:
            guard_mods.append(
                'Routing: <b>"Standard processing"</b> → <b>"Manual review"</b> — '
                'Low confidence must not auto-approve; escalated per policy rule'
            )
        else:
            guard_mods.append(t)

    # ── RAG coverage ───────────────────────────────────────────────────
    _all_sections = ["Covered Events", "Exclusions", "Required Documents", "Routing Rules"]
    _short = {"Covered Events": "Covered Events", "Exclusions": "Exclusions",
              "Required Documents": "Required Docs", "Routing Rules": "Routing Rules"}
    sections_hit = {c.section for c in result.retrieved}
    section_badges = " &nbsp;·&nbsp; ".join(
        f'<span style="color:#6ee7b7">✓</span>&nbsp;{_short[s]}'
        if s in sections_hit
        else f'<span style="color:#ef4444">✗</span>&nbsp;{_short[s]}'
        for s in _all_sections
    )
    avg_score = sum(c.score for c in result.retrieved) / max(len(result.retrieved), 1)

    # ── Input guard ────────────────────────────────────────────────────
    pii_count = len(result.input_guard.pii_triggers)
    inject_count = len(result.input_guard.injection_triggers)
    input_clean = pii_count == 0 and inject_count == 0

    # ── Build tiles ────────────────────────────────────────────────────
    def _tile(bg: str, lc: str, label: str, value: str, sub: str) -> str:
        return (
            f'<div style="background:{bg};border-radius:10px;padding:10px 14px;'
            f'flex:1;min-width:140px">'
            f'<div style="color:{lc};font-size:0.70rem;font-weight:700;'
            f'letter-spacing:0.5px;margin-bottom:4px">{label}</div>'
            f'<div style="color:#f1f5f9;font-size:1.05rem;font-weight:700;line-height:1.3">{value}</div>'
            f'<div style="color:{lc};opacity:0.85;font-size:0.72rem;margin-top:3px">{sub}</div>'
            f'</div>'
        )

    cit_tile = (
        _tile("#064e3b", "#6ee7b7", "CITATION AUDIT",
              f"{verified_count}/{total_original} verified ✅",
              "All cited clauses in RAG context")
        if citation_ok else
        _tile("#78350f", "#fcd34d", "CITATION AUDIT",
              f"{verified_count}/{total_original} verified ⚠️",
              f"{len(stripped_clauses)} hallucinated — blocked")
    )

    guard_tile = (
        _tile("#064e3b", "#6ee7b7", "OUTPUT GUARD",
              "No changes ✅",
              "Safety invariants passed")
        if guard_ok else
        _tile("#78350f", "#fcd34d", "OUTPUT GUARD",
              f"{len(guard_mods)} correction(s) ⚠️",
              "Output modified by rule engine")
    )

    rag_tile = _tile(
        "#1e3a8a", "#93c5fd", "RAG GROUNDING",
        f"{len(result.retrieved)} clauses · {len(sections_hit)}/4 sections",
        f"Avg relevance {avg_score:.2f} · 4 targeted queries",
    )

    if input_clean:
        inp_tile = _tile("#0f1629", "#a78bfa", "INPUT GUARD",
                         "Clean ✅",
                         "No PII · No injection detected")
    else:
        parts = ([f"{pii_count} PII"] if pii_count else []) + \
                ([f"{inject_count} injection"] if inject_count else [])
        inp_tile = _tile("#2e1065", "#c4b5fd", "INPUT GUARD",
                         " · ".join(parts) + " 🔒",
                         "Masked / flagged before LLM")

    tiles_row = (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;'
        f'margin-bottom:{"12px" if (guard_mods or True) else "0"}">'
        f'{cit_tile}{guard_tile}{rag_tile}{inp_tile}'
        f'</div>'
    )

    # ── Guard modification details ─────────────────────────────────────
    mods_block = ""
    if guard_mods:
        items = "".join(
            f'<div style="border-left:3px solid #f59e0b;padding:6px 10px;margin:4px 0;'
            f'background:#1c1200;border-radius:0 6px 6px 0;color:#fde68a;font-size:0.82rem">'
            f'⚠️ {m}</div>'
            for m in guard_mods
        )
        mods_block = (
            f'<div style="margin-top:10px">'
            f'<div style="color:#fcd34d;font-size:0.75rem;font-weight:700;margin-bottom:5px">'
            f'GUARDRAIL CORRECTIONS APPLIED:</div>'
            f'{items}</div>'
        )

    # ── RAG section coverage strip ──────────────────────────────────────
    rag_strip = (
        f'<div style="margin-top:10px;padding:7px 12px;background:#0b1120;'
        f'border-radius:8px;font-size:0.78rem;color:#94a3b8">'
        f'<span style="color:#60a5fa;font-weight:700">📚 Policy sections retrieved:&nbsp;</span>'
        f'{section_badges}'
        f'</div>'
    )

    html = (
        f'<div style="background:#0f172a;border:1px solid #334155;border-radius:14px;'
        f'padding:16px 18px;margin:14px 0;font-family:\'Helvetica Neue\',sans-serif">'
        f'<div style="color:#f1f5f9;font-weight:700;font-size:0.95rem;margin-bottom:14px">'
        f'🛡️ AI Governance &amp; Hallucination Controls</div>'
        f'{tiles_row}{mods_block}{rag_strip}'
        f'</div>'
    )
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


def _ai_ctx_html(chunks: list, json_buf: str, streaming: bool) -> str:
    """HTML panel showing Claude's context (retrieved clauses) + live streaming output."""
    sections = {c.section for c in chunks}
    top = sorted(chunks, key=lambda c: c.score, reverse=True)[:7]

    rows = "".join(
        f'<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid #1e293b;'
        f'font-size:0.72rem">'
        f'<span style="color:#60a5fa;font-family:monospace;min-width:52px">[{c.clause_id}]</span>'
        f'<span style="flex:1;color:#cbd5e1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{c.section}</span>'
        f'<span style="color:#6ee7b7;font-family:monospace">{c.score:.2f}</span>'
        f'</div>'
        for c in top
    )
    if len(chunks) > 7:
        rows += (
            f'<div style="font-size:0.68rem;color:#475569;padding:3px 0">'
            f'… and {len(chunks) - 7} more clauses</div>'
        )

    if json_buf:
        safe = json_buf.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cursor = '<span style="animation:blink 1s step-end infinite">▌</span>' if streaming else " ✅"
        label = "▶ Generating..." if streaming else "✅ Complete"
        label_color = "#f59e0b" if streaming else "#6ee7b7"
        json_block = (
            f'<div style="color:{label_color};font-size:0.72rem;margin:6px 0 4px 0">{label}</div>'
            f'<pre style="margin:0;padding:8px;background:#020b18;border-radius:6px;'
            f'font-size:0.65rem;color:#a5f3fc;overflow:auto;max-height:180px;'
            f'line-height:1.45;white-space:pre-wrap;word-break:break-all">'
            f'{safe}{cursor}</pre>'
        )
    else:
        json_block = (
            f'<div style="color:#475569;font-size:0.74rem;text-align:center;'
            f'padding:10px 0">⏳ Waiting for Claude to start generating...</div>'
        )

    return (
        f'<style>@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}</style>'
        f'<div style="background:#0f172a;border:1px solid #334155;border-radius:12px;'
        f'padding:12px 14px;margin-top:14px;font-family:\'Helvetica Neue\',sans-serif">'
        f'<div style="color:#f1f5f9;font-weight:700;font-size:0.85rem;margin-bottom:6px">'
        f'🤖 Claude Sonnet — Step 4</div>'
        f'<div style="color:#64748b;font-size:0.70rem;margin-bottom:6px">'
        f'📋 {len(chunks)} clauses · {len(sections)}/4 sections sent as context</div>'
        f'{rows}'
        f'<div style="border-top:1px solid #1e293b;margin-top:6px;padding-top:4px">'
        f'{json_block}'
        f'</div>'
        f'</div>'
    )


def _render_governance_panel(result: TriageResult) -> None:
    """Full-width AI Governance panel: summary tiles + per-section detail expanders."""
    st.divider()
    st.markdown(_governance_html(result), unsafe_allow_html=True)

    # Precompute shared values
    orig_cited = set(result.raw_output.cited_clauses)
    final_cited = set(result.output.cited_clauses)
    stripped_clauses = orig_cited - final_cited
    retrieved_map = {c.clause_id: c for c in result.retrieved}
    triggers_set = set(result.output_guard_triggers)
    sections_hit = {c.section for c in result.retrieved}
    avg_score = sum(c.score for c in result.retrieved) / max(len(result.retrieved), 1)

    col_a, col_b = st.columns(2)

    # ── Citation Audit ──────────────────────────────────────────────
    with col_a:
        _cit_lbl = (
            f"🔍 Citation Audit — ⚠️ {len(stripped_clauses)} clause(s) stripped"
            if stripped_clauses
            else f"🔍 Citation Audit — {len(final_cited)}/{len(orig_cited)} verified ✅"
        )
        with st.expander(_cit_lbl):
            if not orig_cited:
                st.caption("Claude did not cite any clauses.")
            else:
                rows = []
                for cid in sorted(orig_cited):
                    r = retrieved_map.get(cid)
                    rows.append({
                        "Clause": cid,
                        "Section": r.section if r else "—",
                        "Score": f"{r.score:.3f}" if r else "—",
                        "In RAG context": "✅ Yes" if r else "❌ No",
                        "Final output": "✅ Kept" if cid in final_cited else "⚠️ Stripped",
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
                if stripped_clauses:
                    st.warning(
                        f"Hallucinated clauses stripped before officer sees output: "
                        f"`{', '.join(sorted(stripped_clauses))}`"
                    )
                else:
                    st.success("Zero hallucinated citations — all clause references traceable to retrieved policy.")

    # ── RAG Grounding ───────────────────────────────────────────────
    with col_a:
        with st.expander(
            f"📚 RAG Grounding — {len(result.retrieved)} clauses · "
            f"{len(sections_hit)}/4 sections · avg score {avg_score:.2f}"
        ):
            rows = [
                {
                    "Clause": c.clause_id,
                    "Section": c.section,
                    "Score": round(c.score, 3),
                    "Preview": c.text.split("\n")[0][:55] if c.text else "—",
                }
                for c in sorted(result.retrieved, key=lambda x: x.score, reverse=True)
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.caption(
                "Strategy: 4 section-filtered sub-queries (sections 1–4) · "
                "top-3 per query · deduplicated by max score per clause"
            )

    # ── Output Guard ────────────────────────────────────────────────
    with col_b:
        rule2_fired = "not_covered_without_exclusion" in triggers_set
        rule3_fired = "low_confidence_standard_routing" in triggers_set
        rule2_applicable = result.raw_output.coverage_assessment == "Not covered"
        rule3_applicable = result.raw_output.confidence_level == "Low"

        _guard_lbl = (
            f"✅ Output Guard — {len(result.output_guard_triggers)} correction(s) applied"
            if result.output_guard_triggers
            else "✅ Output Guard — all 3 rules passed ✅"
        )
        with st.expander(_guard_lbl):
            # Rule 1
            if stripped_clauses:
                st.error(
                    f"**Rule 1 — Citation validity:** ⚠️ FIRED  \n"
                    f"Stripped `{', '.join(sorted(stripped_clauses))}` — not in retrieved context"
                )
            else:
                st.success("**Rule 1 — Citation validity:** All cited clauses in RAG context ✅")

            # Rule 2
            if rule2_fired:
                st.warning(
                    '**Rule 2 — "Not covered" requires Section-2 exclusion:** ⚠️ FIRED  \n'
                    'No Section-2 clause retrieved → downgraded to "Cannot determine"'
                )
            elif rule2_applicable:
                st.success(
                    '**Rule 2 — "Not covered" requires Section-2 exclusion:** ✅  \n'
                    '"Not covered" verdict allowed — Section-2 exclusion was retrieved'
                )
            else:
                st.info('**Rule 2 — "Not covered" requires Section-2 exclusion:** ➖ Not applicable')

            # Rule 3
            if rule3_fired:
                st.warning(
                    '**Rule 3 — Low confidence routing:** ⚠️ FIRED  \n'
                    '"Standard processing" → "Manual review" (Low confidence must escalate)'
                )
            elif rule3_applicable:
                st.success(
                    '**Rule 3 — Low confidence routing:** ✅  \n'
                    'Confidence Low — routing already non-Standard'
                )
            else:
                st.info('**Rule 3 — Low confidence routing:** ➖ Not applicable')

            # Before / after comparison if any rule fired
            if result.output_guard_triggers:
                st.divider()
                st.caption("Before → After guardrail:")
                bc1, bc2 = st.columns(2)
                with bc1:
                    st.markdown("**Before (Claude raw output)**")
                    st.markdown(f"Coverage: `{result.raw_output.coverage_assessment}`")
                    st.markdown(f"Routing: `{result.raw_output.recommended_routing}`")
                    st.markdown(f"Cited: `{result.raw_output.cited_clauses}`")
                with bc2:
                    st.markdown("**After (guardrail applied)**")
                    st.markdown(f"Coverage: `{result.output.coverage_assessment}`")
                    st.markdown(f"Routing: `{result.output.recommended_routing}`")
                    st.markdown(f"Cited: `{result.output.cited_clauses}`")

    # ── Input Guard ─────────────────────────────────────────────────
    with col_b:
        pii = result.input_guard.pii_triggers
        inj = result.input_guard.injection_triggers
        _inp_lbl = (
            f"🧹 Input Guard — {len(pii)} PII · {len(inj)} injection detected"
            if (pii or inj)
            else "🧹 Input Guard — clean ✅"
        )
        with st.expander(_inp_lbl):
            if pii:
                st.markdown("**PII detected & masked before LLM:**")
                for p in pii:
                    st.markdown(f"- 🔒 `{p}`")
            else:
                st.success("No PII detected in claim text.")

            st.markdown("")
            if inj:
                st.markdown("**Injection patterns flagged:**")
                for inj_t in inj:
                    st.markdown(f"- ⚠️ `{inj_t}`")
            else:
                st.success("No injection patterns detected.")

            st.markdown("")
            st.markdown("**Sanitized text sent to Claude:**")
            preview = result.input_guard.sanitized
            st.code(
                preview[:500] + ("…" if len(preview) > 500 else ""),
                language="text",
            )


def _render_result(result: TriageResult) -> None:
    o = result.output

    st.divider()
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

    with st.expander(f"📋 Retrieved policy clauses ({len(result.retrieved)}) — click to inspect RAG evidence"):
        for c in result.retrieved:
            st.markdown(f"**[Clause {c.clause_id}]** · {c.section} · score {c.score:.2f}")
            st.code(c.text, language="markdown")

    with st.expander(
        f"🔍 Guardrail detail — "
        f"input: {len(result.input_guard.pii_triggers)} PII · "
        f"{len(result.input_guard.injection_triggers)} injection · "
        f"output: {len(result.output_guard_triggers)} triggers"
    ):
        st.markdown("**Input guard — free-text sanitisation**")
        st.json(
            {
                "pii_masked": result.input_guard.pii_triggers,
                "injection_flagged": result.input_guard.injection_triggers,
            }
        )
        st.markdown("**Output guard — post-LLM invariant checks**")
        st.json(result.output_guard_triggers if result.output_guard_triggers else ["(none — output passed all checks)"])

    with st.expander(f"📝 Audit record — {result.audit.session_id}"):
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

    # Determine run state early — used for button disabled flag below.
    _is_running = st.session_state.get("triage_running", False)

    # ---- Main layout ----
    left, right = st.columns([1, 1.2])

    with left:
        st.subheader("Claim case")

        # ── Claim details ──────────────────────────────────────────
        st.markdown("##### 🔖 Claim details")
        col_id, col_pol = st.columns([1, 1])
        with col_id:
            st.text_input(
                "Claim ID",
                key="claim_id",
                placeholder="e.g. CLM-2026-00001",
                value=st.session_state.get("claim_id", ""),
            )
        with col_pol:
            st.text_input(
                "Policy number",
                key="policy_number",
                placeholder="e.g. POL-2026-14201",
                value=st.session_state.get("policy_number", ""),
            )
        col_cust, col_type = st.columns([1, 1])
        with col_cust:
            st.text_input(
                "Customer name / ID",
                key="customer",
                placeholder="e.g. C-14201",
                value=st.session_state.get("customer", ""),
            )
        with col_type:
            _ct_opts = ["(select)"] + CLAIM_TYPES
            _ct_current = st.session_state.get("claim_type", "")
            _ct_idx = _ct_opts.index(_ct_current) if _ct_current in _ct_opts else 0
            st.selectbox(
                "Claim type",
                options=_ct_opts,
                index=_ct_idx,
                key="claim_type",
            )

        # ── Vehicle ───────────────────────────────────────────────
        st.markdown("##### 🚗 Vehicle")
        col_make, col_model, col_year = st.columns([1, 1.5, 0.75])
        with col_make:
            st.text_input(
                "Make",
                key="vehicle_make",
                placeholder="Toyota",
                value=st.session_state.get("vehicle_make", ""),
            )
        with col_model:
            st.text_input(
                "Model",
                key="vehicle_model",
                placeholder="Camry 2.5G",
                value=st.session_state.get("vehicle_model", ""),
            )
        with col_year:
            st.number_input(
                "Year",
                key="vehicle_year",
                min_value=1990,
                max_value=date.today().year + 1,
                step=1,
                format="%d",
                value=st.session_state.get("vehicle_year", date.today().year),
            )

        # ── Incident ───────────────────────────────────────────────
        st.markdown("##### 📅 Incident details")
        col_inc, col_sub = st.columns(2)
        with col_inc:
            st.date_input(
                "Incident date",
                key="incident_date",
                value=st.session_state.get("incident_date", date.today()),
            )
        with col_sub:
            st.date_input(
                "Claim submitted",
                key="claim_submitted_date",
                value=st.session_state.get("claim_submitted_date", date.today()),
            )
        st.text_input(
            "Incident location",
            key="incident_location",
            placeholder="e.g. Central World P4 parking lot, Bangkok",
            value=st.session_state.get("incident_location", ""),
        )

        # ── Claim description ──────────────────────────────────────
        st.markdown("##### 📝 Claim description")
        st.text_area(
            "claim_desc",
            key="claim_description",
            height=150,
            placeholder="Describe what happened — when, where, and how the incident occurred...",
            label_visibility="collapsed",
            value=st.session_state.get("claim_description", ""),
        )
        char_count = len(st.session_state.get("claim_description", ""))
        char_color = "#c62828" if char_count > 5000 else "#64748b"
        st.markdown(
            f'<p style="text-align:right;color:{char_color};font-size:0.78rem;margin-top:-10px">'
            f'{char_count:,} / 5,000</p>',
            unsafe_allow_html=True,
        )

        # ── Customer claim history ─────────────────────────────────
        st.markdown("##### 🕐 Customer claim history")
        _hist_has_label = st.radio(
            "Prior claims",
            options=["No claims", "Has prior claims"],
            key="hist_has_claims_label",
            horizontal=True,
        )
        _has_claims = _hist_has_label == "Has prior claims"
        if _has_claims:
            _hcol1, _hcol2 = st.columns(2)
            with _hcol1:
                st.number_input(
                    "Number of claims",
                    min_value=1,
                    max_value=99,
                    step=1,
                    key="hist_count_num",
                    format="%d",
                )
            with _hcol2:
                st.number_input(
                    "Lookback period (months)",
                    min_value=1,
                    max_value=120,
                    step=1,
                    key="hist_period_months",
                    format="%d",
                )
            st.caption("Claim type(s) in history:")
            _htype_cols = st.columns(2)
            for _i, _ht in enumerate(HISTORY_CLAIM_TYPES):
                with _htype_cols[_i % 2]:
                    st.checkbox(_ht, key=f"hist_type_{_i}")
            st.caption("Risk flags:")
            for _i, _hf in enumerate(HISTORY_FLAGS):
                st.checkbox(f"⚠️ {_hf}", key=f"hist_flag_{_i}")

        # ── Documents & Photos ─────────────────────────────────────
        st.markdown("##### 📄 Documents & Photos")
        for i, doc_name in enumerate(DOC_TYPES):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.checkbox(
                    doc_name,
                    key=f"doc_{i}",
                    value=st.session_state.get(f"doc_{i}", False),
                )
            with col_b:
                if st.session_state.get(f"doc_{i}", False):
                    st.markdown(
                        '<span style="color:#2e7d32;font-weight:600;font-size:0.82rem">'
                        "✓ Submitted</span>",
                        unsafe_allow_html=True,
                    )

        st.markdown("")
        col_photo_hd, col_photo_badge = st.columns([3, 1])
        with col_photo_hd:
            st.markdown("**📸 Photos of damage** _(optional)_")
        with col_photo_badge:
            if st.session_state.get("photo_analysis"):
                st.markdown(
                    '<span style="color:#2e7d32;font-weight:600;font-size:0.82rem">'
                    "✅ Analyzed</span>",
                    unsafe_allow_html=True,
                )

        uploaded_photos = st.file_uploader(
            "photos",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="damage_photos",
        )
        if uploaded_photos:
            ph_col1, ph_col2 = st.columns([3, 1])
            with ph_col1:
                analyze_clicked = st.button(
                    "🔍 Analyze damage photos",
                    use_container_width=True,
                    key="analyze_photos_btn",
                )
            with ph_col2:
                st.caption(f"{len(uploaded_photos)} photo(s)")
            if analyze_clicked:
                with st.spinner("Analyzing photos with Claude vision..."):
                    images = [(f.read(), f.type or "image/jpeg") for f in uploaded_photos]
                    st.session_state["photo_analysis"] = analyze_damage_photos(images)
            if st.session_state.get("photo_analysis"):
                st.info(f"**Photo analysis:** {st.session_state['photo_analysis']}")
                st.caption("ผลนี้จะถูกรวมเข้า triage context อัตโนมัติ")
        else:
            st.session_state.pop("photo_analysis", None)

        # ── Run triage button ──────────────────────────────────────
        st.markdown("")
        _photos_pending = (
            bool(st.session_state.get("damage_photos"))
            and not st.session_state.get("photo_analysis")
        )
        _btn_disabled = _is_running or _photos_pending
        _btn_label = "⏳ กำลังประมวลผล..." if _is_running else "▶  Run triage"

        run_clicked = st.button(
            _btn_label,
            type="primary",
            use_container_width=True,
            disabled=_btn_disabled,
        )
        if _is_running:
            st.caption("⏳ กำลังวิเคราะห์ claim กรุณารอสักครู่...")
        elif _photos_pending:
            st.caption("⚠️ กรุณากด Analyze photos ก่อน Run triage")

        # Placeholder for live Claude context + streaming panel (shown during run)
        ai_ctx_slot = st.empty()

        # Validate, build ClaimInput, then flip the running flag and rerun.
        # The rerun causes the button to re-render as disabled BEFORE the
        # agent call starts (Streamlit processes the new session state first).
        if run_clicked:
            if not st.session_state.get("claim_id") or not st.session_state.get("claim_description"):
                st.error("Claim ID and description are required.")
                st.stop()

            make = st.session_state.get("vehicle_make", "").strip()
            model_v = st.session_state.get("vehicle_model", "").strip()
            year_v = st.session_state.get("vehicle_year", "")
            vehicle_str = " ".join(p for p in [make, model_v, str(year_v)] if p)

            _ct_sel = st.session_state.get("claim_type", "")
            claim_type_val = _ct_sel if _ct_sel in CLAIM_TYPES else ""

            _hist_has = st.session_state.get("hist_has_claims_label", "No claims") == "Has prior claims"
            _hist_count_v = int(st.session_state.get("hist_count_num", 1)) if _hist_has else 0
            _hist_period_months = int(st.session_state.get("hist_period_months", 24)) if _hist_has else 24
            _prior_types = [
                HISTORY_CLAIM_TYPES[i]
                for i in range(len(HISTORY_CLAIM_TYPES))
                if st.session_state.get(f"hist_type_{i}", False)
            ]
            _hist_flags = [
                HISTORY_FLAGS[i]
                for i in range(len(HISTORY_FLAGS))
                if st.session_state.get(f"hist_flag_{i}", False)
            ]

            try:
                claim = ClaimInput(
                    claim_id=st.session_state["claim_id"],
                    policy_number=st.session_state.get("policy_number", ""),
                    claim_type=claim_type_val,
                    customer=st.session_state.get("customer", ""),
                    vehicle=vehicle_str,
                    incident_date=st.session_state["incident_date"],
                    incident_location=st.session_state.get("incident_location", ""),
                    claim_submitted_date=st.session_state["claim_submitted_date"],
                    claim_description=st.session_state["claim_description"],
                    documents_submitted=[
                        DOC_TYPES[i]
                        for i in range(len(DOC_TYPES))
                        if st.session_state.get(f"doc_{i}", False)
                    ] + (["Photos of damage"] if st.session_state.get("photo_analysis") else []),
                    prior_claims_count=_hist_count_v,
                    prior_claims_period=f"{_hist_period_months} months",
                    prior_claim_types=_prior_types,
                    history_flags=_hist_flags,
                )
            except ValidationError as e:
                for err in e.errors():
                    loc = " → ".join(str(x) for x in err["loc"])
                    st.error(f"**{loc}:** {err['msg']}")
                st.stop()
            except Exception as e:
                st.error(f"Unexpected error preparing claim: {e}")
                st.stop()

            st.session_state["_pending_claim"] = claim
            st.session_state["triage_running"] = True
            st.rerun()

    # ---- Right column ----
    with right:
        st.subheader("Triage recommendation")

        if _is_running and "_pending_claim" in st.session_state:
            # Agent execution pass: button is visually disabled; run the pipeline.
            claim = st.session_state.pop("_pending_claim")

            result_container = st.container()
            trace_slot = st.empty()
            trace_slot.html(_inline_trace_html([], running=True))
            completed: list = []

            def _on_step(step) -> None:
                completed.append(step)
                trace_slot.html(_inline_trace_html(completed, running=True))

            _chunks_ref: list = []

            def _on_prompt_ready(chunks, prompt) -> None:
                _chunks_ref.clear()
                _chunks_ref.extend(chunks)
                ai_ctx_slot.markdown(
                    _ai_ctx_html(chunks, "", False), unsafe_allow_html=True
                )

            def _on_token(json_buf: str) -> None:
                ai_ctx_slot.markdown(
                    _ai_ctx_html(_chunks_ref, json_buf, True), unsafe_allow_html=True
                )

            try:
                with st.spinner("Retrieving policy and calling Claude Sonnet..."):
                    agent = TriageAgent()
                    result = agent.run(
                        claim,
                        on_step=_on_step,
                        photo_description=st.session_state.get("photo_analysis", ""),
                        on_prompt_ready=_on_prompt_ready,
                        on_token=_on_token,
                    )
            except RuntimeError as exc:
                st.session_state["triage_running"] = False
                trace_slot.empty()
                st.error(f"**Pipeline error:** {exc}")
                st.info(
                    "ตรวจสอบ: Qdrant รันอยู่ไหม? (`docker ps`) "
                    "และ ANTHROPIC_API_KEY ถูกต้องไหม?"
                )
                st.stop()
            except Exception as exc:
                st.session_state["triage_running"] = False
                trace_slot.empty()
                st.error(f"**Unexpected error:** `{type(exc).__name__}: {exc}`")
                st.stop()

            # Store result, clear running flag, then rerun to re-enable button.
            st.session_state["last_result"] = result
            st.session_state["triage_running"] = False
            st.rerun()

        elif "last_result" in st.session_state:
            # Display pass: show stored result with the button re-enabled.
            last: TriageResult = st.session_state["last_result"]
            _render_result(last)
            _trace_slot = st.empty()
            _trace_slot.html(_inline_trace_html(last.trace, running=False))

        else:
            st.info(
                "Load a sample from the sidebar or fill in the form on the left, "
                "then click **▶ Run triage**."
            )

    # ── Full-width AI Governance panel ────────────────────────────────
    if "last_result" in st.session_state and not _is_running:
        _render_governance_panel(st.session_state["last_result"])


if __name__ == "__main__":
    main()
