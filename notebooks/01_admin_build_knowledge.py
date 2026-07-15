# Databricks notebook source
# MAGIC %pip install openpyxl

# COMMAND ----------

"""
Admin notebook: build METOD knowledge from the Excel source of truth.

Only admins should run this notebook. It converts each Excel sheet into:
- one markdown per prueba under knowledge/<METOD>/pruebas/
- one manifest.json under knowledge/<METOD>/

In production, SOFTIA_KNOWLEDGE_BASE_DIR should point to:
/dbfs/FileStore/softia_mvp/knowledge
"""

# COMMAND ----------

import os
import sys
from dataclasses import replace

try:
    dbutils.widgets.text("excel_path", "", "Excel maestro")
    dbutils.widgets.text("sheet_name", "", "Hoja opcional")
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
from metod_observations.pipeline import build_admin_knowledge  # noqa: E402

# COMMAND ----------

excel_path = get_widget("excel_path")
sheet_name = get_widget("sheet_name") or None
knowledge_base_dir = get_widget("knowledge_base_dir")

if not excel_path:
    raise ValueError("Set widget excel_path with the admin Excel file path.")

config = replace(load_config(), knowledge_base_dir=knowledge_base_dir)

print("Excel:", excel_path)
print("Sheet:", sheet_name or "all")
print("Knowledge base:", config.knowledge_base_dir)

# COMMAND ----------

manifests = build_admin_knowledge(
    excel_path=excel_path,
    knowledge_base_dir=config.knowledge_base_dir,
    sheet_name=sheet_name,
    config=config,
)

for metod_id, manifest in manifests.items():
    print(
        f"{metod_id}: pruebas={manifest['pruebas_count']} "
        f"controles={manifest['controls_count']} "
        f"source={manifest['source_file']}"
    )

print("Admin knowledge build completed.")
