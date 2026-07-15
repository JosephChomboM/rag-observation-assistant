# Databricks notebook source
# MAGIC %pip install openai

# COMMAND ----------

"""
Provider comparison notebook for METOD RAG experiments.

Compares the current Azure AI Foundry / Azure OpenAI setup against Databricks
Model Serving using the same inputs, chunks, retrieval logic, allocation
profiles, and observation prompt.
"""

# COMMAND ----------

import base64
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# COMMAND ----------

# ============================================================
# WIDGETS
# ============================================================

try:
    for stale_widget in ["strategies", "allocation_profiles"]:
        try:
            dbutils.widgets.remove(stale_widget)
        except Exception:
            pass


    dbutils.widgets.text("chunking_dir", "", "Chunking experiment dir")
    dbutils.widgets.text("metod_id", "METOD5", "METOD")
    dbutils.widgets.dropdown("dry_run", "true", ["true", "false"], "Dry run")
    dbutils.widgets.text("providers", "azure_ai_foundry,databricks_model_serving", "Providers")
    dbutils.widgets.text("inputs_dir", "", "Inputs dir")
    dbutils.widgets.text("chunks_base_dir", "", "Chunks base dir")
    dbutils.widgets.text("output_dir", "", "Output dir")
    dbutils.widgets.dropdown("include_images_in_observation", "true", ["true", "false"], "Attach images")
    dbutils.widgets.dropdown("image_detail", "low", ["low", "high", "auto"], "Image detail")
except NameError:
    dbutils = None


def get_widget(name: str, default: str) -> str:
    if dbutils is None:
        return os.getenv(name.upper(), default)
    value = dbutils.widgets.get(name).strip()
    return value or default


def parse_csv_widget(name: str, default: str) -> list[str]:
    return [item.strip() for item in get_widget(name, default).split(",") if item.strip()]


METOD_ID = get_widget("metod_id", "METOD5").upper()
DRY_RUN = get_widget("dry_run", "true").lower() == "true"
PROVIDERS = parse_csv_widget("providers", "azure_ai_foundry,databricks_model_serving")
KNOWLEDGE_STRATEGY = "dynamic"
CONTEXT_PROFILE = "dynamic_top_7"
CONTEXT_TOP_K = 7

INCLUDE_IMAGES_IN_OBSERVATION = get_widget("include_images_in_observation", "true").lower() == "true"
IMAGE_DETAIL = get_widget("image_detail", "low")

raw_chunking_dir = get_widget("chunking_dir", "")
if raw_chunking_dir:
    CHUNKING_DIR = Path(raw_chunking_dir)
elif "__file__" in globals():
    CHUNKING_DIR = Path(__file__).resolve().parents[1]
else:
    CHUNKING_DIR = Path.cwd()

if str(CHUNKING_DIR) not in sys.path:
    sys.path.append(str(CHUNKING_DIR))

from io_utils import read_text, write_json, write_jsonl  # noqa: E402
from rag_chunking_pipeline import (  # noqa: E402
    chunk_file_for_strategy,
    image_to_base64_data_url,
    list_images,
    read_jsonl,
    retrieve_top_k,
)
from modality_allocation_pipeline import list_text_files, normalize_text_query  # noqa: E402

INPUTS_DIR = Path(get_widget("inputs_dir", "")) if get_widget("inputs_dir", "") else CHUNKING_DIR / "inputs" / METOD_ID
CHUNKS_BASE_DIR = Path(get_widget("chunks_base_dir", "")) if get_widget("chunks_base_dir", "") else CHUNKING_DIR / "outputs"
RUN_ID = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
OUTPUT_DIR = Path(get_widget("output_dir", "")) if get_widget("output_dir", "") else CHUNKING_DIR / "provider_comparison_outputs" / METOD_ID / RUN_ID

print("METOD:", METOD_ID)
print("Dry run:", DRY_RUN)
print("Providers:", PROVIDERS)
print("Knowledge strategy:", KNOWLEDGE_STRATEGY)
print("Context profile:", CONTEXT_PROFILE)
print("Context top k:", CONTEXT_TOP_K)
print("Inputs dir:", INPUTS_DIR)
print("Chunks base dir:", CHUNKS_BASE_DIR)
print("Output dir:", OUTPUT_DIR)

# COMMAND ----------

# ============================================================
# PROVIDER CONFIGURATION
# ============================================================

DEFAULT_DATABRICKS_EMBEDDING_ENDPOINT = "databricks-qwen3-embedding-0-6b"
DEFAULT_DATABRICKS_CHAT_ENDPOINT = "databricks-claude-haiku-4-5"


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def azure_config() -> dict[str, Any]:
    from openai import AzureOpenAI

    embedding_model = os.getenv("MODEL_NAME_EMB_SMALL", "text-embedding-3-small").strip()
    embedding_deployment = (
        os.getenv("DEPLOYMENT_EMB_SMALL")
        or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or embedding_model
    ).strip()
    chat_model = os.getenv("MODEL_NAME_GPT4", "gpt-4o").strip()
    chat_deployment = (
        os.getenv("DEPLOYMENT_GPT4")
        or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        or chat_model
    ).strip()

    return {
        "provider": "azure_ai_foundry",
        "client": AzureOpenAI(
            azure_endpoint=require_env("AZURE_OPENAI_ENDPOINT"),
            api_key=require_env("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        ),
        "embedding_model_name": embedding_model,
        "embedding_endpoint": embedding_deployment,
        "chat_model_name": chat_model,
        "chat_endpoint": chat_deployment,
    }


def databricks_config() -> dict[str, Any]:
    import mlflow.deployments

    embedding_endpoint = os.getenv(
        "DATABRICKS_EMBEDDING_ENDPOINT",
        DEFAULT_DATABRICKS_EMBEDDING_ENDPOINT,
    ).strip()
    chat_endpoint = os.getenv(
        "DATABRICKS_CHAT_ENDPOINT",
        DEFAULT_DATABRICKS_CHAT_ENDPOINT,
    ).strip()

    return {
        "provider": "databricks_model_serving",
        "client": mlflow.deployments.get_deploy_client("databricks"),
        "embedding_model_name": embedding_endpoint,
        "embedding_endpoint": embedding_endpoint,
        "chat_model_name": chat_endpoint,
        "chat_endpoint": chat_endpoint,
    }


def provider_config(provider: str) -> dict[str, Any]:
    if provider == "azure_ai_foundry":
        return azure_config()
    if provider == "databricks_model_serving":
        return databricks_config()
    raise ValueError(f"Unsupported provider: {provider}")

# COMMAND ----------

# ============================================================
# API CALL HELPERS
# ============================================================


def response_usage(response: Any) -> dict[str, int]:
    if isinstance(response, dict):
        usage = response.get("usage", {}) or {}
        return {key: int(usage.get(key, 0) or 0) for key in ["prompt_tokens", "completion_tokens", "total_tokens"]}

    usage = getattr(response, "usage", None)
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def record_call(call_log: list[dict], provider: str, task: str, endpoint: str, started_at: float, response: Any, error: Exception | None = None) -> None:
    call_log.append(
        {
            "provider": provider,
            "task": task,
            "endpoint": endpoint,
            "duration_seconds": round(time.perf_counter() - started_at, 4),
            "usage": response_usage(response) if error is None else {},
            "error": str(error) if error else None,
        }
    )


def embedding_from_response(response: Any) -> list[float]:
    if isinstance(response, dict):
        return response["data"][0]["embedding"]
    return response.data[0].embedding


def text_from_chat_response(response: Any) -> str:
    if isinstance(response, dict):
        return (response["choices"][0]["message"].get("content") or "").strip()
    return (response.choices[0].message.content or "").strip()


def embed_text(config: dict[str, Any], text: str, call_log: list[dict]) -> list[float]:
    provider = config["provider"]
    endpoint = config["embedding_endpoint"]
    started_at = time.perf_counter()
    try:
        if provider == "azure_ai_foundry":
            response = config["client"].embeddings.create(model=endpoint, input=text)
        else:
            response = config["client"].predict(endpoint=endpoint, inputs={"input": text})
        record_call(call_log, provider, "embedding", endpoint, started_at, response)
        return embedding_from_response(response)
    except Exception as error:
        record_call(call_log, provider, "embedding", endpoint, started_at, {}, error)
        raise


def chat_completion(config: dict[str, Any], messages: list[dict], call_log: list[dict], temperature: float = 0.1, max_tokens: int = 1600) -> str:
    provider = config["provider"]
    endpoint = config["chat_endpoint"]
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    started_at = time.perf_counter()
    try:
        if provider == "azure_ai_foundry":
            response = config["client"].chat.completions.create(model=endpoint, **payload)
        else:
            response = config["client"].predict(endpoint=endpoint, inputs=payload)
        record_call(call_log, provider, "chat", endpoint, started_at, response)
        return text_from_chat_response(response)
    except Exception as error:
        record_call(call_log, provider, "chat", endpoint, started_at, {}, error)
        raise

# COMMAND ----------

# ============================================================
# INPUTS AND EMBEDDINGS
# ============================================================

TEXT_EXTENSIONS = {".txt", ".md"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_inputs() -> dict[str, Any]:
    image_files = list_images(INPUTS_DIR)
    text_files = list_text_files(INPUTS_DIR)
    chunk_path = chunk_file_for_strategy(CHUNKS_BASE_DIR, KNOWLEDGE_STRATEGY)
    chunks = read_jsonl(chunk_path)
    if not chunks:
        raise ValueError(f"No chunks found for {KNOWLEDGE_STRATEGY}: {chunk_path}")

    return {
        "images": len(image_files),
        "text_files": len(text_files),
        "knowledge_strategy": KNOWLEDGE_STRATEGY,
        "context_profile": CONTEXT_PROFILE,
        "context_top_k": CONTEXT_TOP_K,
        "chunk_count": len(chunks),
    }


def build_text_items() -> list[dict]:
    items = []
    for path in list_text_files(INPUTS_DIR):
        text = read_text(path)
        if not text.strip():
            continue
        items.append(
            {
                "input_name": path.name,
                "relative_input_path": path.relative_to(INPUTS_DIR).as_posix(),
                "input_path": str(path),
                "input_sha256": file_sha256(path),
                "modality": "text",
                "query_text": normalize_text_query(text),
                "summary": normalize_text_query(text, max_chars=1200),
            }
        )
    return items


def describe_image(config: dict[str, Any], image_path: Path, call_log: list[dict]) -> dict:
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    image_data_url = image_to_base64_data_url(image_path)
    prompt = f"""
Describe esta imagen como evidencia de validacion de modelos para {METOD_ID}.
Extrae solo valores visibles, metricas, alertas, tablas y senales metodologicas.
No inventes valores. Devuelve JSON valido con estas llaves:
summary, visible_metrics, methodology_signals, possible_queries.
""".strip()
    raw_text = chat_completion(
        config,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url, "detail": IMAGE_DETAIL}},
                ],
            }
        ],
        call_log=call_log,
        temperature=0.0,
        max_tokens=1200,
    )
    try:
        parsed = json.loads(raw_text.removeprefix("```json").removesuffix("```").strip())
    except json.JSONDecodeError:
        parsed = {
            "summary": raw_text,
            "visible_metrics": [],
            "methodology_signals": [],
            "possible_queries": [],
        }
    parsed["input_name"] = image_path.name
    parsed["image_sha256"] = file_sha256(image_path)
    return parsed


def build_image_items(config: dict[str, Any], call_log: list[dict]) -> tuple[list[dict], list[dict]]:
    items = []
    descriptions = []
    for path in list_images(INPUTS_DIR):
        description = describe_image(config, path, call_log)
        query_text = json.dumps(
            {
                "summary": description.get("summary", ""),
                "visible_metrics": description.get("visible_metrics", []),
                "methodology_signals": description.get("methodology_signals", []),
                "possible_queries": description.get("possible_queries", []),
            },
            ensure_ascii=False,
        )
        items.append(
            {
                "input_name": path.name,
                "relative_input_path": path.relative_to(INPUTS_DIR).as_posix(),
                "input_path": str(path),
                "input_sha256": description["image_sha256"],
                "modality": "image",
                "query_text": query_text,
                "summary": description.get("summary", ""),
            }
        )
        descriptions.append(description)
    return items, descriptions


def build_input_embeddings(config: dict[str, Any], input_items: list[dict], call_log: list[dict]) -> list[dict]:
    rows = []
    for item in input_items:
        rows.append(
            {
                **item,
                "query_text_sha256": hashlib.sha256(item["query_text"].encode("utf-8")).hexdigest(),
                "embedding_model": config["embedding_endpoint"],
                "embedding": embed_text(config, item["query_text"], call_log),
            }
        )
    return rows


def load_or_create_chunk_embeddings(config: dict[str, Any], strategy: str, output_dir: Path, call_log: list[dict]) -> list[dict]:
    chunk_path = chunk_file_for_strategy(CHUNKS_BASE_DIR, strategy)
    chunks = read_jsonl(chunk_path)
    cache_path = output_dir / "chunk_embeddings" / f"chunks_{strategy}_embeddings.jsonl"
    existing = read_jsonl(cache_path) if cache_path.exists() else []
    existing_by_id = {
        row["chunk_id"]: row
        for row in existing
        if row.get("chunk_id")
        and row.get("text_sha256")
        and row.get("embedding")
        and row.get("embedding_model") == config["embedding_endpoint"]
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
                "embedding_model": config["embedding_endpoint"],
                "embedding": embed_text(config, text, call_log),
                "chunk": chunk,
            }
        )
        if index % 10 == 0:
            print(f"{config['provider']} embedded {strategy} chunks: {index}/{len(chunks)}")

    write_jsonl(cache_path, rows)
    return rows

# COMMAND ----------

# ============================================================
# RETRIEVAL AND OBSERVATIONS
# ============================================================


def retrieve_for_inputs(input_embedding_rows: list[dict], chunk_embedding_rows: list[dict], strategy: str, max_k: int, run_id: str) -> list[dict]:
    rows = []
    for input_row in input_embedding_rows:
        retrieved = retrieve_top_k(input_row["embedding"], chunk_embedding_rows, max_k)
        for rank, item in enumerate(retrieved, start=1):
            rows.append(
                {
                    "run_id": run_id,
                    "metod_id": METOD_ID,
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


def select_top_context_rows(rows: list[dict]) -> list[dict]:
    sorted_rows = sorted(rows, key=lambda item: item["score"], reverse=True)
    selected = sorted_rows[:CONTEXT_TOP_K]
    return [
        {
            **row,
            "context_profile": CONTEXT_PROFILE,
            "allocation_rank": rank,
        }
        for rank, row in enumerate(selected, start=1)
    ]


def summarize_context_rows(rows: list[dict]) -> dict:
    scores = [row["score"] for row in rows]
    return {
        "context_profile": CONTEXT_PROFILE,
        "knowledge_strategy": KNOWLEDGE_STRATEGY,
        "selected_chunks": len(rows),
        "text_query_chunks": sum(1 for row in rows if row["modality"] == "text"),
        "image_query_chunks": sum(1 for row in rows if row["modality"] == "image"),
        "unique_inputs": len({row["input_name"] for row in rows}),
        "unique_knowledge_chunks": len({row["chunk_id"] for row in rows}),
        "unique_knowledge_sources": len({row["relative_path"] for row in rows}),
        "avg_score": round(sum(scores) / len(scores), 6) if scores else 0,
        "min_score": round(min(scores), 6) if scores else 0,
        "max_score": round(max(scores), 6) if scores else 0,
        "selection_rule": "top_7_global_over_dynamic_chunks",
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


def observation_image_parts(input_items: list[dict]) -> list[dict]:
    parts = []
    for item in input_items:
        if item.get("modality") != "image":
            continue
        image_path = Path(item["input_path"])
        parts.extend(
            [
                {"type": "text", "text": f"Imagen original para analisis visual: {item['input_name']}"},
                {"type": "image_url", "image_url": {"url": image_to_base64_data_url(image_path), "detail": IMAGE_DETAIL}},
            ]
        )
    return parts


def fix_mojibake(value: Any) -> Any:
    if isinstance(value, str):
        if "Ã" in value or "Â" in value:
            try:
                return value.encode("latin1").decode("utf-8")
            except UnicodeError:
                return value
        return value
    if isinstance(value, list):
        return [fix_mojibake(item) for item in value]
    if isinstance(value, dict):
        return {key: fix_mojibake(item) for key, item in value.items()}
    return value


def strip_json_fence(text: str) -> str:
    clean_text = text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()
    return clean_text


def extract_complete_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def extract_json_string_field(text: str, field_name: str) -> str:
    pattern = rf'"{re.escape(field_name)}"\s*:\s*"((?:\\.|[^"\\])*)"'
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return ""
    try:
        return json.loads('"' + match.group(1) + '"')
    except json.JSONDecodeError:
        return match.group(1)


def salvage_observation(raw_text: str, strategy: str, context_profile: str) -> dict:
    fields = {
        "criticality": extract_json_string_field(raw_text, "criticality") or "Media",
        "observation": extract_json_string_field(raw_text, "observation"),
        "evidence": extract_json_string_field(raw_text, "evidence"),
        "risk": extract_json_string_field(raw_text, "risk"),
        "action_plan": extract_json_string_field(raw_text, "action_plan"),
        "context_assessment": extract_json_string_field(raw_text, "context_assessment"),
    }
    if not any(fields[key] for key in ["observation", "evidence", "risk", "action_plan"]):
        fields["observation"] = "The model response was not valid JSON and no usable field could be recovered."

    if not fields["context_assessment"]:
        fields["context_assessment"] = "The model response was not valid JSON; usable fields were recovered from the raw response."

    return fix_mojibake(
        {
            "metod_id": METOD_ID,
            "knowledge_strategy": strategy,
            "context_profile": context_profile,
            **fields,
            "missing_information": ["Model response was not valid JSON; review llm_call_log.jsonl if exact raw output is needed."],
            "sources": [],
            "parse_status": "recovered_from_invalid_json",
        }
    )


def parse_observation_json(raw_text: str, strategy: str, context_profile: str) -> dict:
    clean_text = strip_json_fence(fix_mojibake(raw_text))
    candidates = [extract_complete_json_object(clean_text), clean_text]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                parsed.setdefault("metod_id", METOD_ID)
                parsed.setdefault("knowledge_strategy", strategy)
                parsed.setdefault("context_profile", context_profile)
                parsed.setdefault("missing_information", [])
                parsed.setdefault("sources", [])
                parsed["parse_status"] = "valid_json"
                return fix_mojibake(parsed)
        except json.JSONDecodeError:
            continue

    return salvage_observation(clean_text, strategy, context_profile)

def generate_observation(config: dict[str, Any], input_items: list[dict], selected_rows: list[dict], strategy: str, context_profile: str, call_log: list[dict]) -> dict:
    payload = {
        "metod_id": METOD_ID,
        "provider": config["provider"],
        "knowledge_chunking_strategy": strategy,
        "context_profile": context_profile,
        "selection_rule": "top_7_global_over_dynamic_chunks",
        "image_inputs_attached_to_prompt": INCLUDE_IMAGES_IN_OBSERVATION,
        "input_evidence": compact_input_evidence(input_items),
        "selected_knowledge_chunks": compact_selected_chunks(selected_rows),
    }

    prompt = f"""
Eres un revisor senior de validacion de modelos del BCP.

Genera una observacion consolidada para METOD usando evidencia de entrada
multimodal y chunks de conocimiento recuperados.

Reglas:
- No inventes valores.
- Usa evidencia de texto e imagen cuando este disponible.
- Usa los chunks recuperados como criterio metodologico RAG, no como evidencia del modelo validado.
- Explica si el contexto recuperado fue suficiente o genero ruido.
- Cita las fuentes de conocimiento recuperadas.
- Devuelve solo JSON valido, sin Markdown y sin bloques de codigo.
- Mantén cada campo textual en máximo 900 caracteres.

Required JSON:
{{
  "metod_id": "{METOD_ID}",
  "knowledge_strategy": "{strategy}",
  "context_profile": "{context_profile}",
  "criticality": "Alta|Media|Baja|Sin observacion",
  "observation": "max 900 chars",
  "evidence": "max 900 chars",
  "risk": "max 700 chars",
  "action_plan": "max 900 chars",
  "context_assessment": "max 500 chars",
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
    if INCLUDE_IMAGES_IN_OBSERVATION:
        content.extend(observation_image_parts(input_items))

    raw_text = chat_completion(
        config,
        messages=[{"role": "user", "content": content}],
        call_log=call_log,
        temperature=0.1,
        max_tokens=2600,
    )
    return parse_observation_json(raw_text, strategy, context_profile)


def observation_to_markdown(observation: dict) -> str:
    sources = observation.get("sources", []) or []
    source_lines = [
        f"- {source.get('source_file', '')}: {source.get('reason_used', '')}"
        for source in sources
    ] or ["- None"]
    missing_lines = [f"- {item}" for item in observation.get("missing_information", [])] or ["- None"]
    return "\n".join(
        [
            f"# Observacion - {observation.get('knowledge_strategy', '')} / {observation.get('context_profile', '')}",
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
            "## Evaluacion del contexto",
            observation.get("context_assessment", ""),
            "",
            "## Informacion faltante",
            "\n".join(missing_lines),
            "",
            "## Fuentes",
            "\n".join(source_lines),
        ]
    )

# COMMAND ----------

# ============================================================
# RUNNER
# ============================================================


def usage_summary(config: dict[str, Any], call_log: list[dict]) -> dict:
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    by_task = {}
    for row in call_log:
        task_summary = by_task.setdefault(
            row["task"],
            {"calls": 0, "duration_seconds": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "errors": 0},
        )
        task_summary["calls"] += 1
        task_summary["duration_seconds"] += row["duration_seconds"]
        if row.get("error"):
            task_summary["errors"] += 1
        for key in totals:
            value = int((row.get("usage") or {}).get(key, 0) or 0)
            totals[key] += value
            task_summary[key] += value

    for task_summary in by_task.values():
        task_summary["duration_seconds"] = round(task_summary["duration_seconds"], 4)

    return {
        "provider": config["provider"],
        "embedding_model_name": config["embedding_model_name"],
        "embedding_endpoint": config["embedding_endpoint"],
        "chat_model_name": config["chat_model_name"],
        "chat_endpoint": config["chat_endpoint"],
        "calls": len(call_log),
        "duration_seconds": round(sum(row["duration_seconds"] for row in call_log), 4),
        "tokens": totals,
        "by_task": by_task,
    }


def run_provider(provider: str) -> dict:
    provider_output_dir = OUTPUT_DIR / provider
    provider_output_dir.mkdir(parents=True, exist_ok=True)

    if DRY_RUN:
        return {
            "provider": provider,
            "dry_run": True,
            "knowledge_strategy": KNOWLEDGE_STRATEGY,
            "context_profile": CONTEXT_PROFILE,
            "context_top_k": CONTEXT_TOP_K,
            "output_dir": str(provider_output_dir),
        }

    config = provider_config(provider)
    call_log = []
    text_items = build_text_items()
    image_items, image_descriptions = build_image_items(config, call_log)
    input_items = text_items + image_items
    if not input_items:
        raise ValueError(f"No input items found in: {INPUTS_DIR}")

    input_embeddings = build_input_embeddings(config, input_items, call_log)
    chunk_embeddings = load_or_create_chunk_embeddings(
        config,
        KNOWLEDGE_STRATEGY,
        provider_output_dir,
        call_log,
    )
    retrieval_rows = retrieve_for_inputs(
        input_embeddings,
        chunk_embeddings,
        KNOWLEDGE_STRATEGY,
        CONTEXT_TOP_K,
        RUN_ID,
    )
    selected_rows = select_top_context_rows(retrieval_rows)
    context_summary = summarize_context_rows(selected_rows)

    observation = generate_observation(
        config,
        input_items,
        selected_rows,
        KNOWLEDGE_STRATEGY,
        CONTEXT_PROFILE,
        call_log,
    )
    write_json(provider_output_dir / f"observation_{CONTEXT_PROFILE}.json", observation)
    (provider_output_dir / f"observation_{CONTEXT_PROFILE}.md").write_text(
        observation_to_markdown(observation),
        encoding="utf-8",
    )

    comparison = {
        "metod_id": METOD_ID,
        "run_id": RUN_ID,
        "provider": provider,
        "knowledge_strategy": KNOWLEDGE_STRATEGY,
        "context_profile": CONTEXT_PROFILE,
        "context_top_k": CONTEXT_TOP_K,
        "context_summary": context_summary,
        "decision_rule": "Compare the same dynamic_top_7 context across Azure and Databricks outputs.",
    }

    write_jsonl(provider_output_dir / "image_descriptions.jsonl", image_descriptions)
    write_jsonl(provider_output_dir / "input_items.jsonl", input_items)
    write_jsonl(provider_output_dir / "input_embeddings.jsonl", input_embeddings)
    write_jsonl(provider_output_dir / "retrieval_results_all.jsonl", retrieval_rows)
    write_jsonl(provider_output_dir / "retrieval_results_selected.jsonl", selected_rows)
    write_json(provider_output_dir / "context_metrics.json", context_summary)
    write_json(provider_output_dir / "context_comparison.json", comparison)
    write_json(
        provider_output_dir / "run_config.json",
        {**config, "client": str(type(config["client"])), "output_dir": str(provider_output_dir)},
    )
    write_jsonl(provider_output_dir / "llm_call_log.jsonl", call_log)
    summary = usage_summary(config, call_log)
    write_json(provider_output_dir / "llm_usage_summary.json", summary)
    summary["output_dir"] = str(provider_output_dir)
    summary["dry_run"] = False
    summary["knowledge_strategy"] = KNOWLEDGE_STRATEGY
    summary["context_profile"] = CONTEXT_PROFILE
    summary["context_top_k"] = CONTEXT_TOP_K
    return summary

def write_final_comparison(provider_summaries: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    comparison = {
        "metod_id": METOD_ID,
        "run_id": RUN_ID,
        "dry_run": DRY_RUN,
        "providers": provider_summaries,
        "decision_rubric": [
            "Grounding: relevant retrieved sources, low noise, and source diversity.",
            "Observation quality: valid JSON, specific evidence, actionable risk and action plan.",
            "Operations: latency, token usage, governance, authentication, and endpoint ownership.",
        ],
    }
    write_json(OUTPUT_DIR / "provider_comparison.json", comparison)
    (OUTPUT_DIR / "provider_comparison.md").write_text(
        "# Provider Comparison\n\n```json\n"
        + json.dumps(comparison, indent=2, ensure_ascii=False)
        + "\n```\n",
        encoding="utf-8",
    )


validation = validate_inputs()
print("Validation:", json.dumps(validation, indent=2, ensure_ascii=False))

provider_summaries = [run_provider(provider) for provider in PROVIDERS]
write_final_comparison(provider_summaries)
print("Provider comparison output:", OUTPUT_DIR)










