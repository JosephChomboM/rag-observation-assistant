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


def document_key(document: ParsedDocument, base_dir: str | Path | None = None) -> str:
    """Stable identity of a parsed document, independent of the file order.

    Uses the path relative to `base_dir` so the id survives moving the whole
    workspace, plus the document metadata that splits one file into several
    documents (PDF page, Excel sheet).
    """
    path = Path(document.source_file)
    relative = path.as_posix()
    if base_dir:
        try:
            relative = path.resolve().relative_to(Path(base_dir).resolve()).as_posix()
        except (ValueError, OSError):
            relative = path.as_posix()
    parts = [relative]
    parts.extend(f"{key}={document.metadata[key]}" for key in sorted(document.metadata))
    return "|".join(parts)


def document_slug(document: ParsedDocument, base_dir: str | Path | None = None) -> str:
    return hashlib.sha256(document_key(document, base_dir).encode("utf-8")).hexdigest()[:12]


def build_evidence_chunks(
    documents: list[ParsedDocument],
    metod_id: str,
    chunk_size: int = 1800,
    overlap: int = 200,
    common_metadata: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
) -> list[EvidenceChunk]:
    chunks: list[EvidenceChunk] = []
    shared_metadata = common_metadata or {}
    for document in documents:
        parts = split_text(document.text, chunk_size=chunk_size, overlap=overlap)
        source_name = Path(document.source_file).name
        slug = document_slug(document, base_dir)
        for part_index, part in enumerate(parts, start=1):
            chunk_id = f"{metod_id}_E{slug}_C{part_index:03d}"
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
