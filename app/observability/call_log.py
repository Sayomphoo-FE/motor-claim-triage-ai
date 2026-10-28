"""Call transcript log — one JSON per phone session, written incrementally.

Separate from the triage audit log (which lives under
`data/audit_logs/` and captures the policy-grounded reasoning for
one claim). The call log captures the *dialogue* between the AI
intake agent and the caller, plus every SupervisorAgent routing
decision. The two files are linked via `triage_session_id`.

File layout:
    data/call_logs/{session_id}.json

Design decisions:
- Written AFTER every state mutation (greeting, language set, user
  turn, triage done). The write is idempotent — the whole file is
  rewritten each time — so partial calls are also captured.
- UTF-8, `ensure_ascii=False`, so Thai text stays readable.
- Directory is gitignored (`data/call_logs/`) because transcripts
  may contain customer-ish content even with the PII mask.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv

if TYPE_CHECKING:
    from app.agents.conversation import ConversationState

load_dotenv()

CALL_LOG_DIR = Path(os.getenv("CALL_LOG_DIR", "./data/call_logs"))


def new_session_id() -> str:
    return (
        f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    )


def save_call_log(state: "ConversationState") -> Path:
    """Serialize the full call state to disk. Returns the written path."""
    CALL_LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = CALL_LOG_DIR / f"{state.session_id}.json"

    turns = [
        {"role": t.role, "text": t.text, "lang": t.lang} for t in state.turns
    ]
    supervisor_log = [asdict(d) for d in state.supervisor_log]
    collected = state.collected.model_dump() if state.collected else {}
    triage_audit: dict[str, Any] | None = None
    if state.triage is not None:
        triage_audit = state.triage.audit.to_dict()

    doc = {
        "session_id": state.session_id,
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "language": state.language,
        "turns": turns,
        "collected_info": collected,
        "supervisor_log": supervisor_log,
        "triage_session_id": (triage_audit or {}).get("session_id"),
        "triage_audit": triage_audit,
    }
    path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return path
