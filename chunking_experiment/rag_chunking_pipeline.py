import base64
import csv
import hashlib
import json
import math
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import OUTPUT_DIR, PROJECT_ROOT
from io_utils import file_sha256, write_json, write_jsonl

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_STRATEGIES = ("static", "dynamic")


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"JSONL file does not exist: {path}")

    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            clean_line = line.strip()
            if not clean_line:
                continue
            try:
                rows.append(json.loads(clean_line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {error}") from error
    return rows


def list_images(inputs_dir: Path) -> list[Path]:
    if not inputs_dir.exists():
        raise FileNotFoundError(f"Input images folder does not exist: {inputs_dir}")
    if not inputs_dir.is_dir():
        raise NotADirectoryError(f"Input images path is not a folder: {inputs_dir}")

    return sorted(
        path
        for path in inputs_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def chunk_file_for_strategy(chunks_base_dir: Path, strategy: str) -> Path:
    return chunks_base_dir / strategy / f"chunks_{strategy}.jsonl"


def embedding_file_for_strategy(chunks_base_dir: Path, strategy: str) -> Path:
    return chunks_base_dir / strategy / f"chunks_{strategy}_embeddings.jsonl"


def load_eval_labels(path: Path | None) -> dict[str, list[dict]]:
    if path is None or not path.exists():
        return {}

    labels_by_image: dict[str, list[dict]] = {}
    for row in read_jsonl(path):
        image_name = row.get("image_name")
        expected = row.get("expected", [])
        if not image_name:
            raise ValueError(f"Evaluation label is missing image_name: {row}")
        if not isinstance(expected, list) or not expected:
            raise ValueError(f"Evaluation label must include non-empty expected list: {row}")
        labels_by_image[image_name] = expected
    return labels_by_image


def require_azure_client():
    load_local_env()
    inject_truststore()

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21").strip()

    missing = []
    if not endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY")
    if missing:
        raise ValueError(
            "Missing Azure OpenAI environment variable(s): "
            + ", ".join(missing)
            + ". Configure them on the Databricks cluster before running the pipeline."
        )

    from openai import AzureOpenAI

    return AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )


def load_local_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as error:
        raise ImportError(
            "python-dotenv is required for local .env loading. Install it with `%pip install python-dotenv` in Databricks."
        ) from error

    load_dotenv(".env", override=True)
    project_env = PROJECT_ROOT / ".env"
    if project_env.exists():
        load_dotenv(project_env, override=True)


def inject_truststore() -> None:
    try:
        import truststore
    except ImportError as error:
        raise ImportError(
            "truststore is required for SSL configuration. Install it with `%pip install truststore` in Databricks."
        ) from error

    truststore.inject_into_ssl()


def resolve_deployments() -> tuple[str, str, str, str]:
    embedding_model_name = os.getenv("MODEL_NAME_EMB_SMALL", "text-embedding-3-small").strip()
    embedding_deployment = (
        os.getenv("DEPLOYMENT_EMB_SMALL")
        or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or embedding_model_name
    ).strip()

    chat_model_name = os.getenv("MODEL_NAME_GPT4", "gpt-4o").strip()
    chat_deployment = (
        os.getenv("DEPLOYMENT_GPT4")
        or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        or chat_model_name
    ).strip()

    missing = []
    if not embedding_deployment:
        missing.append("DEPLOYMENT_EMB_SMALL")
    if not chat_deployment:
        missing.append("DEPLOYMENT_GPT4")
    if missing:
        raise ValueError("Missing deployment variable(s): " + ", ".join(missing))

    return embedding_model_name, embedding_deployment, chat_model_name, chat_deployment


def get_embedding(client: Any, text: str, embedding_deployment: str) -> list[float]:
    response = client.embeddings.create(
        model=embedding_deployment,
        input=text,
    )
    return response.data[0].embedding


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def build_chunk_embedding_rows(
    client: Any,
    chunks: list[dict],
    embedding_deployment: str,
    existing_rows: list[dict],
) -> list[dict]:
    existing_by_id = {
        row["chunk_id"]: row
        for row in existing_rows
        if row.get("chunk_id")
        and row.get("text_sha256")
        and row.get("embedding")
        and row.get("embedding_model") == embedding_deployment
    }

    rows = []
    for index, chunk in enumerate(chunks, start=1):
        text = chunk.get("text", "")
        text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = existing_by_id.get(chunk["chunk_id"])

        if cached and cached.get("text_sha256") == text_sha256:
            rows.append(cached)
            continue

        rows.append(
            {
                "chunk_id": chunk["chunk_id"],
                "strategy": chunk["strategy"],
                "relative_path": chunk["relative_path"],
                "source_file": chunk["source_file"],
                "text_sha256": text_sha256,
                "embedding_model": embedding_deployment,
                "embedding": get_embedding(client, text, embedding_deployment),
                "chunk": chunk,
            }
        )

        if index % 10 == 0:
            print(f"Embedded chunks: {index}/{len(chunks)}")

    return rows


def image_to_base64_data_url(image_path: Path) -> str:
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def describe_image(
    client: Any,
    image_path: Path,
    vision_deployment: str,
    metod_id: str,
) -> dict:
    prompt = f"""
Describe esta imagen como evidencia para un benchmark de recuperaciÃ³n RAG.

EnfÃ³cate en la informaciÃ³n visible que pueda ayudar a recuperar conocimiento de METOD, especialmente:

* criterios de validaciÃ³n
* tamaÃ±os de muestra
* cantidades objetivo
* Gini, calibraciÃ³n, tuning, Train/Dev/Test, Test/OOT
* tablas, grÃ¡ficos, advertencias y notas metodolÃ³gicas

METOD seleccionado: {metod_id}

Devuelve un JSON conciso con:

summary, visible_metrics, methodology_signals, possible_queries, confidence.

No inventes valores que no sean visibles.
""".strip()

    response = client.chat.completions.create(
        model=vision_deployment,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_to_base64_data_url(image_path),
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
        temperature=0.0,
        max_tokens=700,
        response_format={"type": "json_object"},
    )

    raw_content = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        parsed = {"summary": raw_content, "visible_metrics": [], "methodology_signals": [], "confidence": 0.0}

    parsed.update(
        {
            "image_path": str(image_path),
            "image_name": image_path.name,
            "image_sha256": file_sha256(image_path),
            "vision_model": vision_deployment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return parsed


def normalize_image_description(description: dict) -> str:
    parts = [
        f"Image: {description.get('image_name', '')}",
        f"Summary: {description.get('summary', '')}",
    ]

    for key in ("visible_metrics", "methodology_signals", "possible_queries"):
        value = description.get(key, [])
        if value:
            parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")

    return "\n".join(parts).strip()


def retrieve_top_k(
    query_embedding: list[float],
    chunk_embedding_rows: list[dict],
    top_k: int,
) -> list[dict]:
    scored = []
    for row in chunk_embedding_rows:
        score = cosine_similarity(query_embedding, row.get("embedding", []))
        chunk = row["chunk"]
        scored.append(
            {
                "score": score,
                "chunk_id": row["chunk_id"],
                "strategy": row["strategy"],
                "source_file": row["source_file"],
                "relative_path": row["relative_path"],
                "heading_path": chunk.get("metadata", {}).get("heading_path", []),
                "text_preview": chunk.get("text", "")[:500],
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def group_results_by_strategy(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["strategy"], []).append(row)
    return grouped


def compact_image_descriptions(descriptions: list[dict]) -> list[dict]:
    return [
        {
            "image_name": description.get("image_name"),
            "summary": description.get("summary"),
            "visible_metrics": description.get("visible_metrics", []),
            "methodology_signals": description.get("methodology_signals", []),
            "confidence": description.get("confidence"),
        }
        for description in descriptions
    ]


def compact_retrieved_chunks_by_image(rows: list[dict], max_chunks_per_image: int = 3) -> list[dict]:
    rows_by_image: dict[str, list[dict]] = {}
    for row in rows:
        rows_by_image.setdefault(row["image_name"], []).append(row)

    compact = []
    seen_per_image: dict[str, set[str]] = {}

    for image_name in sorted(rows_by_image):
        image_rows = sorted(rows_by_image[image_name], key=lambda item: item["rank"])
        seen_per_image[image_name] = set()
        image_chunk_count = 0

        for row in image_rows:
            chunk_id = row["chunk_id"]
            if chunk_id in seen_per_image[image_name]:
                continue

            seen_per_image[image_name].add(chunk_id)
            compact.append(
                {
                    "image_name": image_name,
                    "rank": row.get("rank"),
                    "chunk_id": chunk_id,
                    "source_file": row.get("source_file"),
                    "relative_path": row.get("relative_path"),
                    "heading_path": row.get("heading_path", []),
                    "score": round(float(row.get("score", 0)), 6),
                    "text_preview": row.get("text_preview", ""),
                }
            )
            image_chunk_count += 1

            if image_chunk_count >= max_chunks_per_image:
                break

    return compact


def generate_observation_for_strategy(
    client: Any,
    chat_deployment: str,
    metod_id: str,
    strategy: str,
    image_descriptions: list[dict],
    retrieved_rows: list[dict],
) -> dict:
    prompt_payload = {
        "metod_id": metod_id,
        "chunking_strategy": strategy,
        "image_evidence": compact_image_descriptions(image_descriptions),
        "retrieved_chunks_by_image": compact_retrieved_chunks_by_image(retrieved_rows),
    }

    prompt = f"""
Eres el mejor revisor senior de validaciÃ³n de modelos del Banco de Credito del Peru (BCP).

Genera una observaciÃ³n de validaciÃ³n consolidada usando TODAS las imÃ¡genes del folder de entrada.

Usa Ãºnicamente:

1. la evidencia extraÃ­da de todas las imÃ¡genes
2. los chunks de conocimiento METOD recuperados mediante la estrategia de chunking `{strategy}`

Reglas:

- No inventes valores.
- No te limites a la primera imagen.
- Revisa cada elemento de `image_evidence`.
- Usa `retrieved_chunks_by_image` para considerar evidencia recuperada por cada imagen.
- Si una imagen no aporta evidencia suficiente, indÃ­calo en `missing_information`.
- Si los chunks recuperados no son suficientes, indica quÃ© informaciÃ³n falta.
- Cita los archivos fuente y los encabezados de los chunks recuperados.
- Devuelve Ãºnicamente JSON vÃ¡lido.


Required JSON:
{{
  "strategy": "{strategy}",
  "metod_id": "{metod_id}",
  "observation": "...",
  "criticality": "Low | Medium | High | Critical | Not enough evidence",
  "evidence": "...",
  "risk": "...",
  "action_plan": "...",
  "missing_information": ["..."],
  "sources": [
    {{
      "source_file": "...",
      "heading_path": ["..."],
      "reason_used": "..."
    }}
  ]
}}

Context:
{json.dumps(prompt_payload, indent=2, ensure_ascii=False)}
""".strip()

    response = client.chat.completions.create(
        model=chat_deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=1200,
        response_format={"type": "json_object"},
    )

    raw_content = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        parsed = {
            "strategy": strategy,
            "metod_id": metod_id,
            "observation": raw_content,
            "criticality": "Not enough evidence",
            "evidence": "",
            "risk": "",
            "action_plan": "",
            "missing_information": ["The model did not return valid JSON."],
            "sources": [],
        }

    parsed["strategy"] = strategy
    parsed["metod_id"] = metod_id
    parsed["created_at"] = datetime.now(timezone.utc).isoformat()
    return parsed


def observation_to_markdown(observation: dict) -> str:
    sources = []
    for source in observation.get("sources", []):
        heading_path = " > ".join(source.get("heading_path", []))
        heading = f" ({heading_path})" if heading_path else ""
        sources.append(f"- {source.get('source_file', '')}{heading}: {source.get('reason_used', '')}")

    missing = [f"- {item}" for item in observation.get("missing_information", [])]

    return "\n".join(
        [
            f"# Observacion - {observation.get('strategy', '')}",
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
            "## Informacion faltante",
            "\n".join(missing) if missing else "- None",
            "",
            "## Sources",
            "\n".join(sources) if sources else "- None",
            "",
        ]
    )


def metric_value(metrics_by_strategy: dict, strategy: str, key: str) -> float:
    return float(metrics_by_strategy.get(strategy, {}).get(key, 0))


def compare_observations_from_metrics(evaluation_metrics: dict, top_k: int) -> dict:
    if evaluation_metrics.get("status") != "computed":
        return {
            "winner": None,
            "reason": "No labeled evaluation was computed, so observation quality cannot be compared objectively.",
        }

    metrics_by_strategy = evaluation_metrics.get("metrics_by_strategy", {})
    section_key = f"section_recall_at_{top_k}"
    source_key = f"source_recall_at_{top_k}"

    ranking = []
    for strategy in sorted(metrics_by_strategy):
        ranking.append(
            {
                "strategy": strategy,
                section_key: metric_value(metrics_by_strategy, strategy, section_key),
                "section_mrr": metric_value(metrics_by_strategy, strategy, "section_mrr"),
                source_key: metric_value(metrics_by_strategy, strategy, source_key),
                "source_mrr": metric_value(metrics_by_strategy, strategy, "source_mrr"),
            }
        )

    ranking.sort(
        key=lambda item: (
            item[section_key],
            item["section_mrr"],
            item[source_key],
            item["source_mrr"],
        ),
        reverse=True,
    )

    winner = ranking[0]["strategy"] if ranking else None
    if len(ranking) > 1 and ranking[0] == ranking[1]:
        winner = None

    return {
        "winner": winner,
        "ranking": ranking,
        "decision_rule": f"Prefer higher {section_key}, then section_mrr, then {source_key}, then source_mrr.",
    }


def write_results_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_id",
        "image_name",
        "image_sha256",
        "strategy",
        "rank",
        "score",
        "chunk_id",
        "relative_path",
        "source_file",
        "heading_path",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def summarize_retrieval(rows: list[dict]) -> dict:
    by_strategy: dict[str, list[dict]] = {}
    for row in rows:
        by_strategy.setdefault(row["strategy"], []).append(row)

    summary = {}
    for strategy, strategy_rows in by_strategy.items():
        rank_1_scores = [row["score"] for row in strategy_rows if row["rank"] == 1]
        all_scores = [row["score"] for row in strategy_rows]
        summary[strategy] = {
            "result_rows": len(strategy_rows),
            "avg_top1_score": round(sum(rank_1_scores) / len(rank_1_scores), 6) if rank_1_scores else 0,
            "avg_returned_score": round(sum(all_scores) / len(all_scores), 6) if all_scores else 0,
            "unique_chunks_retrieved": len({row["chunk_id"] for row in strategy_rows}),
            "unique_sources_retrieved": len({row["relative_path"] for row in strategy_rows}),
        }
    return summary


def matches_expected_source(result: dict, label: dict) -> bool:
    expected_relative_path = label.get("relative_path")
    expected_source_file = label.get("source_file")
    expected_chunk_id = label.get("chunk_id")

    if expected_chunk_id and result.get("chunk_id") != expected_chunk_id:
        return False
    if expected_relative_path and result.get("relative_path") != expected_relative_path:
        return False
    if expected_source_file and result.get("source_file") != expected_source_file:
        return False

    return any(
        [
            expected_relative_path,
            expected_source_file,
            expected_chunk_id,
        ]
    )


def matches_expected_section(result: dict, label: dict) -> bool:
    if not matches_expected_source(result, label):
        return False

    expected_heading_contains = label.get("heading_contains")
    if not expected_heading_contains:
        return True

    needle = expected_heading_contains.lower()
    heading_text = " > ".join(result.get("heading_path") or []).lower()
    preview_text = result.get("text_preview", "").lower()
    return needle in heading_text or needle in preview_text


def evaluate_retrieval(rows: list[dict], labels_by_image: dict[str, list[dict]], top_k: int) -> dict:
    if not labels_by_image:
        return {
            "status": "skipped",
            "reason": "No eval labels were provided. Add eval/golden_labels.jsonl to compute recall@k.",
        }

    by_strategy_image: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (row["strategy"], row["image_name"])
        by_strategy_image.setdefault(key, []).append(row)

    strategies = sorted({row["strategy"] for row in rows})
    metrics = {}

    for strategy in strategies:
        labeled_images = 0
        source_hits_at_1 = 0
        source_hits_at_k = 0
        source_reciprocal_ranks = []
        section_hits_at_1 = 0
        section_hits_at_k = 0
        section_reciprocal_ranks = []
        missing_images = []

        for image_name, expected_labels in labels_by_image.items():
            strategy_rows = sorted(
                by_strategy_image.get((strategy, image_name), []),
                key=lambda item: item["rank"],
            )
            if not strategy_rows:
                missing_images.append(image_name)
                continue

            labeled_images += 1
            first_source_hit_rank = None
            first_section_hit_rank = None
            for row in strategy_rows[:top_k]:
                if first_source_hit_rank is None and any(
                    matches_expected_source(row, label) for label in expected_labels
                ):
                    first_source_hit_rank = row["rank"]
                if first_section_hit_rank is None and any(
                    matches_expected_section(row, label) for label in expected_labels
                ):
                    first_section_hit_rank = row["rank"]
                if first_source_hit_rank is not None and first_section_hit_rank is not None:
                    break

            if first_source_hit_rank is not None:
                source_hits_at_k += 1
                source_reciprocal_ranks.append(1 / first_source_hit_rank)
                if first_source_hit_rank == 1:
                    source_hits_at_1 += 1
            else:
                source_reciprocal_ranks.append(0)

            if first_section_hit_rank is not None:
                section_hits_at_k += 1
                section_reciprocal_ranks.append(1 / first_section_hit_rank)
                if first_section_hit_rank == 1:
                    section_hits_at_1 += 1
            else:
                section_reciprocal_ranks.append(0)

        metrics[strategy] = {
            "labeled_images": labeled_images,
            "missing_images": missing_images,
            "source_hit_at_1": round(source_hits_at_1 / labeled_images, 6) if labeled_images else 0,
            f"source_recall_at_{top_k}": round(source_hits_at_k / labeled_images, 6) if labeled_images else 0,
            "source_mrr": round(sum(source_reciprocal_ranks) / labeled_images, 6) if labeled_images else 0,
            "section_hit_at_1": round(section_hits_at_1 / labeled_images, 6) if labeled_images else 0,
            f"section_recall_at_{top_k}": round(section_hits_at_k / labeled_images, 6) if labeled_images else 0,
            "section_mrr": round(sum(section_reciprocal_ranks) / labeled_images, 6) if labeled_images else 0,
        }

    return {
        "status": "computed",
        "top_k": top_k,
        "labels_count": len(labels_by_image),
        "metrics_by_strategy": metrics,
        "how_to_read": {
            f"source_recall_at_{top_k}": "fraction of labeled images where an expected source file appears in top-k",
            f"section_recall_at_{top_k}": "fraction of labeled images where the expected source and section appears in top-k",
            "hit_at_1": "fraction of labeled images where the expected result is rank 1",
            "mrr": "mean reciprocal rank; higher means the expected result appears earlier",
        },
    }


def validate_inputs(
    images_dir: Path,
    chunks_base_dir: Path,
    strategies: tuple[str, ...],
    dry_run: bool,
    eval_labels_path: Path | None,
) -> dict:
    images = list_images(images_dir)
    chunk_counts = {}
    labels_by_image = load_eval_labels(eval_labels_path)

    for strategy in strategies:
        chunk_path = chunk_file_for_strategy(chunks_base_dir, strategy)
        chunks = read_jsonl(chunk_path)
        if not chunks:
            raise ValueError(f"No chunks found for strategy '{strategy}': {chunk_path}")
        chunk_counts[strategy] = len(chunks)

    if not images and not dry_run:
        raise ValueError(f"No supported images found in: {images_dir}")

    return {
        "image_count": len(images),
        "chunk_counts": chunk_counts,
        "eval_labels_count": len(labels_by_image),
    }


def run_pipeline(
    metod_id: str,
    images_dir: Path,
    chunks_base_dir: Path,
    output_dir: Path,
    top_k: int,
    strategies: tuple[str, ...],
    dry_run: bool,
    eval_labels_path: Path | None,
) -> None:
    validation = validate_inputs(images_dir, chunks_base_dir, strategies, dry_run, eval_labels_path)
    if dry_run:
        print("Dry run OK")
        print("Images:", validation["image_count"])
        print("Chunk counts:", validation["chunk_counts"])
        print("Eval labels:", validation["eval_labels_count"])
        return

    client = require_azure_client()
    embedding_model_name, embedding_deployment, chat_model_name, vision_deployment = resolve_deployments()

    output_dir.mkdir(parents=True, exist_ok=True)
    images = list_images(images_dir)
    image_descriptions = []
    image_query_rows = []
    results = []
    labels_by_image = load_eval_labels(eval_labels_path)

    embeddings_by_strategy = {}
    for strategy in strategies:
        chunks = read_jsonl(chunk_file_for_strategy(chunks_base_dir, strategy))
        embedding_path = embedding_file_for_strategy(chunks_base_dir, strategy)
        existing_embeddings = read_jsonl(embedding_path) if embedding_path.exists() else []
        chunk_embeddings = build_chunk_embedding_rows(client, chunks, embedding_deployment, existing_embeddings)
        write_jsonl(embedding_path, chunk_embeddings)
        embeddings_by_strategy[strategy] = chunk_embeddings

    for image_path in images:
        description = describe_image(client, image_path, vision_deployment, metod_id)
        query_text = normalize_image_description(description)
        query_embedding = get_embedding(client, query_text, embedding_deployment)

        image_descriptions.append(description)
        image_query_rows.append(
            {
                "image_name": image_path.name,
                "image_path": str(image_path),
                "image_sha256": description["image_sha256"],
                "query_text": query_text,
                "embedding_model": embedding_deployment,
                "embedding": query_embedding,
            }
        )

        for strategy in strategies:
            retrieved = retrieve_top_k(query_embedding, embeddings_by_strategy[strategy], top_k)
            for rank, item in enumerate(retrieved, start=1):
                results.append(
                    {
                        "run_id": output_dir.name,
                        "metod_id": metod_id,
                        "image_name": image_path.name,
                        "image_sha256": description["image_sha256"],
                        "strategy": strategy,
                        "rank": rank,
                        **item,
                    }
                )

    write_jsonl(output_dir / "image_descriptions.jsonl", image_descriptions)
    write_jsonl(output_dir / "image_queries.jsonl", image_query_rows)
    write_jsonl(output_dir / "retrieval_results.jsonl", results)
    write_results_csv(output_dir / "retrieval_results.csv", results)
    evaluation_metrics = evaluate_retrieval(results, labels_by_image, top_k)
    results_by_strategy = group_results_by_strategy(results)
    observations = {}

    for strategy in strategies:
        observation = generate_observation_for_strategy(
            client=client,
            chat_deployment=vision_deployment,
            metod_id=metod_id,
            strategy=strategy,
            image_descriptions=image_descriptions,
            retrieved_rows=results_by_strategy.get(strategy, []),
        )
        observations[strategy] = observation
        write_json(output_dir / f"observation_{strategy}.json", observation)
        (output_dir / f"observation_{strategy}.md").write_text(
            observation_to_markdown(observation),
            encoding="utf-8",
        )

    observation_comparison = compare_observations_from_metrics(evaluation_metrics, top_k)
    observation_comparison["observations"] = {
        strategy: {
            "criticality": observation.get("criticality"),
            "source_count": len(observation.get("sources", [])),
            "missing_information_count": len(observation.get("missing_information", [])),
            "images_with_retrieved_chunks": len(
                {
                    row["image_name"]
                    for row in results_by_strategy.get(strategy, [])
                    if row.get("rank", 0) <= top_k
                }
            ),
        }
        for strategy, observation in observations.items()
    }

    retrieval_summary = {
        "metod_id": metod_id,
        "image_count": len(images),
        "top_k": top_k,
        "strategies": list(strategies),
        "embedding_deployment": embedding_deployment,
        "embedding_model_name": embedding_model_name,
        "vision_deployment": vision_deployment,
        "vision_model_name": chat_model_name,
        "summary_by_strategy": summarize_retrieval(results),
        "evaluation": evaluation_metrics,
        "observation_comparison": observation_comparison,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_dir / "retrieval_summary.json", retrieval_summary)
    write_json(output_dir / "evaluation_metrics.json", evaluation_metrics)
    write_json(output_dir / "observation_comparison.json", observation_comparison)

    print("Images processed:", len(images))
    print("Results:", len(results))
    print("Output:", output_dir)


def main(
    metod_id: str = "METOD5",
    top_k: int = 5,
    strategies: tuple[str, ...] = DEFAULT_STRATEGIES,
    dry_run: bool = False,
    images_dir: str | Path | None = None,
    chunks_base_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    eval_labels_path: str | Path | None = None,
) -> None:
    strategies = tuple(strategies)
    unsupported = sorted(set(strategies) - set(DEFAULT_STRATEGIES))
    if unsupported:
        raise ValueError(f"Unsupported strategies: {unsupported}. Expected one of: {DEFAULT_STRATEGIES}")

    run_id = utc_run_id()
    resolved_images_dir = Path(images_dir) if images_dir else PROJECT_ROOT / "inputs" / metod_id
    resolved_chunks_base_dir = Path(chunks_base_dir) if chunks_base_dir else OUTPUT_DIR
    resolved_output_dir = (
        Path(output_dir)
        if output_dir
        else PROJECT_ROOT / "rag_outputs" / metod_id / run_id
    )
    resolved_eval_labels_path = (
        Path(eval_labels_path)
        if eval_labels_path
        else PROJECT_ROOT / "eval" / "golden_labels.jsonl"
    )

    run_pipeline(
        metod_id=metod_id,
        images_dir=resolved_images_dir,
        chunks_base_dir=resolved_chunks_base_dir,
        output_dir=resolved_output_dir,
        top_k=top_k,
        strategies=strategies,
        dry_run=dry_run,
        eval_labels_path=resolved_eval_labels_path,
    )


if __name__ == "__main__":
    main()

