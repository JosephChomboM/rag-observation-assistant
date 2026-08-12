from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any

from .schemas import RetrievedChunk

BM25_K1 = 1.5
BM25_B = 0.75
RRF_K = 60

_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, strip accents, keep alphanumerics and underscores.

    Underscores survive because evidence carries identifiers like CODMES_12
    and target_default, which must stay as single lexical units.
    """
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = folded.encode("ascii", "ignore").decode("ascii")
    return _TOKEN_PATTERN.findall(folded)


def build_bm25_index(rows: list[dict[str, Any]], text_key: str = "text") -> dict[str, Any]:
    documents = [tokenize(row.get(text_key, "")) for row in rows]
    lengths = [len(doc) for doc in documents]
    document_frequency: Counter[str] = Counter()
    for doc in documents:
        document_frequency.update(set(doc))
    total = len(documents)
    return {
        "term_frequencies": [Counter(doc) for doc in documents],
        "lengths": lengths,
        "avg_length": (sum(lengths) / total) if total else 0.0,
        "document_frequency": document_frequency,
        "total_documents": total,
    }


def bm25_scores(query: str, index: dict[str, Any]) -> list[float]:
    total = index["total_documents"]
    if not total:
        return []
    avg_length = index["avg_length"] or 1.0
    document_frequency = index["document_frequency"]
    scores = [0.0] * total

    for term in tokenize(query):
        n_qi = document_frequency.get(term, 0)
        if not n_qi:
            continue
        idf = math.log(1 + (total - n_qi + 0.5) / (n_qi + 0.5))
        for position, frequencies in enumerate(index["term_frequencies"]):
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            length_norm = 1 - BM25_B + BM25_B * (index["lengths"][position] / avg_length)
            scores[position] += idf * (
                frequency * (BM25_K1 + 1) / (frequency + BM25_K1 * length_norm)
            )
    return scores


def retrieve_bm25(
    query: str,
    rows: list[dict[str, Any]],
    top_k: int,
    index: dict[str, Any] | None = None,
    text_key: str = "text",
) -> list[dict[str, Any]]:
    active_index = index or build_bm25_index(rows, text_key=text_key)
    scores = bm25_scores(query, active_index)
    scored = [
        {**row, "score": score}
        for row, score in zip(rows, scores)
        if score > 0
    ]
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    top_k: int,
    id_key: str = "id",
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """Fuse rankings by reciprocal rank instead of raw score.

    Dense cosine and BM25 live on incomparable scales, so any weighted sum of
    their scores needs per-corpus calibration that drifts. Rank position is
    scale free, which makes the fusion stable without tuning.
    """
    fused: dict[str, dict[str, Any]] = {}
    for ranked in ranked_lists:
        for rank, row in enumerate(ranked, start=1):
            row_id = row.get(id_key)
            if row_id is None:
                continue
            entry = fused.setdefault(row_id, {**row, "rrf_score": 0.0, "found_by": []})
            entry["rrf_score"] += 1.0 / (k + rank)
            entry["found_by"].append({"rank": rank, "score": row.get("score")})
    ordered = sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)
    return [{**row, "score": row["rrf_score"]} for row in ordered[:top_k]]


def retrieve_hybrid(
    query_text: str,
    query_embedding: list[float],
    rows: list[dict[str, Any]],
    top_k: int,
    candidate_multiplier: int = 3,
    bm25_index: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Dense + lexical retrieval fused by reciprocal rank.

    Each channel proposes candidate_multiplier * top_k candidates so the fusion
    has room to promote a chunk that only one channel ranked highly.
    """
    candidates = max(top_k * candidate_multiplier, top_k)
    dense = retrieve_top_k(query_embedding, rows, candidates)
    lexical = retrieve_bm25(query_text, rows, candidates, index=bm25_index)
    if not lexical:
        return dense[:top_k]
    return reciprocal_rank_fusion([dense, lexical], top_k)


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
