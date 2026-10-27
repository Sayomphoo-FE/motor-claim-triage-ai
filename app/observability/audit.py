"""JSON audit log — one file per triage session.

Shape mirrors design doc §11.4 so a reviewer can map 1:1 from the
spec to the artifact. Each log is append-only once written: we never
rewrite a prior session.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

AUDIT_DIR = Path(os.getenv("AUDIT_LOG_DIR", "./data/audit_logs"))


def _hash(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


@dataclass
class AuditRecord:
    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    claim_id: str = ""
    customer_hash: str = ""
    model_versions: dict[str, str] = field(default_factory=dict)
    input_guard_triggers: list[str] = field(default_factory=list)
    output_guard_triggers: list[str] = field(default_factory=list)
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    triage_output: dict[str, Any] = field(default_factory=dict)
    cited_clauses: list[str] = field(default_factory=list)
    routing_decision: str = ""
    coverage_assessment: str = ""
    confidence_level: str = ""
    latency_ms: int = 0

    def set_customer(self, customer: str) -> None:
        self.customer_hash = _hash(customer)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_audit(record: AuditRecord, directory: Path = AUDIT_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record.session_id}.json"
    path.write_text(
        json.dumps(record.to_dict(), indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )
    return path
