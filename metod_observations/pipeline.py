from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

from .chunking import build_evidence_chunks
from .config import AppConfig, load_config, metod_paths
from .embeddings import EmbeddingStats, ModelClient, embed_rows_with_cache
from .excel_loader import load_pruebas_from_excel
from .io_utils import ensure_dir, read_json, read_jsonl, write_jsonl
from .knowledge_builder import (
    build_knowledge_for_all_metods,
    prueba_markdown_filename,
    prueba_profile_text,
)
from .observation_generator import generate_observation
from .outputs import save_run_outputs, utc_run_id
from .parsers import list_evidence_files, parse_evidence_files
from .prompt_builder import build_generation_prompt
from .retrieval import compact_retrieved_evidence, retrieve_top_k
from .schemas import ControlSpec, PruebaSpec


def build_admin_knowledge(
    excel_path: str,
    knowledge_base_dir: str | None = None,
    sheet_name: str | None = None,
    config: AppConfig | None = None,
) -> dict[str, dict]:
    active_config = config or load_config()
    output_dir = knowledge_base_dir or active_config.knowledge_base_dir
    pruebas_by_metod = load_pruebas_from_excel(excel_path, sheet_name=sheet_name)
    return build_knowledge_for_all_metods(pruebas_by_metod, output_dir)


def _control_from_dict(row: dict[str, Any]) -> ControlSpec:
    return ControlSpec(
        metod_id=row["metod_id"],
        prueba_id=row["prueba_id"],
        control_id=row["control_id"],
        nombre_prueba=row["nombre_prueba"],
        detalle=row.get("detalle", ""),
        prompt=row.get("prompt", ""),
        limites=row.get("limites", ""),
        criticidad=row.get("criticidad", ""),
        excepciones=row.get("excepciones", ""),
        row_number=int(row.get("row_number", 0)),
    )


def load_manifest_pruebas(manifest_path: str) -> list[PruebaSpec]:
    manifest = read_json(manifest_path)
    pruebas = []
    for prueba_row in manifest.get("pruebas", []):
        controls = [_control_from_dict(row) for row in prueba_row.get("controls", [])]
        pruebas.append(
            PruebaSpec(
                metod_id=prueba_row["metod_id"],
                prueba_id=prueba_row["prueba_id"],
                nombre_prueba=prueba_row["nombre_prueba"],
                controls=controls,
                source_file=prueba_row.get("source_file", manifest.get("source_file", "")),
            )
        )
    return pruebas


def read_prueba_markdown(knowledge_dir: str, prueba: PruebaSpec) -> str:
    path = Path(knowledge_dir) / "pruebas" / prueba_markdown_filename(prueba)
    if not path.exists():
        raise FileNotFoundError(f"Missing prueba markdown: {path}")
    return path.read_text(encoding="utf-8")


def _evidence_rows(chunks) -> list[dict[str, Any]]:
    return [
        {
            "id": chunk.chunk_id,
            "text": chunk.text,
            "source_file": chunk.source_file,
            "chunk": chunk.to_dict(),
        }
        for chunk in chunks
    ]


def build_evidence_index(
    metod_id: str,
    input_dir: str,
    index_path: str,
    embed_fn,
    embedding_model: str,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
    rebuild: bool = False,
    source_scope: str = "metod",
    summary_prefix: str = "evidence",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    files = list_evidence_files(input_dir)
    documents = parse_evidence_files(files)
    chunks = build_evidence_chunks(
        documents,
        metod_id,
        chunk_size=chunk_size,
        overlap=chunk_overlap,
        common_metadata={"source_scope": source_scope},
    )
    existing = [] if rebuild else read_jsonl(index_path)
    rows, stats = embed_rows_with_cache(
        _evidence_rows(chunks),
        existing,
        embed_fn=embed_fn,
        embedding_model=embedding_model,
    )
    write_jsonl(index_path, rows)
    parsed_documents_key = (
        "parsed_documents"
        if summary_prefix == "evidence"
        else f"{summary_prefix}_parsed_documents"
    )
    return rows, {
        f"{summary_prefix}_files": len(files),
        parsed_documents_key: len(documents),
        f"{summary_prefix}_chunks": len(chunks),
        f"{summary_prefix}_embeddings_created": stats.created,
        f"{summary_prefix}_embeddings_reused": stats.reused,
    }


def _glossary_rows(glossary_path: str) -> list[dict[str, Any]]:
    if not os.path.exists(glossary_path):
        return []
    data = read_json(glossary_path)
    rows = []
    for item in data:
        term = str(item.get("term", "")).strip()
        aliases = item.get("aliases", []) or []
        definition = str(item.get("definition", "")).strip()
        if not term or not definition:
            continue
        rows.append(
            {
                "id": f"glossary:{term}",
                "term": term,
                "definition": definition,
                "aliases": aliases,
                "text": "\n".join(
                    [
                        f"Termino: {term}",
                        f"Aliases: {', '.join(str(alias) for alias in aliases)}",
                        f"Definicion: {definition}",
                    ]
                ),
            }
        )
    return rows


def build_glossary_index(
    glossary_path: str,
    index_path: str,
    embed_fn,
    embedding_model: str,
    rebuild: bool = False,
) -> tuple[list[dict[str, Any]], EmbeddingStats]:
    rows = _glossary_rows(glossary_path)
    existing = [] if rebuild else read_jsonl(index_path)
    embedded, stats = embed_rows_with_cache(
        rows,
        existing,
        embed_fn=embed_fn,
        embedding_model=embedding_model,
    )
    write_jsonl(index_path, embedded)
    return embedded, stats


def build_profile_index(
    pruebas: list[PruebaSpec],
    index_path: str,
    embed_fn,
    embedding_model: str,
    rebuild: bool = False,
) -> tuple[list[dict[str, Any]], EmbeddingStats]:
    rows = [
        {
            "id": prueba.prueba_id,
            "prueba_id": prueba.prueba_id,
            "nombre_prueba": prueba.nombre_prueba,
            "text": prueba_profile_text(prueba),
        }
        for prueba in pruebas
    ]
    existing = [] if rebuild else read_jsonl(index_path)
    embedded, stats = embed_rows_with_cache(
        rows,
        existing,
        embed_fn=embed_fn,
        embedding_model=embedding_model,
    )
    write_jsonl(index_path, embedded)
    return embedded, stats


def _select_glossary_rows(
    query_text: str,
    query_embedding: list[float],
    glossary_rows: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    query_lower = query_text.lower()
    exact = []
    for row in glossary_rows:
        terms = [row.get("term", ""), *(row.get("aliases") or [])]
        if any(str(term).lower() in query_lower for term in terms if term):
            exact.append({**row, "score": 1.0})

    exact_ids = {row["id"] for row in exact}
    semantic = [
        row
        for row in retrieve_top_k(query_embedding, glossary_rows, top_k)
        if row.get("id") not in exact_ids
    ]
    return (exact + semantic)[:top_k]




def _image_to_data_url(path: str) -> str:
    mime_type = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _prompt_image_attachments(
    selected_evidence_rows: list[dict[str, Any]],
    max_images: int,
) -> tuple[list[str], list[str]]:
    if max_images <= 0:
        return [], []

    image_data_urls: list[str] = []
    image_files: list[str] = []
    seen_paths: set[str] = set()
    for row in selected_evidence_rows:
        chunk = row.get("chunk", {})
        metadata = chunk.get("metadata", {})
        if metadata.get("content_type") != "image":
            continue
        source_path = metadata.get("source_path")
        if not source_path or source_path in seen_paths or not os.path.exists(source_path):
            continue
        image_data_urls.append(_image_to_data_url(source_path))
        image_files.append(chunk.get("source_file") or os.path.basename(source_path))
        seen_paths.add(source_path)
        if len(image_data_urls) >= max_images:
            break
    return image_data_urls, image_files

def run_observation_pipeline(
    metod_id: str,
    config: AppConfig | None = None,
    rebuild_evidence_index: bool = False,
    run_mode: str = "full",
    prueba_id: str | None = None,
    model_client: ModelClient | None = None,
) -> dict[str, Any]:
    active_config = config or load_config()
    clean_metod = metod_id.strip().upper()
    paths = metod_paths(active_config, clean_metod)
    ensure_dir(paths["input_dir"])
    ensure_dir(paths["global_input_dir"])
    ensure_dir(paths["index_dir"])
    ensure_dir(paths["global_index_dir"])
    ensure_dir(active_config.outputs_base_dir)

    if not os.path.exists(paths["manifest_path"]):
        raise FileNotFoundError(
            f"Missing manifest for {clean_metod}: {paths['manifest_path']}. "
            "Run the admin knowledge build first."
        )

    client = model_client or ModelClient(
        embedding_provider=active_config.embedding_provider,
        chat_provider=active_config.chat_provider,
        embedding_deployment=active_config.embedding_deployment,
        chat_deployment=active_config.chat_deployment,
    )

    pruebas = load_manifest_pruebas(paths["manifest_path"])
    if run_mode == "prueba_unica":
        if not prueba_id:
            raise ValueError("prueba_id is required when run_mode='prueba_unica'.")
        pruebas = [prueba for prueba in pruebas if prueba.prueba_id == prueba_id]
        if not pruebas:
            raise ValueError(f"prueba_id '{prueba_id}' was not found for {clean_metod}.")

    evidence_rows, evidence_summary = build_evidence_index(
        clean_metod,
        paths["input_dir"],
        paths["evidence_index_path"],
        client.embed_text,
        active_config.embedding_deployment,
        chunk_size=active_config.chunk_size,
        chunk_overlap=active_config.chunk_overlap,
        rebuild=rebuild_evidence_index,
    )
    global_context_rows, global_context_summary = build_evidence_index(
        "GLOBAL",
        paths["global_input_dir"],
        paths["global_context_index_path"],
        client.embed_text,
        active_config.embedding_deployment,
        chunk_size=active_config.chunk_size,
        chunk_overlap=active_config.chunk_overlap,
        rebuild=rebuild_evidence_index,
        source_scope="global",
        summary_prefix="global_context",
    )
    glossary_path = os.path.join(active_config.knowledge_base_dir, "_shared", "glossary_data.json")
    glossary_rows, glossary_stats = build_glossary_index(
        glossary_path,
        paths["glossary_index_path"],
        client.embed_text,
        active_config.embedding_deployment,
        rebuild=False,
    )
    _, profile_stats = build_profile_index(
        pruebas,
        paths["profile_index_path"],
        client.embed_text,
        active_config.embedding_deployment,
        rebuild=False,
    )

    observations = []
    retrieval_debug_rows = []
    for prueba in pruebas:
        query_text = prueba_profile_text(prueba)
        query_embedding = client.embed_text(query_text)
        selected_evidence_rows = retrieve_top_k(
            query_embedding,
            evidence_rows,
            active_config.top_k_evidence,
        )
        retrieved_evidence = compact_retrieved_evidence(selected_evidence_rows)
        selected_global_context_rows = retrieve_top_k(
            query_embedding,
            global_context_rows,
            active_config.top_k_global_context,
        )
        retrieved_global_context = compact_retrieved_evidence(selected_global_context_rows)
        selected_glossary_rows = _select_glossary_rows(
            query_text,
            query_embedding,
            glossary_rows,
            active_config.top_k_glossary,
        )
        image_data_urls, attached_image_files = _prompt_image_attachments(
            selected_evidence_rows,
            active_config.max_prompt_images,
        )
        prueba_markdown = read_prueba_markdown(paths["knowledge_dir"], prueba)
        prompt = build_generation_prompt(
            prueba,
            prueba_markdown,
            retrieved_evidence,
            retrieved_global_context,
            selected_glossary_rows,
            attached_image_files=attached_image_files,
        )
        observations.append(
            generate_observation(
                prompt,
                prueba,
                client.chat_json,
                image_data_urls=image_data_urls,
            )
        )

        for row in selected_evidence_rows:
            retrieval_debug_rows.append(
                {
                    "metod_id": clean_metod,
                    "prueba_id": prueba.prueba_id,
                    "source_type": "evidence",
                    "score": row.get("score"),
                    "chunk_id": row.get("id"),
                    "source_file": row.get("source_file"),
                    "sent_as_prompt_image": row.get("source_file") in attached_image_files,
                }
            )
        for row in selected_glossary_rows:
            retrieval_debug_rows.append(
                {
                    "metod_id": clean_metod,
                    "prueba_id": prueba.prueba_id,
                    "source_type": "glossary",
                    "score": row.get("score"),
                    "term": row.get("term"),
                }
            )
        for row in selected_global_context_rows:
            retrieval_debug_rows.append(
                {
                    "metod_id": clean_metod,
                    "prueba_id": prueba.prueba_id,
                    "source_type": "global_context",
                    "score": row.get("score"),
                    "chunk_id": row.get("id"),
                    "source_file": row.get("source_file"),
                    "source_scope": "global",
                }
            )

    run_id = utc_run_id(clean_metod)
    usage_summary = {
        **evidence_summary,
        **global_context_summary,
        "pruebas_processed": len(pruebas),
        "controls_processed": sum(len(prueba.controls) for prueba in pruebas),
        "llm_generation_requests": len(pruebas),
        "top_k_global_context_per_prueba": active_config.top_k_global_context,
        "max_prompt_images_per_prueba": active_config.max_prompt_images,
        "glossary_embeddings_created": glossary_stats.created,
        "glossary_embeddings_reused": glossary_stats.reused,
        "profile_embeddings_created": profile_stats.created,
        "profile_embeddings_reused": profile_stats.reused,
    }
    output_paths = save_run_outputs(
        active_config.outputs_base_dir,
        clean_metod,
        run_id,
        observations,
        retrieval_debug_rows,
        usage_summary,
    )
    return {
        "metod_id": clean_metod,
        "run_id": run_id,
        "output_paths": output_paths,
        "usage_summary": usage_summary,
        "observations": [observation.to_dict() for observation in observations],
    }


