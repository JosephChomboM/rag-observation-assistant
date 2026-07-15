from __future__ import annotations

import os
from dataclasses import dataclass

from .schemas import VALID_CRITICALITIES


@dataclass(frozen=True)
class AppConfig:
    user_email: str
    workspace_base_dir: str
    knowledge_base_dir: str
    inputs_base_dir: str
    indexes_base_dir: str
    outputs_base_dir: str
    embedding_provider: str
    chat_provider: str
    embedding_deployment: str
    chat_deployment: str
    top_k_evidence: int = 8
    top_k_glossary: int = 5
    max_prompt_images: int = 2
    chunk_size: int = 1800
    chunk_overlap: int = 200


def load_dotenv_if_exists(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def first_env(names: list[str], default: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def resolve_embedding_deployment(provider: str) -> str:
    if provider == "databricks":
        return first_env(
            ["SOFTIA_EMBEDDING_ENDPOINT", "DEPLOYMENT_EMB_DATABRICKS"],
            "databricks-qwen3-embedding-0-6b",
        )
    return first_env(
        ["SOFTIA_EMBEDDING_ENDPOINT", "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "DEPLOYMENT_EMB_SMALL"],
        "text-embedding-3-small",
    )


def resolve_chat_deployment(provider: str) -> str:
    if provider == "databricks":
        return first_env(
            ["SOFTIA_CHAT_ENDPOINT", "MODEL_NAME_DATABRICKS", "DEPLOYMENT_CHAT_DATABRICKS"],
            "databricks-claude-haiku-4-5",
        )
    return first_env(
        ["SOFTIA_CHAT_ENDPOINT", "AZURE_OPENAI_CHAT_DEPLOYMENT", "DEPLOYMENT_AZURE", "DEPLOYMENT_GPT4"],
        "gpt-4o-mini",
    )


def load_config() -> AppConfig:
    load_dotenv_if_exists()
    user_email = os.getenv("SOFTIA_USER_EMAIL", "josephchombo@company.com").strip()
    workspace_base = os.getenv(
        "SOFTIA_WORKSPACE_BASE_DIR",
        f"/Workspace/Users/{user_email}/softia_mvp",
    ).strip()
    knowledge_base = os.getenv(
        "SOFTIA_KNOWLEDGE_BASE_DIR",
        "/dbfs/FileStore/softia_mvp/knowledge",
    ).strip()
    embedding_provider = os.getenv("SOFTIA_EMBEDDING_PROVIDER", "azure").strip().lower()
    chat_provider = os.getenv("SOFTIA_CHAT_PROVIDER", embedding_provider).strip().lower()

    return AppConfig(
        user_email=user_email,
        workspace_base_dir=workspace_base,
        knowledge_base_dir=knowledge_base,
        inputs_base_dir=os.path.join(workspace_base, "inputs"),
        indexes_base_dir=os.path.join(workspace_base, "indexes"),
        outputs_base_dir=os.path.join(workspace_base, "outputs", "generated_observations"),
        embedding_provider=embedding_provider,
        chat_provider=chat_provider,
        embedding_deployment=resolve_embedding_deployment(embedding_provider),
        chat_deployment=resolve_chat_deployment(chat_provider),
        top_k_evidence=int(os.getenv("SOFTIA_TOP_K_EVIDENCE", "8")),
        top_k_glossary=int(os.getenv("SOFTIA_TOP_K_GLOSSARY", "5")),
        max_prompt_images=int(os.getenv("SOFTIA_MAX_PROMPT_IMAGES", "2")),
        chunk_size=int(os.getenv("SOFTIA_CHUNK_SIZE", "1800")),
        chunk_overlap=int(os.getenv("SOFTIA_CHUNK_OVERLAP", "200")),
    )


def metod_paths(config: AppConfig, metod_id: str) -> dict[str, str]:
    clean_metod = metod_id.strip().upper()
    return {
        "knowledge_dir": os.path.join(config.knowledge_base_dir, clean_metod),
        "pruebas_dir": os.path.join(config.knowledge_base_dir, clean_metod, "pruebas"),
        "manifest_path": os.path.join(config.knowledge_base_dir, clean_metod, "manifest.json"),
        "input_dir": os.path.join(config.inputs_base_dir, clean_metod),
        "index_dir": os.path.join(config.indexes_base_dir, clean_metod),
        "evidence_index_path": os.path.join(
            config.indexes_base_dir,
            clean_metod,
            "evidence_chunks_embeddings.jsonl",
        ),
        "glossary_index_path": os.path.join(
            config.indexes_base_dir,
            clean_metod,
            "glossary_embeddings.jsonl",
        ),
        "profile_index_path": os.path.join(
            config.indexes_base_dir,
            clean_metod,
            "prueba_profile_embeddings.jsonl",
        ),
    }


CRITICALITY_ENUM_TEXT = ", ".join(sorted(VALID_CRITICALITIES))
