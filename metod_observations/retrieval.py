from __future__ import annotations

import math
from typing import Any

from .schemas import RetrievedChunk


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def retrieve_top_k(
    query_embedding: list[float],
    embedded_rows: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    scored = []
    for row in embedded_rows:
        score = cosine_similarity(query_embedding, row.get("embedding", []))
        scored.append({**row, "score": score})
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


def compact_retrieved_evidence(rows: list[dict[str, Any]]) -> list[RetrievedChunk]:
    output = []
    for row in rows:
        chunk = row.get("chunk", {})
        output.append(
            RetrievedChunk(
                chunk_id=chunk.get("chunk_id", row.get("id", "")),
                source_file=chunk.get("source_file", row.get("source_file", "")),
                score=float(row.get("score", 0.0)),
                text=chunk.get("text", row.get("text", "")),
                metadata=chunk.get("metadata", row.get("metadata", {})),
            )
        )
    return output
