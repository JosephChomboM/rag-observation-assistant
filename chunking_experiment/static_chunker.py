def chunk_static_text(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int, str]]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append((start, end, chunk_text))
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def build_static_chunks(doc: dict, chunk_size: int, overlap: int) -> list[dict]:
    chunks = []
    for index, (start, end, text) in enumerate(chunk_static_text(doc["text"], chunk_size, overlap)):
        chunks.append(
            {
                "chunk_id": f"{doc['doc_id']}::static::{index:04d}",
                "strategy": "static",
                "source_file": doc["source_file"],
                "relative_path": doc["relative_path"],
                "text": text,
                "metadata": {
                    "char_start": start,
                    "char_end": end,
                    "chunk_index": index,
                    "chunk_size_chars": len(text),
                    "source_sha256": doc["source_sha256"],
                },
            }
        )
    return chunks

