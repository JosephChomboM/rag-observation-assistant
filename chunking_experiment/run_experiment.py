from pathlib import Path

from config import (
    DYNAMIC_MAX_CHARS,
    DYNAMIC_MIN_CHARS,
    KNOWLEDGE_DIR,
    OUTPUT_DIR,
    STATIC_CHUNK_CHARS,
    STATIC_OVERLAP_CHARS,
    SUPPORTED_EXTENSIONS,
)
from dynamic_chunker import build_dynamic_chunks
from io_utils import file_sha256, iter_knowledge_files, read_text, write_json, write_jsonl
from metrics import compare_summaries, summarize_chunks
from static_chunker import build_static_chunks


def load_documents(base_dir: Path) -> list[dict]:
    docs = []
    for path in iter_knowledge_files(base_dir, SUPPORTED_EXTENSIONS):
        relative_path = path.relative_to(base_dir).as_posix()
        docs.append(
            {
                "doc_id": f"knowledge::{relative_path.replace('/', '__')}",
                "source_file": path.name,
                "relative_path": relative_path,
                "source_sha256": file_sha256(path),
                "text": read_text(path),
            }
        )
    return docs


def main() -> None:
    docs = load_documents(KNOWLEDGE_DIR)

    static_chunks = []
    dynamic_chunks = []

    for doc in docs:
        static_chunks.extend(build_static_chunks(doc, STATIC_CHUNK_CHARS, STATIC_OVERLAP_CHARS))
        dynamic_chunks.extend(build_dynamic_chunks(doc, DYNAMIC_MAX_CHARS, DYNAMIC_MIN_CHARS))

    static_summary = summarize_chunks(static_chunks)
    dynamic_summary = summarize_chunks(dynamic_chunks)
    comparison = compare_summaries(static_summary, dynamic_summary)

    write_jsonl(OUTPUT_DIR / "static" / "chunks_static.jsonl", static_chunks)
    write_json(OUTPUT_DIR / "static" / "metrics_static.json", static_summary)

    write_jsonl(OUTPUT_DIR / "dynamic" / "chunks_dynamic.jsonl", dynamic_chunks)
    write_json(OUTPUT_DIR / "dynamic" / "metrics_dynamic.json", dynamic_summary)

    write_json(OUTPUT_DIR / "comparison_summary.json", comparison)

    print("Documents:", len(docs))
    print("Static chunks:", len(static_chunks))
    print("Dynamic chunks:", len(dynamic_chunks))
    print("Output:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
