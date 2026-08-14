from __future__ import annotations

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    knowledge_base_dir: str
    inputs_base_dir: str
    indexes_base_dir: str
    outputs_base_dir: str
    embedding_deployment: str
    chat_deployment: str
    reasoning_effort: str = "high"
    top_k_evidence: int = 8
    top_k_global_context: int = 4
    top_k_glossary: int = 5
    max_prompt_files: int = 4
    max_prompt_images: int = 2
    chunk_size: int = 1800
    chunk_overlap: int = 200
    retrieval_mode: str = "hybrid"
    candidate_multiplier: int = 3
    enable_rerank: bool = False
    rerank_min_relevance: int = 1


def configure_runtime(env_path: str = ".env") -> None:
    import truststore
    from dotenv import load_dotenv

    load_dotenv(env_path, override=True)
    truststore.inject_into_ssl()


def resolve_embedding_deployment() -> str:
    return os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "").strip()


def resolve_chat_deployment() -> str:
    return os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "").strip()


def load_config(env_path: str = ".env") -> AppConfig:
    configure_runtime(env_path)
    knowledge_base = os.getenv(
        "SOFTIA_KNOWLEDGE_BASE_DIR",
        "/dbfs/FileStore/gestor_obs/knowledge",
    ).strip()
    reasoning_effort = os.getenv("SOFTIA_REASONING_EFFORT", "high").strip().lower()

    return AppConfig(
        knowledge_base_dir=knowledge_base,
        inputs_base_dir="",
        indexes_base_dir="",
        outputs_base_dir="",
        embedding_deployment=resolve_embedding_deployment(),
        chat_deployment=resolve_chat_deployment(),
        reasoning_effort=reasoning_effort,
        top_k_evidence=int(os.getenv("SOFTIA_TOP_K_EVIDENCE", "8")),
        top_k_global_context=int(os.getenv("SOFTIA_TOP_K_GLOBAL_CONTEXT", "4")),
        top_k_glossary=int(os.getenv("SOFTIA_TOP_K_GLOSSARY", "5")),
        max_prompt_files=int(os.getenv("SOFTIA_MAX_PROMPT_FILES", "4")),
        max_prompt_images=int(os.getenv("SOFTIA_MAX_PROMPT_IMAGES", "2")),
        chunk_size=int(os.getenv("SOFTIA_CHUNK_SIZE", "1800")),
        chunk_overlap=int(os.getenv("SOFTIA_CHUNK_OVERLAP", "200")),
        retrieval_mode=os.getenv("SOFTIA_RETRIEVAL_MODE", "hybrid").strip().lower(),
        candidate_multiplier=int(os.getenv("SOFTIA_CANDIDATE_MULTIPLIER", "3")),
        enable_rerank=os.getenv("SOFTIA_ENABLE_RERANK", "false").strip().lower() == "true",
        rerank_min_relevance=int(os.getenv("SOFTIA_RERANK_MIN_RELEVANCE", "1")),
    )


def metod_paths(config: AppConfig, metod_id: str) -> dict[str, str]:
    clean_metod = metod_id.strip().upper()
    return {
        "knowledge_dir": os.path.join(config.knowledge_base_dir, clean_metod),
        "pruebas_dir": os.path.join(config.knowledge_base_dir, clean_metod, "pruebas"),
        "manifest_path": os.path.join(config.knowledge_base_dir, clean_metod, "manifest.json"),
        "input_dir": os.path.join(config.inputs_base_dir, clean_metod),
        "global_input_dir": os.path.join(config.inputs_base_dir, "_global"),
        "index_dir": os.path.join(config.indexes_base_dir, clean_metod),
        "global_index_dir": os.path.join(config.indexes_base_dir, "_global"),
        "knowledge_index_dir": os.path.join(config.knowledge_base_dir, "_indexes", clean_metod),
        "shared_knowledge_index_dir": os.path.join(config.knowledge_base_dir, "_indexes", "_shared"),
        "evidence_index_path": os.path.join(
            config.indexes_base_dir,
            clean_metod,
            "evidence_chunks_embeddings.jsonl",
        ),
        "glossary_index_path": os.path.join(
            config.knowledge_base_dir,
            "_indexes",
            "_shared",
            "glossary_embeddings.jsonl",
        ),
        "profile_index_path": os.path.join(
            config.knowledge_base_dir,
            "_indexes",
            clean_metod,
            "control_profile_embeddings.jsonl",
        ),
        "global_context_index_path": os.path.join(
            config.indexes_base_dir,
            "_global",
            "global_context_embeddings.jsonl",
        ),
    }
