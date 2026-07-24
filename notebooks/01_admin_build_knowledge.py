# Databricks notebook source
# MAGIC %pip install --upgrade openai pydantic python-dotenv truststore openpyxl

# COMMAND ----------

"""
Admin notebook: build METOD knowledge from the Excel source of truth.

Only admins should run this notebook. It converts each Excel sheet into:
- one markdown per prueba under knowledge/<METOD>/pruebas/
- one manifest.json under knowledge/<METOD>/
- prueba profile embeddings under knowledge/_indexes/<METOD>/
- glossary embeddings under knowledge/_indexes/_shared/

In production, SOFTIA_KNOWLEDGE_BASE_DIR should point to:
/dbfs/FileStore/gestor_obs/knowledge
"""

# COMMAND ----------

import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import truststore
from dotenv import load_dotenv


def find_repo_root() -> str:
    starts = [Path.cwd()]
    if "__file__" in globals():
        starts.append(Path(__file__).resolve().parent)
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / "metod_observations").is_dir():
                return str(candidate)
    raise FileNotFoundError("No se encontro la raiz del repositorio.")


repo_root = find_repo_root()
load_dotenv(os.path.join(repo_root, ".env"), override=True)
truststore.inject_into_ssl()


try:
    dbutils.widgets.text("excel_path", "", "Excel maestro")
    dbutils.widgets.text("sheet_name", "", "Hoja opcional")
    dbutils.widgets.dropdown("rebuild_embeddings", "false", ["false", "true"], "Rebuild embeddings")
    dbutils.widgets.text(
        "knowledge_base_dir",
        os.getenv("SOFTIA_KNOWLEDGE_BASE_DIR", "/dbfs/FileStore/gestor_obs/knowledge"),
        "Knowledge base dir",
    )
except NameError:
    pass


def get_widget(name: str, default: str = "") -> str:
    try:
        return dbutils.widgets.get(name).strip()
    except NameError:
        return os.getenv(name.upper(), default).strip()


if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from metod_observations.config import load_config  # noqa: E402
from metod_observations.pipeline import build_admin_assets  # noqa: E402

# COMMAND ----------

excel_path = get_widget("excel_path")
sheet_name = get_widget("sheet_name") or None
knowledge_base_dir = get_widget("knowledge_base_dir")

if not excel_path:
    raise ValueError("Set widget excel_path with the admin Excel file path.")

config = replace(
    load_config(os.path.join(repo_root, ".env")),
    knowledge_base_dir=knowledge_base_dir,
)
rebuild_embeddings = get_widget("rebuild_embeddings", "false").lower() == "true"

print("Excel:", excel_path)
print("Sheet:", sheet_name or "all")
print("Knowledge base:", config.knowledge_base_dir)

# COMMAND ----------

print("Embedding deployment:", config.embedding_deployment)
print("Rebuild embeddings:", rebuild_embeddings)
result = build_admin_assets(
    excel_path=excel_path,
    knowledge_base_dir=config.knowledge_base_dir,
    sheet_name=sheet_name,
    rebuild_embeddings=rebuild_embeddings,
    config=config,
)
manifests = result["manifests"]

for metod_id, manifest in manifests.items():
    print(
        f"{metod_id}: pruebas={manifest['pruebas_count']} "
        f"controles={manifest['controls_count']} "
        f"source={manifest['source_file']}"
    )

print(json.dumps(result["embedding_summary"], ensure_ascii=False, indent=2))

print("Admin knowledge build completed.")
