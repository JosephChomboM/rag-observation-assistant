import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import OUTPUT_DIR, PROJECT_ROOT
from io_utils import file_sha256, read_text, write_json, write_jsonl
from rag_chunking_pipeline import (
    DEFAULT_STRATEGIES,
    build_chunk_embedding_rows,
    chunk_file_for_strategy,
    describe_image,
    embedding_file_for_strategy,
    get_embedding,
    image_to_base64_data_url,
    list_images,
    read_jsonl,
    require_azure_client,
    resolve_deployments,
    retrieve_top_k,
)

TEXT_EXTENSIONS = {".txt", ".md"}

ALLOCATION_PROFILES = {
    "static_global_7": {
        "description": "Baseline: take the best 7 chunks globally, without reserving quota by modality.",
        "mode": "global",
        "global_k": 7,
    },
    "dynamic_text_5_image_2": {
        "description": "Dynamic allocation: prioritize text evidence, then image evidence.",
        "mode": "modality_budget",
        "text_k": 5,
        "image_k": 2,
    },
    "dynamic_text_2_image_5": {
        "description": "Dynamic allocation: prioritize image evidence, then text evidence.",
        "mode": "modality_budget",
        "text_k": 2,
        "image_k": 5,
    },
}


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")


def list_text_files(inputs_dir: Path) -> list[Path]:
    if not inputs_dir.exists():
        raise FileNotFoundError(f"Input folder does not exist: {inputs_dir}")
    if not inputs_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a folder: {inputs_dir}")

    return sorted(
        path
        for path in inputs_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS
    )


def normalize_text_query(text: str, max_chars: int = 6000) -> str:
    clean_text = " ".join(text.split())
    if len(clean_text) <= max_chars:
        return clean_text
    return clean_text[:max_chars].rsplit(" ", 1)[0]


def build_text_input_items(text_files: list[Path], inputs_dir: Path) -> list[dict]:
    items = []
    for path in text_files:
        text = read_text(path)
        if not text:
            continue

        relative_path = path.relative_to(inputs_dir).as_posix()
        items.append(
            {
                "input_name": path.name,
                "relative_input_path": relative_path,
                "input_path": str(path),
                "input_sha256": file_sha256(path),
                "modality": "text",
                "query_text": normalize_text_query(text),
                "summary": normalize_text_query(text, max_chars=1200),
            }
        )
    return items


def build_image_input_items(
    client: Any,
    image_files: list[Path],
    inputs_dir: Path,
    vision_deployment: str,
    metod_id: str,
) -> tuple[list[dict], list[dict]]:
    items = []
    descriptions = []
    for path in image_files:
        description = describe_image(client, path, vision_deployment, metod_id)
        query_text = json.dumps(
            {
                "summary": description.get("summary"),
                "visible_metrics": description.get("visible_metrics", []),
                "methodology_signals": description.get("methodology_signals", []),
                "possible_queries": description.get("possible_queries", []),
            },
            ensure_ascii=False,
        )
        relative_path = path.relative_to(inputs_dir).as_posix()

        item = {
            "input_name": path.name,
            "relative_input_path": relative_path,
            "input_path": str(path),
            "input_sha256": description["image_sha256"],
            "modality": "image",
            "query_text": query_text,
            "summary": description.get("summary", ""),
        }
        items.append(item)
        descriptions.append(description)
    return items, descriptions


def build_input_embeddings(
    client: Any,
    input_items: list[dict],
    embedding_deployment: str,
) -> list[dict]:
    rows = []
    for item in input_items:
        text_sha256 = hashlib.sha256(item["query_text"].encode("utf-8")).hexdigest()
        rows.append(
            {
                **item,
                "query_text_sha256": text_sha256,
                "embedding_model": embedding_deployment,
                "embedding": get_embedding(client, item["query_text"], embedding_deployment),
            }
        )
    return rows


def load_or_create_chunk_embeddings(
    client: Any,
    chunks_base_dir: Path,
    strategy: str,
    embedding_deployment: str,
) -> list[dict]:
    chunk_path = chunk_file_for_strategy(chunks_base_dir, strategy)
    if not chunk_path.exists():
        raise FileNotFoundError(f"Chunk file does not exist for strategy '{strategy}': {chunk_path}")

    chunks = read_jsonl(chunk_path)
    if not chunks:
        raise ValueError(f"No chunks found for strategy '{strategy}': {chunk_path}")

    embedding_path = embedding_file_for_strategy(chunks_base_dir, strategy)
    existing = read_jsonl(embedding_path) if embedding_path.exists() else []
    rows = build_chunk_embedding_rows(client, chunks, embedding_deployment, existing)
    write_jsonl(embedding_path, rows)
    return rows


def retrieve_for_inputs(
    input_embedding_rows: list[dict],
    chunk_embedding_rows: list[dict],
    strategy: str,
    max_k: int,
    run_id: str,
    metod_id: str,
) -> list[dict]:
    rows = []
    for input_row in input_embedding_rows:
        retrieved = retrieve_top_k(input_row["embedding"], chunk_embedding_rows, max_k)
        for rank, item in enumerate(retrieved, start=1):
            rows.append(
                {
                    "run_id": run_id,
                    "metod_id": metod_id,
                    "strategy": strategy,
                    "input_name": input_row["input_name"],
                    "relative_input_path": input_row["relative_input_path"],
                    "input_sha256": input_row["input_sha256"],
                    "modality": input_row["modality"],
                    "rank": rank,
                    **item,
                }
            )
    return rows


def max_profile_k(profile_names: list[str]) -> int:
    max_k = 1
    for name in profile_names:
        profile = ALLOCATION_PROFILES[name]
        if profile["mode"] == "global":
            max_k = max(max_k, int(profile["global_k"]))
        else:
            max_k = max(max_k, int(profile["text_k"]), int(profile["image_k"]))
    return max_k


def select_profile_rows(rows: list[dict], profile_name: str) -> list[dict]:
    profile = ALLOCATION_PROFILES[profile_name]
    sorted_rows = sorted(rows, key=lambda item: item["score"], reverse=True)

    if profile["mode"] == "global":
        selected = sorted_rows[: int(profile["global_k"])]
    else:
        selected = []
        budgets = {"text": int(profile["text_k"]), "image": int(profile["image_k"])}
        for modality, budget in budgets.items():
            modality_rows = [row for row in sorted_rows if row["modality"] == modality]
            selected.extend(modality_rows[:budget])
        selected.sort(key=lambda item: item["score"], reverse=True)

    return [
        {
            **row,
            "allocation_profile": profile_name,
            "allocation_rank": rank,
        }
        for rank, row in enumerate(selected, start=1)
    ]


def summarize_profile_rows(rows: list[dict], profile_name: str) -> dict:
    scores = [row["score"] for row in rows]
    return {
        "allocation_profile": profile_name,
        "selected_chunks": len(rows),
        "text_chunks": sum(1 for row in rows if row["modality"] == "text"),
        "image_chunks": sum(1 for row in rows if row["modality"] == "image"),
        "unique_inputs": len({row["input_name"] for row in rows}),
        "unique_knowledge_chunks": len({row["chunk_id"] for row in rows}),
        "unique_knowledge_sources": len({row["relative_path"] for row in rows}),
        "avg_score": round(sum(scores) / len(scores), 6) if scores else 0,
        "min_score": round(min(scores), 6) if scores else 0,
        "max_score": round(max(scores), 6) if scores else 0,
        "profile_definition": ALLOCATION_PROFILES[profile_name],
    }


def compact_input_evidence(input_items: list[dict]) -> list[dict]:
    return [
        {
            "input_name": item["input_name"],
            "modality": item["modality"],
            "summary": item["summary"],
        }
        for item in input_items
    ]


def compact_selected_chunks(rows: list[dict]) -> list[dict]:
    return [
        {
            "allocation_rank": row["allocation_rank"],
            "input_name": row["input_name"],
            "modality": row["modality"],
            "score": round(row["score"], 6),
            "source_file": row["source_file"],
            "relative_path": row["relative_path"],
            "heading_path": row.get("heading_path", []),
            "text_preview": row.get("text_preview", ""),
        }
        for row in rows
    ]


def build_observation_image_parts(input_items: list[dict], image_detail: str) -> list[dict]:
    parts = []
    for item in input_items:
        if item.get("modality") != "image":
            continue

        image_path = Path(item["input_path"])
        if not image_path.exists():
            raise FileNotFoundError(f"Image input no longer exists: {image_path}")

        parts.extend(
            [
                {"type": "text", "text": f"Imagen original para analisis visual: {item['input_name']}"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_to_base64_data_url(image_path),
                        "detail": image_detail,
                    },
                },
            ]
        )
    return parts


def generate_observation(
    client: Any,
    chat_deployment: str,
    metod_id: str,
    knowledge_strategy: str,
    allocation_profile: str,
    input_items: list[dict],
    selected_rows: list[dict],
    include_images_in_observation: bool,
    observation_image_detail: str,
) -> dict:
    payload = {
        "metod_id": metod_id,
        "knowledge_chunking_strategy": knowledge_strategy,
        "allocation_profile": allocation_profile,
        "allocation_definition": ALLOCATION_PROFILES[allocation_profile],
        "image_inputs_attached_to_prompt": include_images_in_observation,
        "image_detail": observation_image_detail if include_images_in_observation else None,
        "input_evidence": compact_input_evidence(input_items),
        "selected_knowledge_chunks": compact_selected_chunks(selected_rows),
    }

    prompt = f"""
Eres un revisor senior de validacion de modelos del BCP.

Genera una observacion consolidada para METOD usando evidencia de entrada
multimodal, chunks de conocimiento recuperados y, si estan adjuntas, las
imagenes originales del folder de entrada.

La comparacion del experimento es:
- knowledge_chunking_strategy: static o dynamic
- allocation_profile: static_global_7, dynamic_text_5_image_2 o dynamic_text_2_image_5

Reglas:
- No inventes valores.
- Usa evidencia de todas las entradas disponibles, texto e imagen.
- Si hay imagenes adjuntas, revisalas directamente y contrastalas con la evidencia textual extraida.
- Usa los chunks recuperados como criterio metodologico RAG, no como evidencia del modelo validado.
- Explica si el perfil de asignacion ayudo o genero ruido.
- Cita las fuentes de conocimiento recuperadas.
- Devuelve solo JSON valido.

Required JSON:
{{
  "metod_id": "{metod_id}",
  "knowledge_strategy": "{knowledge_strategy}",
  "allocation_profile": "{allocation_profile}",
  "criticality": "Alta|Media|Baja|Sin observacion",
  "observation": "...",
  "evidence": "...",
  "risk": "...",
  "action_plan": "...",
  "allocation_assessment": "...",
  "missing_information": ["..."],
  "sources": [
    {{
      "source_file": "...",
      "relative_path": "...",
      "heading_path": ["..."],
      "reason_used": "..."
    }}
  ]
}}

Payload:
{json.dumps(payload, ensure_ascii=False)}
""".strip()

    content = [{"type": "text", "text": prompt}]
    if include_images_in_observation:
        content.extend(build_observation_image_parts(input_items, observation_image_detail))

    response = client.chat.completions.create(
        model=chat_deployment,
        messages=[{"role": "user", "content": content}],
        temperature=0.1,
    )
    content_text = response.choices[0].message.content.strip()
    if content_text.startswith("```json"):
        content_text = content_text.removeprefix("```json").removesuffix("```").strip()
    elif content_text.startswith("```"):
        content_text = content_text.removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(content_text)
    except json.JSONDecodeError:
        return {
            "metod_id": metod_id,
            "knowledge_strategy": knowledge_strategy,
            "allocation_profile": allocation_profile,
            "criticality": "Media",
            "observation": content_text,
            "evidence": "",
            "risk": "",
            "action_plan": "",
            "allocation_assessment": "The model response was not valid JSON.",
            "missing_information": ["Model response could not be parsed as JSON."],
            "sources": [],
        }

def observation_to_markdown(observation: dict) -> str:
    sources = []
    for source in observation.get("sources", []):
        heading_path = " > ".join(source.get("heading_path", []))
        heading = f" ({heading_path})" if heading_path else ""
        sources.append(f"- {source.get('source_file', '')}{heading}: {source.get('reason_used', '')}")

    missing = [f"- {item}" for item in observation.get("missing_information", [])]

    return "\n".join(
        [
            f"# Observacion - {observation.get('knowledge_strategy', '')} / {observation.get('allocation_profile', '')}",
            "",
            f"**METOD:** {observation.get('metod_id', '')}",
            f"**Criticidad:** {observation.get('criticality', '')}",
            "",
            "## Observacion",
            observation.get("observation", ""),
            "",
            "## Evidencia",
            observation.get("evidence", ""),
            "",
            "## Riesgo",
            observation.get("risk", ""),
            "",
            "## Plan de accion",
            observation.get("action_plan", ""),
            "",
            "## Evaluacion del perfil",
            observation.get("allocation_assessment", ""),
            "",
            "## Informacion faltante",
            "\n".join(missing) if missing else "- None",
            "",
            "## Sources",
            "\n".join(sources) if sources else "- None",
            "",
        ]
    )


def rank_profile_summaries(profile_summaries: list[dict]) -> list[dict]:
    ranked = sorted(
        profile_summaries,
        key=lambda item: (
            item["unique_inputs"],
            item["unique_knowledge_sources"],
            item["avg_score"],
            -abs(item["text_chunks"] - item["image_chunks"]),
        ),
        reverse=True,
    )
    return [
        {
            **item,
            "ranking_position": index,
        }
        for index, item in enumerate(ranked, start=1)
    ]


def validate_inputs(
    inputs_dir: Path,
    chunks_base_dir: Path,
    strategies: tuple[str, ...],
    profile_names: list[str],
    dry_run: bool,
) -> dict:
    unsupported_strategies = sorted(set(strategies) - set(DEFAULT_STRATEGIES))
    if unsupported_strategies:
        raise ValueError(f"Unsupported strategies: {unsupported_strategies}. Expected: {DEFAULT_STRATEGIES}")

    unsupported_profiles = sorted(set(profile_names) - set(ALLOCATION_PROFILES))
    if unsupported_profiles:
        raise ValueError(f"Unsupported allocation profiles: {unsupported_profiles}")

    images = list_images(inputs_dir)
    text_files = list_text_files(inputs_dir)
    if not images and not text_files and not dry_run:
        raise ValueError(f"No supported image/text inputs found in: {inputs_dir}")

    chunk_counts = {}
    for strategy in strategies:
        chunk_path = chunk_file_for_strategy(chunks_base_dir, strategy)
        chunks = read_jsonl(chunk_path)
        if not chunks:
            raise ValueError(f"No chunks found for strategy '{strategy}': {chunk_path}")
        chunk_counts[strategy] = len(chunks)

    return {
        "image_count": len(images),
        "text_file_count": len(text_files),
        "chunk_counts": chunk_counts,
        "allocation_profiles": profile_names,
    }


def run_pipeline(
    metod_id: str,
    inputs_dir: Path,
    chunks_base_dir: Path,
    output_dir: Path,
    strategies: tuple[str, ...],
    allocation_profiles: list[str],
    dry_run: bool,
    include_images_in_observation: bool,
    observation_image_detail: str,
    client: Any | None = None,
    embedding_model_name: str | None = None,
    embedding_deployment: str | None = None,
    chat_model_name: str | None = None,
    chat_deployment: str | None = None,
    provider_name: str = "azure_ai_foundry",
) -> None:
    validation = validate_inputs(inputs_dir, chunks_base_dir, strategies, allocation_profiles, dry_run)
    if dry_run:
        print("Dry run OK")
        print("Images:", validation["image_count"])
        print("Text files:", validation["text_file_count"])
        print("Chunk counts:", validation["chunk_counts"])
        print("Allocation profiles:", validation["allocation_profiles"])
        return

    if client is None:
        client = require_azure_client()
        embedding_model_name, embedding_deployment, chat_model_name, chat_deployment = resolve_deployments()
    else:
        missing_model_fields = [
            name
            for name, value in {
                "embedding_model_name": embedding_model_name,
                "embedding_deployment": embedding_deployment,
                "chat_model_name": chat_model_name,
                "chat_deployment": chat_deployment,
            }.items()
            if not value
        ]
        if missing_model_fields:
            raise ValueError(
                "Injected clients must include model/deployment metadata: "
                + ", ".join(missing_model_fields)
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    image_files = list_images(inputs_dir)
    text_files = list_text_files(inputs_dir)

    text_items = build_text_input_items(text_files, inputs_dir)
    image_items, image_descriptions = build_image_input_items(
        client=client,
        image_files=image_files,
        inputs_dir=inputs_dir,
        vision_deployment=chat_deployment,
        metod_id=metod_id,
    )
    input_items = text_items + image_items
    if not input_items:
        raise ValueError(f"No non-empty supported inputs found in: {inputs_dir}")

    input_embedding_rows = build_input_embeddings(client, input_items, embedding_deployment)
    max_k = max_profile_k(allocation_profiles)

    all_retrieval_rows = []
    all_selected_rows = []
    profile_summaries = []
    observations = {}

    embeddings_by_strategy = {
        strategy: load_or_create_chunk_embeddings(client, chunks_base_dir, strategy, embedding_deployment)
        for strategy in strategies
    }

    for strategy in strategies:
        strategy_rows = retrieve_for_inputs(
            input_embedding_rows=input_embedding_rows,
            chunk_embedding_rows=embeddings_by_strategy[strategy],
            strategy=strategy,
            max_k=max_k,
            run_id=output_dir.name,
            metod_id=metod_id,
        )
        all_retrieval_rows.extend(strategy_rows)

        for profile_name in allocation_profiles:
            selected_rows = select_profile_rows(strategy_rows, profile_name)
            all_selected_rows.extend(selected_rows)
            summary = summarize_profile_rows(selected_rows, profile_name)
            summary["knowledge_strategy"] = strategy
            profile_summaries.append(summary)

            observation = generate_observation(
                client=client,
                chat_deployment=chat_deployment,
                metod_id=metod_id,
                knowledge_strategy=strategy,
                allocation_profile=profile_name,
                input_items=input_items,
                selected_rows=selected_rows,
                include_images_in_observation=include_images_in_observation,
                observation_image_detail=observation_image_detail,
            )
            observations[f"{strategy}__{profile_name}"] = observation
            write_json(output_dir / f"observation_{strategy}_{profile_name}.json", observation)
            (output_dir / f"observation_{strategy}_{profile_name}.md").write_text(
                observation_to_markdown(observation),
                encoding="utf-8",
            )

    comparison = {
        "metod_id": metod_id,
        "run_id": output_dir.name,
        "note": (
            "This experiment compares context allocation by modality. "
            "It is not the same as document-level dynamic chunking."
        ),
        "ranked_profiles": rank_profile_summaries(profile_summaries),
        "decision_rule": (
            "Use metrics as a first filter, then manually compare generated observations. "
            "Prefer profiles with relevant sources, enough input coverage, and less noisy observations."
        ),
    }

    write_jsonl(output_dir / "image_descriptions.jsonl", image_descriptions)
    write_jsonl(output_dir / "input_items.jsonl", input_items)
    write_jsonl(output_dir / "input_embeddings.jsonl", input_embedding_rows)
    write_jsonl(output_dir / "retrieval_results_all.jsonl", all_retrieval_rows)
    write_jsonl(output_dir / "retrieval_results_selected.jsonl", all_selected_rows)
    write_json(output_dir / "allocation_metrics.json", {"profile_summaries": profile_summaries})
    write_json(output_dir / "allocation_comparison.json", comparison)
    write_json(output_dir / "run_config.json", {
        "provider_name": provider_name,
        "metod_id": metod_id,
        "inputs_dir": str(inputs_dir),
        "chunks_base_dir": str(chunks_base_dir),
        "output_dir": str(output_dir),
        "strategies": list(strategies),
        "allocation_profiles": allocation_profiles,
        "include_images_in_observation": include_images_in_observation,
        "observation_image_detail": observation_image_detail,
        "embedding_model_name": embedding_model_name,
        "embedding_deployment": embedding_deployment,
        "chat_model_name": chat_model_name,
        "chat_deployment": chat_deployment,
    })

    print("Images processed:", len(image_items))
    print("Text files processed:", len(text_items))
    print("Selected rows:", len(all_selected_rows))
    print("Output:", output_dir)


def main(
    metod_id: str = "METOD5",
    strategies: tuple[str, ...] = DEFAULT_STRATEGIES,
    allocation_profiles: list[str] | None = None,
    dry_run: bool = False,
    inputs_dir: str | Path | None = None,
    chunks_base_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    include_images_in_observation: bool = True,
    observation_image_detail: str = "low",
    client: Any | None = None,
    embedding_model_name: str | None = None,
    embedding_deployment: str | None = None,
    chat_model_name: str | None = None,
    chat_deployment: str | None = None,
    provider_name: str = "azure_ai_foundry",
) -> None:
    run_id = utc_run_id()
    resolved_inputs_dir = Path(inputs_dir) if inputs_dir else PROJECT_ROOT / "inputs" / metod_id
    resolved_chunks_base_dir = Path(chunks_base_dir) if chunks_base_dir else OUTPUT_DIR
    resolved_output_dir = (
        Path(output_dir)
        if output_dir
        else PROJECT_ROOT / "modality_outputs" / metod_id / run_id
    )
    resolved_profiles = allocation_profiles or list(ALLOCATION_PROFILES)

    run_pipeline(
        metod_id=metod_id,
        inputs_dir=resolved_inputs_dir,
        chunks_base_dir=resolved_chunks_base_dir,
        output_dir=resolved_output_dir,
        strategies=tuple(strategies),
        allocation_profiles=resolved_profiles,
        dry_run=dry_run,
        include_images_in_observation=include_images_in_observation,
        observation_image_detail=observation_image_detail,
        client=client,
        embedding_model_name=embedding_model_name,
        embedding_deployment=embedding_deployment,
        chat_model_name=chat_model_name,
        chat_deployment=chat_deployment,
        provider_name=provider_name,
    )


if __name__ == "__main__":
    main(dry_run=True)




