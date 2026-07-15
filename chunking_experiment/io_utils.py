import hashlib
import json
from pathlib import Path
from typing import Iterable


def normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_knowledge_files(base_dir: Path, extensions: set[str]) -> Iterable[Path]:
    for path in sorted(base_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def read_text(path: Path) -> str:
    return normalize_text(path.read_text(encoding="utf-8", errors="replace"))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

