from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

from .chunking import build_evidence_chunks
from .config import AppConfig, load_config, metod_paths, resolve_run_details_dir
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
from .prompt_builder import build_generation_input
from .reranking import rerank_rows
from .retrieval import (
    build_bm25_index,
    compact_retrieved_evidence,
    retrieve_hybrid,
    retrieve_top_k,
)
from .schemas import ControlSpec, PruebaSpec


MAX_FILE_INPUT_BYTES = 50_000_000


def build_admin_knowledge(
    excel_path: str,
    knowledge_base_dir: str | None = None,
    sheet_name: str | None = None,
    config: AppConfig | None = None,
) -> dict[str, dict]:
    result = build_admin_assets(
        excel_path=excel_path,
        knowledge_base_dir=knowledge_base_dir,
        sheet_name=sheet_name,
        config=config,
    )
    return result["manifests"]


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
        base_dir=input_dir,
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

def build_admin_assets(
    excel_path: str,
    knowledge_base_dir: str | None = None,
    sheet_name: str | None = None,
    rebuild_embeddings: bool = False,
    config: AppConfig | None = None,
    model_client: ModelClient | None = None,
) -> dict[str, Any]:
    active_config = config or load_config()
    output_dir = knowledge_base_dir or active_config.knowledge_base_dir
    pruebas_by_metod = load_pruebas_from_excel(excel_path, sheet_name=sheet_name)
    manifests = build_knowledge_for_all_metods(pruebas_by_metod, output_dir)

    client = model_client or ModelClient(
        embedding_deployment=active_config.embedding_deployment,
        chat_deployment=active_config.chat_deployment,
        reasoning_effort=active_config.reasoning_effort,
    )

    shared_index_dir = os.path.join(output_dir, "_indexes", "_shared")
    ensure_dir(shared_index_dir)
    glossary_rows, glossary_stats = build_glossary_index(
        os.path.join(output_dir, "_shared", "glossary_data.json"),
        os.path.join(shared_index_dir, "glossary_embeddings.jsonl"),
        client.embed_text,
        active_config.embedding_deployment,
        rebuild=rebuild_embeddings,
    )

    metod_summaries: dict[str, dict[str, int]] = {}
    for metod_id, pruebas in pruebas_by_metod.items():
        metod_index_dir = os.path.join(output_dir, "_indexes", metod_id)
        ensure_dir(metod_index_dir)
        profile_rows, profile_stats = build_profile_index(
            pruebas,
            os.path.join(metod_index_dir, "prueba_profile_embeddings.jsonl"),
            client.embed_text,
            active_config.embedding_deployment,
            rebuild=rebuild_embeddings,
        )
        metod_summaries[metod_id] = {
            "profiles": len(profile_rows),
            "embeddings_created": profile_stats.created,
            "embeddings_reused": profile_stats.reused,
        }

    return {
        "manifests": manifests,
        "embedding_summary": {
            "embedding_deployment": active_config.embedding_deployment,
            "glossary_terms": len(glossary_rows),
            "glossary_embeddings_created": glossary_stats.created,
            "glossary_embeddings_reused": glossary_stats.reused,
            "metods": metod_summaries,
        },
    }


def _read_admin_index(
    index_path: str,
    label: str,
    expected_embedding_model: str,
) -> list[dict[str, Any]]:
    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"Missing admin {label} index: {index_path}. "
            "Run 01_admin_build_knowledge.py first."
        )

    rows = read_jsonl(index_path)
    unexpected_models = {
        row.get("embedding_model")
        for row in rows
        if row.get("embedding_model") != expected_embedding_model
    }
    if unexpected_models:
        raise ValueError(
            f"Admin {label} index uses {sorted(unexpected_models)} but runtime uses "
            f"'{expected_embedding_model}'. Rebuild it with the admin notebook."
        )
    return rows



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




def _retrieve_context(
    query_text: str,
    query_embedding: list[float],
    rows: list[dict[str, Any]],
    top_k: int,
    config: AppConfig,
    bm25_index: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if config.retrieval_mode == "hybrid":
        return retrieve_hybrid(
            query_text,
            query_embedding,
            rows,
            top_k,
            candidate_multiplier=config.candidate_multiplier,
            bm25_index=bm25_index,
        )
    return retrieve_top_k(query_embedding, rows, top_k)


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


def _file_candidates(
    rows: list[dict[str, Any]],
    scope: str,
) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen_paths: set[str] = set()
    for row in rows:
        metadata = row.get("chunk", {}).get("metadata", {})
        source_path = metadata.get("source_path")
        if (
            metadata.get("content_type") == "image"
            or not source_path
            or source_path in seen_paths
            or not os.path.exists(source_path)
        ):
            continue
        candidates.append((source_path, scope))
        seen_paths.add(source_path)
    return candidates


def _interleave_file_candidates(
    evidence_rows: list[dict[str, Any]],
    global_rows: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    evidence = _file_candidates(evidence_rows, "evidence")
    global_context = _file_candidates(global_rows, "global")
    ordered: list[tuple[str, str]] = []
    for index in range(max(len(evidence), len(global_context))):
        if index < len(evidence):
            ordered.append(evidence[index])
        if index < len(global_context):
            ordered.append(global_context[index])
    return ordered


def _prompt_file_attachments(
    selected_evidence_rows: list[dict[str, Any]],
    selected_global_rows: list[dict[str, Any]],
    client: ModelClient,
    uploaded_files: dict[str, tuple[str, str]],
    max_files: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], set[str], list[str]]:
    if max_files <= 0:
        return [], [], set(), []

    file_inputs: list[dict[str, Any]] = []
    descriptors: list[dict[str, str]] = []
    attached_paths: set[str] = set()
    skipped_files: list[str] = []
    total_bytes = 0

    for source_path, scope in _interleave_file_candidates(
        selected_evidence_rows,
        selected_global_rows,
    ):
        if len(file_inputs) >= max_files:
            break
        content_bytes = os.path.getsize(source_path)
        if content_bytes >= MAX_FILE_INPUT_BYTES:
            skipped_files.append(source_path)
            continue
        if total_bytes + content_bytes >= MAX_FILE_INPUT_BYTES:
            skipped_files.append(source_path)
            continue

        if source_path not in uploaded_files:
            uploaded_files[source_path] = client.upload_input_file(source_path)
        file_id, uploaded_name = uploaded_files[source_path]

        file_input: dict[str, Any] = {
            "type": "input_file",
            "file_id": file_id,
        }
        if Path(source_path).suffix.lower() == ".pdf":
            file_input["detail"] = "high"

        descriptor = {
            "archivo": Path(source_path).name,
            "scope": scope,
            "input_file": uploaded_name,
        }

        file_inputs.append(file_input)
        descriptors.append(descriptor)
        attached_paths.add(source_path)
        total_bytes += content_bytes

    return file_inputs, descriptors, attached_paths, skipped_files


def prepare_user_workspace(
    metod_id: str,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    """Create the user folder tree and report what is still missing.

    Run this before `run_observation_pipeline`: it creates the empty folders so
    the user can drop the evidence in, and reports whether the METOD folder
    already has supported files. It never calls the model.
    """
    active_config = config or load_config()
    if not all(
        [
            active_config.inputs_base_dir,
            active_config.indexes_base_dir,
            active_config.outputs_base_dir,
        ]
    ):
        raise ValueError(
            "Missing user workspace paths. Set user_base_dir in "
            "gestor_observaciones/02_generate_observations_by_prueba.py."
        )

    clean_metod = metod_id.strip().upper()
    paths = metod_paths(active_config, clean_metod)
    run_details_dir = resolve_run_details_dir(active_config)
    for folder in (
        paths["input_dir"],
        paths["global_input_dir"],
        paths["index_dir"],
        paths["global_index_dir"],
        active_config.outputs_base_dir,
        run_details_dir,
    ):
        ensure_dir(folder)

    evidence_files = list_evidence_files(paths["input_dir"])
    global_files = list_evidence_files(paths["global_input_dir"])
    missing_knowledge = [
        path
        for path in (
            paths["manifest_path"],
            paths["profile_index_path"],
            paths["glossary_index_path"],
        )
        if not os.path.exists(path)
    ]

    return {
        "metod_id": clean_metod,
        "input_dir": paths["input_dir"],
        "global_input_dir": paths["global_input_dir"],
        "index_dir": paths["index_dir"],
        "outputs_dir": active_config.outputs_base_dir,
        "run_details_dir": run_details_dir,
        "evidence_files": evidence_files,
        "global_context_files": global_files,
        "missing_admin_knowledge": missing_knowledge,
        "ready": bool(evidence_files) and not missing_knowledge,
    }


def run_observation_pipeline(
    metod_id: str,
    config: AppConfig | None = None,
    rebuild_evidence_index: bool = False,
    model_client: ModelClient | None = None,
) -> dict[str, Any]:
    active_config = config or load_config()
    if not all(
        [
            active_config.inputs_base_dir,
            active_config.indexes_base_dir,
            active_config.outputs_base_dir,
        ]
    ):
        raise ValueError(
            "Missing user workspace paths. Set user_base_dir in "
            "gestor_observaciones/02_generate_observations_by_prueba.py."
        )
    clean_metod = metod_id.strip().upper()
    paths = metod_paths(active_config, clean_metod)
    ensure_dir(paths["input_dir"])
    ensure_dir(paths["global_input_dir"])
    ensure_dir(paths["index_dir"])
    ensure_dir(paths["global_index_dir"])
    ensure_dir(active_config.outputs_base_dir)
    ensure_dir(resolve_run_details_dir(active_config))

    if not os.path.exists(paths["manifest_path"]):
        raise FileNotFoundError(
            f"Missing manifest for {clean_metod}: {paths['manifest_path']}. "
            "Run the admin knowledge build first."
        )

    client = model_client or ModelClient(
        embedding_deployment=active_config.embedding_deployment,
        chat_deployment=active_config.chat_deployment,
        reasoning_effort=active_config.reasoning_effort,
    )

    pruebas = load_manifest_pruebas(paths["manifest_path"])
    glossary_rows = _read_admin_index(
        paths["glossary_index_path"],
        "glossary",
        active_config.embedding_deployment,
    )
    profile_rows = _read_admin_index(
        paths["profile_index_path"],
        f"{clean_metod} prueba profile",
        active_config.embedding_deployment,
    )
    profiles_by_prueba = {
        row.get("prueba_id", row.get("id")): row
        for row in profile_rows
        if row.get("embedding")
    }
    missing_profiles = [
        prueba.prueba_id
        for prueba in pruebas
        if prueba.prueba_id not in profiles_by_prueba
    ]
    if missing_profiles:
        raise ValueError(
            f"Missing admin profile embeddings for {missing_profiles}. "
            "Rebuild them with 01_admin_build_knowledge.py."
        )

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

    observations = []
    retrieval_debug_rows = []
    prompt_files_sent = 0
    prompt_files_skipped = 0
    reranked_pruebas = 0
    uploaded_files: dict[str, tuple[str, str]] = {}
    evidence_bm25 = (
        build_bm25_index(evidence_rows)
        if active_config.retrieval_mode == "hybrid"
        else None
    )
    global_bm25 = (
        build_bm25_index(global_context_rows)
        if active_config.retrieval_mode == "hybrid"
        else None
    )
    for prueba in pruebas:
        profile_row = profiles_by_prueba[prueba.prueba_id]
        query_text = profile_row.get("text") or prueba_profile_text(prueba)
        query_embedding = profile_row["embedding"]
        first_stage_k = (
            active_config.top_k_evidence * active_config.candidate_multiplier
            if active_config.enable_rerank
            else active_config.top_k_evidence
        )
        selected_evidence_rows = _retrieve_context(
            query_text,
            query_embedding,
            evidence_rows,
            first_stage_k,
            active_config,
            evidence_bm25,
        )
        if active_config.enable_rerank:
            selected_evidence_rows, reranked = rerank_rows(
                query_text,
                selected_evidence_rows,
                active_config.top_k_evidence,
                client.parse_response,
                min_relevance=active_config.rerank_min_relevance,
            )
            reranked_pruebas += int(reranked)
        retrieved_evidence = compact_retrieved_evidence(selected_evidence_rows)
        selected_global_context_rows = _retrieve_context(
            query_text,
            query_embedding,
            global_context_rows,
            active_config.top_k_global_context,
            active_config,
            global_bm25,
        )
        retrieved_global_context = compact_retrieved_evidence(selected_global_context_rows)
        selected_glossary_rows = _select_glossary_rows(
            query_text,
            query_embedding,
            glossary_rows,
            active_config.top_k_glossary,
        )
        file_inputs, attached_files, attached_file_paths, skipped_files = (
            _prompt_file_attachments(
                selected_evidence_rows,
                selected_global_context_rows,
                client,
                uploaded_files,
                active_config.max_prompt_files,
            )
        )
        prompt_files_sent += len(file_inputs)
        prompt_files_skipped += len(skipped_files)
        image_data_urls, attached_image_files = _prompt_image_attachments(
            selected_evidence_rows,
            active_config.max_prompt_images,
        )
        prueba_markdown = read_prueba_markdown(paths["knowledge_dir"], prueba)
        input_text = build_generation_input(
            prueba,
            prueba_markdown,
            retrieved_evidence,
            retrieved_global_context,
            selected_glossary_rows,
            attached_files=attached_files,
            attached_image_files=attached_image_files,
        )
        observations.append(
            generate_observation(
                input_text,
                prueba,
                client.parse_response,
                file_inputs=file_inputs,
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
                    "retrieval_mode": active_config.retrieval_mode,
                    "found_by": row.get("found_by"),
                    "rerank_relevance": row.get("rerank_relevance"),
                    "chunk_id": row.get("id"),
                    "source_file": row.get("source_file"),
                    "sent_as_prompt_file": row.get("chunk", {})
                    .get("metadata", {})
                    .get("source_path")
                    in attached_file_paths,
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
                    "sent_as_prompt_file": row.get("chunk", {})
                    .get("metadata", {})
                    .get("source_path")
                    in attached_file_paths,
                }
            )

    run_id = utc_run_id(clean_metod)
    usage_summary = {
        **evidence_summary,
        **global_context_summary,
        "pruebas_processed": len(pruebas),
        "controls_processed": sum(len(prueba.controls) for prueba in pruebas),
        "llm_generation_requests": len(pruebas),
        "retrieval_mode": active_config.retrieval_mode,
        "rerank_enabled": active_config.enable_rerank,
        "pruebas_reranked": reranked_pruebas,
        "llm_rerank_requests": reranked_pruebas,
        "top_k_global_context_per_prueba": active_config.top_k_global_context,
        "max_prompt_files_per_prueba": active_config.max_prompt_files,
        "files_uploaded": len(uploaded_files),
        "prompt_files_sent": prompt_files_sent,
        "prompt_files_skipped_by_size": prompt_files_skipped,
        "max_prompt_images_per_prueba": active_config.max_prompt_images,
        "glossary_embeddings_loaded": len(glossary_rows),
        "profile_embeddings_loaded": len(profile_rows),
        "admin_query_embeddings_reused": len(pruebas),
    }
    output_paths = save_run_outputs(
        active_config.outputs_base_dir,
        resolve_run_details_dir(active_config),
        clean_metod,
        run_id,
        observations,
        retrieval_debug_rows,
        usage_summary,
    )
    result = {
        "metod_id": clean_metod,
        "run_id": run_id,
        "output_paths": output_paths,
        "usage_summary": usage_summary,
        "observations": [observation.to_dict() for observation in observations],
    }
    for file_id, _ in uploaded_files.values():
        client.delete_input_file(file_id)
    return result
