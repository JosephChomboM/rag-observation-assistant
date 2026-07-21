# Databricks notebook source
# MAGIC %pip install openai openpyxl python-docx beautifulsoup4 pypdf

# COMMAND ----------

"""
User notebook: generate one consolidated observation per prueba.

The user selects a METOD and uploads METOD evidence into:
/Workspace/Users/<user>/softia_mvp/inputs/<METOD>/

Shared variable configuration and model context go into:
/Workspace/Users/<user>/softia_mvp/inputs/_global/

The notebook reads admin-managed knowledge from:
/dbfs/FileStore/softia_mvp/knowledge/<METOD>/
"""

# COMMAND ----------

import json
import os
import sys
from dataclasses import replace

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


load_dotenv_if_exists()

DEFAULT_DATABRICKS_EMBEDDING_ENDPOINT = os.getenv(
    "DEPLOYMENT_EMB_DATABRICKS",
    "databricks-qwen3-embedding-0-6b",
)
DEFAULT_DATABRICKS_CHAT_ENDPOINT = os.getenv(
    "MODEL_NAME_DATABRICKS",
    "databricks-claude-haiku-4-5",
)
DEFAULT_AZURE_EMBEDDING_DEPLOYMENT = os.getenv(
    "DEPLOYMENT_EMB_SMALL",
    "text-embedding-3-small",
)
DEFAULT_AZURE_CHAT_DEPLOYMENT = os.getenv(
    "DEPLOYMENT_AZURE",
    "gpt-4o-mini",
)

try:
    dbutils.widgets.text("metod_id", "BBDD1", "METOD")
    dbutils.widgets.dropdown("provider", "databricks", ["databricks", "azure"], "Model provider")
    dbutils.widgets.text(
        "databricks_embedding_endpoint",
        DEFAULT_DATABRICKS_EMBEDDING_ENDPOINT,
        "Databricks embedding endpoint",
    )
    dbutils.widgets.text(
        "databricks_chat_endpoint",
        DEFAULT_DATABRICKS_CHAT_ENDPOINT,
        "Databricks chat endpoint",
    )
    dbutils.widgets.text("azure_embedding_deployment", DEFAULT_AZURE_EMBEDDING_DEPLOYMENT, "Azure embedding deployment")
    dbutils.widgets.text("azure_chat_deployment", DEFAULT_AZURE_CHAT_DEPLOYMENT, "Azure chat deployment")
    dbutils.widgets.dropdown("rebuild_evidence_index", "false", ["false", "true"], "Rebuild input indexes")
    dbutils.widgets.text("top_k_evidence", "8", "Top K evidence")
    dbutils.widgets.text("top_k_global_context", "4", "Top K global context")
    dbutils.widgets.text("top_k_glossary", "5", "Top K glossary")
    dbutils.widgets.text("max_prompt_images", "0", "Max prompt images por prueba")
    dbutils.widgets.dropdown("run_mode", "full", ["full", "prueba_unica"], "Run mode")
    dbutils.widgets.text("prueba_id", "", "Prueba ID opcional")
    dbutils.widgets.text(
        "workspace_base_dir",
        os.getenv("SOFTIA_WORKSPACE_BASE_DIR", ""),
        "Workspace base dir opcional",
    )
    dbutils.widgets.text(
        "knowledge_base_dir",
        os.getenv("SOFTIA_KNOWLEDGE_BASE_DIR", "/dbfs/FileStore/softia_mvp/knowledge"),
        "Knowledge base dir",
    )
except NameError:
    pass


def get_widget(name: str, default: str = "") -> str:
    try:
        return dbutils.widgets.get(name).strip()
    except NameError:
        return os.getenv(name.upper(), default).strip()


repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from metod_observations.config import load_config  # noqa: E402
from metod_observations.pipeline import run_observation_pipeline  # noqa: E402

# COMMAND ----------

base_config = load_config()
workspace_base_dir = get_widget("workspace_base_dir") or base_config.workspace_base_dir
knowledge_base_dir = get_widget("knowledge_base_dir") or base_config.knowledge_base_dir
provider = get_widget("provider", "databricks").lower()

if provider == "databricks":
    embedding_provider = "databricks"
    chat_provider = "databricks"
    embedding_deployment = get_widget(
        "databricks_embedding_endpoint",
        DEFAULT_DATABRICKS_EMBEDDING_ENDPOINT,
    )
    chat_deployment = get_widget(
        "databricks_chat_endpoint",
        DEFAULT_DATABRICKS_CHAT_ENDPOINT,
    )
else:
    embedding_provider = "azure"
    chat_provider = "azure"
    embedding_deployment = get_widget("azure_embedding_deployment", DEFAULT_AZURE_EMBEDDING_DEPLOYMENT)
    chat_deployment = get_widget("azure_chat_deployment", DEFAULT_AZURE_CHAT_DEPLOYMENT)

config = replace(
    base_config,
    workspace_base_dir=workspace_base_dir,
    knowledge_base_dir=knowledge_base_dir,
    inputs_base_dir=os.path.join(workspace_base_dir, "inputs"),
    indexes_base_dir=os.path.join(workspace_base_dir, "indexes"),
    outputs_base_dir=os.path.join(workspace_base_dir, "outputs", "generated_observations"),
    embedding_provider=embedding_provider,
    chat_provider=chat_provider,
    embedding_deployment=embedding_deployment,
    chat_deployment=chat_deployment,
    top_k_evidence=int(get_widget("top_k_evidence", "8")),
    top_k_global_context=int(get_widget("top_k_global_context", "4")),
    top_k_glossary=int(get_widget("top_k_glossary", "5")),
    max_prompt_images=int(get_widget("max_prompt_images", "0")),
)

metod_id = get_widget("metod_id", "BBDD1").upper()
rebuild_evidence_index = get_widget("rebuild_evidence_index", "false").lower() == "true"
run_mode = get_widget("run_mode", "full")
prueba_id = get_widget("prueba_id") or None

print("METOD:", metod_id)
print("Workspace base:", config.workspace_base_dir)
print("Knowledge base:", config.knowledge_base_dir)
print("METOD evidence input:", os.path.join(config.inputs_base_dir, metod_id))
print("Global context input:", os.path.join(config.inputs_base_dir, "_global"))
print("Provider:", provider)
print("Embedding endpoint/deployment:", config.embedding_deployment)
print("Chat endpoint/deployment:", config.chat_deployment)
print("Run mode:", run_mode)
print("Prueba ID:", prueba_id or "all")
print("Top K evidence:", config.top_k_evidence)
print("Top K glossary:", config.top_k_glossary)
print("Top K global context:", config.top_k_global_context)
print("Max prompt images:", config.max_prompt_images)

# COMMAND ----------

result = run_observation_pipeline(
    metod_id=metod_id,
    config=config,
    rebuild_evidence_index=rebuild_evidence_index,
    run_mode=run_mode,
    prueba_id=prueba_id,
)

print("Run completed.")
print(json.dumps(result["usage_summary"], ensure_ascii=False, indent=2))
print(json.dumps(result["output_paths"], ensure_ascii=False, indent=2))

# COMMAND ----------

try:
    display(
        [
            {
                "prueba_id": row["prueba_id"],
                "nombre_prueba": row["nombre_prueba"],
                "hay_observacion": row["hay_observacion"],
                "criticidad": row["criticidad"],
                "observacion": row["observacion"][:250],
            }
            for row in result["observations"]
        ]
    )
except NameError:
    print(json.dumps(result["observations"], ensure_ascii=False, indent=2))

