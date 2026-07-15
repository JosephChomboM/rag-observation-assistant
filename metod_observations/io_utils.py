from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable


def ensure_dir(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str | Path, payload: Any) -> None:
    ensure_dir(Path(path).parent)
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            clean = line.strip()
            if not clean:
                continue
            try:
                rows.append(json.loads(clean))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at {file_path}:{line_number}: {error}") from error
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_dir(Path(path).parent)
    with Path(path).open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def file_sha256(path: str | Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def list_files(folder_path: str | Path, extensions: set[str]) -> list[str]:
    base = Path(folder_path)
    if not base.exists():
        return []
    return sorted(
        str(path)
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in extensions
    )


def relative_to_folder(file_path: str | Path, folder_path: str | Path) -> str:
    try:
        return os.path.relpath(str(file_path), str(folder_path))
    except ValueError:
        return str(file_path)
