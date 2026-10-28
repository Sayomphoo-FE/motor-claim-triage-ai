"""Retrieve relevant policy clauses from Qdrant."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.rag.ingest import (
    DEFAULT_COLLECTION,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_QDRANT_URL,
)
from app.schemas import RetrievedChunk

load_dotenv()
DEFAULT_TOP_K = int(os.getenv("TOP_K", "5"))


@lru_cache(maxsize=1)
def _embedder() -> TextEmbedding:
    return TextEmbedding(model_name=DEFAULT_EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    return QdrantClient(url=DEFAULT_QDRANT_URL, timeout=30, check_compatibility=False)


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    section_num: str | None = None,
    collection: str = DEFAULT_COLLECTION,
) -> list[RetrievedChunk]:
    """Semantic search over policy clauses.

    Args:
        query: free-text query (claim description or synthesized sub-query).
        top_k: number of chunks to return.
        section_num: optional metadata filter — one of "1", "2", "3", "4"
            to restrict to Covered Events / Exclusions / Required Documents /
            Routing Rules respectively.
        collection: Qdrant collection name.
    """
    vector = next(iter(_embedder().embed([query]))).tolist()
    qfilter: Filter | None = None
    if section_num:
        qfilter = Filter(
            must=[
                FieldCondition(key="section_num", match=MatchValue(value=section_num))
            ]
        )
    hits = _client().query_points(
        collection_name=collection,
        query=vector,
        limit=top_k,
        query_filter=qfilter,
        with_payload=True,
    ).points
    return [
        RetrievedChunk(
            clause_id=hit.payload["clause_id"],
            section=hit.payload["section"],
            text=hit.payload["text"],
            score=hit.score,
        )
        for hit in hits
    ]


def retrieve_multi(
    queries: list[str],
    top_k_per_query: int = 3,
    section_nums: list[str] | None = None,
) -> list[RetrievedChunk]:
    """Run multiple sub-queries and merge, keeping best score per clause."""
    sections = section_nums or [None] * len(queries)
    seen: dict[str, RetrievedChunk] = {}
    for q, sec in zip(queries, sections, strict=False):
        for hit in retrieve(q, top_k=top_k_per_query, section_num=sec):
            prev = seen.get(hit.clause_id)
            if prev is None or hit.score > prev.score:
                seen[hit.clause_id] = hit
    return sorted(seen.values(), key=lambda c: c.score, reverse=True)
