import re

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def is_heading_only(section_text: str) -> bool:
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    return len(lines) == 1 and bool(HEADING_PATTERN.match(lines[0]))


def split_markdown_sections(text: str) -> list[dict]:
    matches = list(HEADING_PATTERN.finditer(text))
    if not matches:
        return [{"heading_path": [], "start": 0, "end": len(text), "text": text.strip()}]

    sections = []
    heading_stack = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        heading_stack = [heading for heading in heading_stack if heading["level"] < level]
        heading_stack.append({"level": level, "title": title})

        section_text = text[start:end].strip()
        if section_text and not is_heading_only(section_text):
            sections.append(
                {
                    "heading_path": [heading["title"] for heading in heading_stack],
                    "start": start,
                    "end": end,
                    "text": section_text,
                }
            )
    return sections


def split_large_section(section: dict, max_chars: int) -> list[dict]:
    if len(section["text"]) <= max_chars:
        return [section]

    blocks = [block.strip() for block in section["text"].split("\n\n") if block.strip()]
    result = []
    buffer = []
    part = 0

    for block in blocks:
        candidate = "\n\n".join(buffer + [block])
        if len(candidate) > max_chars and buffer:
            result.append({**section, "text": "\n\n".join(buffer), "part": part})
            buffer = [block]
            part += 1
        else:
            buffer.append(block)

    if buffer:
        result.append({**section, "text": "\n\n".join(buffer), "part": part})
    return result


def build_dynamic_chunks(doc: dict, max_chars: int, min_chars: int = 0) -> list[dict]:
    chunks = []
    expanded = []

    for section in split_markdown_sections(doc["text"]):
        expanded.extend(split_large_section(section, max_chars))

    for index, section in enumerate(expanded):
        if len(section["text"]) < min_chars and is_heading_only(section["text"]):
            continue

        chunks.append(
            {
                "chunk_id": f"{doc['doc_id']}::dynamic::{index:04d}",
                "strategy": "dynamic",
                "source_file": doc["source_file"],
                "relative_path": doc["relative_path"],
                "text": section["text"],
                "metadata": {
                    "heading_path": section["heading_path"],
                    "char_start": section["start"],
                    "char_end": section["end"],
                    "chunk_index": index,
                    "section_part": section.get("part", 0),
                    "chunk_size_chars": len(section["text"]),
                    "source_sha256": doc["source_sha256"],
                },
            }
        )
    return chunks
