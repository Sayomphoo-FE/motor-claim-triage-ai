"""Policy ingestion: parse markdown by section/clause, embed, upsert to Qdrant.

Design choices for this prototype:
- Chunk granularity = one Clause (level ### heading). Policy rules are
  terse, so one clause per chunk preserves the exact text we want
  the triage agent to cite, without diluting embeddings.
- Metadata attached: {section, clause_id, section_num, source}
  → enables metadata filtering (e.g. search only in exclusions).
- Embedding model: BAAI/bge-m3 via FastEmbed (CPU, no GPU needed).
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

load_dotenv()

# intfloat/multilingual-e5-large (1024-dim, ~2.24 GB) chosen so that
# Thai customer queries embed in the same vector space as the English
# policy. The prototype originally used BAAI/bge-small-en-v1.5
# (384-dim, 33 MB) which only handles English — set EMBEDDING_MODEL
# in .env to fall back if a smaller model is required.
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
DEFAULT_COLLECTION = os.getenv("QDRANT_COLLECTION", "motor_policy")
DEFAULT_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

SECTION_RE = re.compile(r"^## Section (\d+) — (.+)$")
CLAUSE_RE = re.compile(r"^### Clause (\d+\.\d+) — (.+)$")


@dataclass
class PolicyChunk:
    clause_id: str
    section_num: str
    section: str
    title: str
    text: str
    source: str

    def payload(self) -> dict[str, str]:
        return {
            "clause_id": self.clause_id,
            "section_num": self.section_num,
            "section": self.section,
            "title": self.title,
            "text": self.text,
            "source": self.source,
        }


def parse_policy(markdown_path: Path) -> list[PolicyChunk]:
    """Split policy markdown into clause-level chunks."""
    chunks: list[PolicyChunk] = []
    current_section_num = ""
    current_section = ""
    current_clause_id = ""
    current_title = ""
    buffer: list[str] = []
    source = markdown_path.name

    def flush() -> None:
        if current_clause_id and buffer:
            body = "\n".join(buffer).strip()
            if body:
                chunks.append(
                    PolicyChunk(
                        clause_id=current_clause_id,
                        section_num=current_section_num,
                        section=current_section,
                        title=current_title,
                        text=f"[Clause {current_clause_id} — {current_title}]\n{body}",
                        source=source,
                    )
                )

    for raw in markdown_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if m := SECTION_RE.match(line):
            flush()
            buffer = []
            current_section_num, current_section = m.group(1), m.group(2)
            current_clause_id = ""
            current_title = ""
            continue
        if m := CLAUSE_RE.match(line):
            flush()
            buffer = []
            current_clause_id, current_title = m.group(1), m.group(2)
            continue
        if current_clause_id and line.strip():
            buffer.append(line)
    flush()
    return chunks


def _ensure_collection(client: QdrantClient, name: str, dim: int) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        client.delete_collection(name)
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )


def ingest(
    policy_path: Path,
    collection: str = DEFAULT_COLLECTION,
    qdrant_url: str = DEFAULT_QDRANT_URL,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> int:
    """Ingest a policy markdown file into Qdrant. Returns the chunk count."""
    chunks = parse_policy(policy_path)
    if not chunks:
        raise RuntimeError(f"No clauses parsed from {policy_path}")

    embedder = TextEmbedding(model_name=embedding_model)
    # e5 models expect "passage: " prefix on documents (and "query: " on
    # queries, applied in the retriever). Applied unconditionally — other
    # models tolerate the extra token with negligible impact.
    use_e5_prefix = "e5" in embedding_model.lower()
    texts = [f"passage: {c.text}" if use_e5_prefix else c.text for c in chunks]
    vectors = list(embedder.embed(texts))

    client = QdrantClient(url=qdrant_url, timeout=30)
    _ensure_collection(client, collection, dim=len(vectors[0]))

    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{chunk.source}:{chunk.clause_id}")),
            vector=vec.tolist(),
            payload=chunk.payload(),
        )
        for chunk, vec in zip(chunks, vectors, strict=True)
    ]
    client.upsert(collection_name=collection, points=points, wait=True)
    return len(points)
