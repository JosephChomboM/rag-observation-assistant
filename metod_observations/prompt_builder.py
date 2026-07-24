from __future__ import annotations

import json

from .schemas import PruebaSpec, RetrievedChunk


def build_generation_input(
    prueba: PruebaSpec,
    prueba_markdown: str,
    evidence: list[RetrievedChunk],
    global_context: list[RetrievedChunk],
    glossary_rows: list[dict],
    attached_files: list[dict] | None = None,
    attached_image_files: list[str] | None = None,
) -> str:
    evidence_payload = [
        {
            "chunk_id": item.chunk_id,
            "archivo": item.source_file,
            "score": round(item.score, 4),
            "extracto": item.text[:1800],
            "metadata": item.metadata,
        }
        for item in evidence
    ]
    global_context_payload = [
        {
            "chunk_id": item.chunk_id,
            "archivo": item.source_file,
            "score": round(item.score, 4),
            "extracto": item.text[:1800],
            "metadata": item.metadata,
        }
        for item in global_context
    ]

    glossary_payload = [
        {
            "term": row.get("term"),
            "definition": row.get("definition"),
            "aliases": row.get("aliases", []),
            "score": round(float(row.get("score", 0.0)), 4),
        }
        for row in glossary_rows
    ]
    control_ids = [control.control_id for control in prueba.controls]
    attached_files_text = attached_files or []
    attached_images_text = attached_image_files or []

    return f"""
Genera el resultado consolidado de validacion para la siguiente prueba METOD.

METADATA:
METOD: {prueba.metod_id}
PRUEBA_ID: {prueba.prueba_id}
NOMBRE_PRUEBA: {prueba.nombre_prueba}
CONTROLES_ESPERADOS: {json.dumps(control_ids, ensure_ascii=False)}

ESPECIFICACION DE LA PRUEBA:
{prueba_markdown}

GLOSARIO RELEVANTE:
{json.dumps(glossary_payload, ensure_ascii=False, indent=2)}


CONTEXTO GLOBAL COMPARTIDO PARA TODOS LOS METOD:
{json.dumps(global_context_payload, ensure_ascii=False, indent=2)}

ARCHIVOS ADJUNTOS AL MENSAJE:
{json.dumps(attached_files_text, ensure_ascii=False, indent=2)}

IMAGENES ADJUNTAS AL MENSAJE:
{json.dumps(attached_images_text, ensure_ascii=False, indent=2)}

EVIDENCIAS RECUPERADAS:
{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}
""".strip()
