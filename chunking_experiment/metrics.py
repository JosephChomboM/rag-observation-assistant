from collections import Counter


def summarize_chunks(chunks: list[dict]) -> dict:
    sizes = [len(chunk["text"]) for chunk in chunks]
    source_counts = Counter(chunk["relative_path"] for chunk in chunks)

    heading_chunks = sum(1 for chunk in chunks if chunk.get("metadata", {}).get("heading_path"))

    return {
        "chunk_count": len(chunks),
        "source_file_count": len(source_counts),
        "avg_chars": round(sum(sizes) / len(sizes), 2) if sizes else 0,
        "min_chars": min(sizes) if sizes else 0,
        "max_chars": max(sizes) if sizes else 0,
        "chunks_by_source": dict(source_counts),
        "chunks_with_heading_metadata": heading_chunks,
    }


def compare_summaries(static_summary: dict, dynamic_summary: dict) -> dict:
    return {
        "static": static_summary,
        "dynamic": dynamic_summary,
        "decision_hints": {
            "prefer_dynamic_when": [
                "more chunks preserve heading metadata",
                "chunks map cleanly to acceptance, boundaries, criticalities or exceptions",
                "average chunk size remains reasonable",
            ],
            "prefer_static_when": [
                "markdown structure is poor",
                "dynamic creates too many tiny chunks",
                "retrieval tests later show better recall with fixed windows",
            ],
        },
    }

