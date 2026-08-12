from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel

RERANK_INSTRUCTIONS = """
Eres un reordenador de evidencia para validacion metodologica de modelos.

Recibes la especificacion de una prueba y una lista numerada de fragmentos
candidatos. Para cada fragmento asigna una relevancia de 0 a 3:

3 = sustenta directamente el cumplimiento o incumplimiento de un control.
2 = aporta datos necesarios para evaluar el control, sin concluirlo.
1 = tema relacionado, sin datos utiles para esta prueba.
0 = irrelevante para esta prueba.

Juzga solo la utilidad del fragmento para esta prueba. No evalues todavia si
el control se cumple. Devuelve un puntaje por cada indice recibido.
""".strip()


class RerankedItem(BaseModel):
    index: int
    relevance: int


class RerankPayload(BaseModel):
    items: list[RerankedItem]


def _rerank_input(query_text: str, rows: list[dict[str, Any]], excerpt_chars: int) -> str:
    blocks = []
    for position, row in enumerate(rows):
        chunk = row.get("chunk", {})
        text = chunk.get("text", row.get("text", ""))
        source = chunk.get("source_file", row.get("source_file", ""))
        blocks.append(f"[{position}] archivo={source}\n{text[:excerpt_chars]}")
    return "\n\n".join(
        [
            "ESPECIFICACION DE LA PRUEBA:",
            query_text,
            "",
            "FRAGMENTOS CANDIDATOS:",
            *blocks,
        ]
    )


def rerank_rows(
    query_text: str,
    rows: list[dict[str, Any]],
    top_k: int,
    parse_fn: Callable[..., BaseModel],
    min_relevance: int = 1,
    excerpt_chars: int = 900,
) -> tuple[list[dict[str, Any]], bool]:
    """Reorder candidates with a listwise LLM judge.

    Returns the surviving rows and whether the rerank actually ran. The first
    stage optimises recall over a wide candidate window; this stage trades a
    cheap call for precision, and drops anything below min_relevance so an
    irrelevant chunk never reaches the generator just to fill top_k.

    Any failure degrades to the fused ranking rather than breaking the run:
    reranking is an improvement, not a dependency.
    """
    if len(rows) <= 1:
        return rows[:top_k], False

    try:
        parsed = parse_fn(
            _rerank_input(query_text, rows, excerpt_chars),
            instructions=RERANK_INSTRUCTIONS,
            text_format=RerankPayload,
        )
    except Exception:
        return rows[:top_k], False

    scores = {
        item.index: item.relevance
        for item in parsed.items
        if 0 <= item.index < len(rows)
    }
    if not scores:
        return rows[:top_k], False

    kept = [
        {**row, "rerank_relevance": scores.get(position, 0), "retrieval_score": row.get("score")}
        for position, row in enumerate(rows)
        if scores.get(position, 0) >= min_relevance
    ]
    kept.sort(
        key=lambda row: (row["rerank_relevance"], row.get("retrieval_score") or 0.0),
        reverse=True,
    )
    return kept[:top_k], True
