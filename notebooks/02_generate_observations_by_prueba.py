# Databricks notebook source
# MAGIC %pip install --upgrade openai python-dotenv truststore openpyxl python-docx beautifulsoup4 pypdf

# COMMAND ----------

"""
User notebook: generate one consolidated observation per prueba.

The user only selects a METOD and their workspace folder. The pipeline reads:
- METOD evidence from <user_base_dir>/inputs/<METOD>/
- shared user context from <user_base_dir>/inputs/_global/
- admin knowledge and stable embeddings from SOFTIA_KNOWLEDGE_BASE_DIR

Model deployments, reasoning, retrieval and chunking settings come from .env.
"""

# COMMAND ----------

import json
import os
import sys
from dataclasses import replace

import truststore
from dotenv import load_dotenv

load_dotenv(".env", override=True)
truststore.inject_into_ssl()

try:
    dbutils.widgets.text("metod_id", "BBDD1", "METOD")
    dbutils.widgets.text(
        "user_base_dir",
        os.getenv("SOFTIA_WORKSPACE_BASE_DIR", ""),
        "Carpeta del usuario",
    )
except NameError:
    pass


def get_widget(name: str, default: str = "") -> str:
    try:
        return dbutils.widgets.get(name).strip()
    except NameError:
        return os.getenv(name.upper(), default).strip()


repo_root = os.getenv("SOFTIA_CODE_PATH", os.getcwd()).strip()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from metod_observations.config import load_config  # noqa: E402
from metod_observations.pipeline import run_observation_pipeline  # noqa: E402

# COMMAND ----------

base_config = load_config()
user_base_dir = get_widget("user_base_dir") or base_config.workspace_base_dir
metod_id = get_widget("metod_id", "BBDD1").upper()

config = replace(
    base_config,
    workspace_base_dir=user_base_dir,
    inputs_base_dir=os.path.join(user_base_dir, "inputs"),
    indexes_base_dir=os.path.join(user_base_dir, "indexes"),
    outputs_base_dir=os.path.join(user_base_dir, "outputs", "generated_observations"),
)

print("METOD:", metod_id)
print("Evidencias:", os.path.join(config.inputs_base_dir, metod_id))
print("Contexto global:", os.path.join(config.inputs_base_dir, "_global"))
print("Resultados:", config.outputs_base_dir)

# COMMAND ----------

result = run_observation_pipeline(
    metod_id=metod_id,
    config=config,
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

