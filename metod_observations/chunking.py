from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .schemas import EvidenceChunk, ParsedDocument


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_text(text: str, chunk_size: int = 1800, overlap: int = 200) -> list[str]:
    clean = text.strip()
    if not clean:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap.")

    chunks = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        chunks.append(clean[start:end].strip())
        if end == len(clean):
            break
        start = end - overlap
    return [chunk for chunk in chunks if chunk]


def build_evidence_chunks(
    documents: list[ParsedDocument],
    metod_id: str,
    chunk_size: int = 1800,
    overlap: int = 200,
    common_metadata: dict[str, Any] | None = None,
) -> list[EvidenceChunk]:
    chunks: list[EvidenceChunk] = []
    shared_metadata = common_metadata or {}
    for doc_index, document in enumerate(documents, start=1):
        parts = split_text(document.text, chunk_size=chunk_size, overlap=overlap)
        source_name = Path(document.source_file).name
        for part_index, part in enumerate(parts, start=1):
            chunk_id = f"{metod_id}_E{doc_index:04d}_C{part_index:03d}"
            chunks.append(
                EvidenceChunk(
                    chunk_id=chunk_id,
                    source_file=source_name,
                    text=part,
                    metadata={
                        "metod_id": metod_id,
                        "source_path": document.source_file,
                        "content_type": document.content_type,
                        **document.metadata,
                        **shared_metadata,
                    },
                    text_sha256=text_sha256(part),
                )
            )
    return chunks
