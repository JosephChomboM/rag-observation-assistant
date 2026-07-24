# Databricks notebook source
# MAGIC %pip install --upgrade openai pydantic python-dotenv truststore openpyxl python-docx beautifulsoup4 pypdf

# COMMAND ----------

"""
User notebook: generate one consolidated observation per prueba.

The administrator configures the shared backend path once in this notebook.
The user selects a METOD and their workspace folder.
The pipeline reads:
- shared backend code from <BACKEND_PROJECT_DIR>/metod_observations/
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
from pathlib import Path

import truststore
from dotenv import load_dotenv

# Configure this path before distributing the notebook to users.
# The folder must contain metod_observations/ and the .env file.
BACKEND_PROJECT_DIR = "/Workspace/Users/<admin>/<cualquier_nombre>"

try:
    dbutils.widgets.text("metod_id", "BBDD1", "METOD")
    dbutils.widgets.text(
        "user_base_dir",
        "",
        "Carpeta del usuario",
    )
except NameError:
    pass


def get_widget(name: str, default: str = "") -> str:
    try:
        return dbutils.widgets.get(name).strip()
    except NameError:
        return os.getenv(name.upper(), default).strip()


backend_project_dir = BACKEND_PROJECT_DIR.strip()
if not (Path(backend_project_dir) / "metod_observations").is_dir():
    raise FileNotFoundError(
        "Configura BACKEND_PROJECT_DIR con la carpeta que contiene "
        f"metod_observations. Ruta actual: {backend_project_dir}"
    )

load_dotenv(os.path.join(backend_project_dir, ".env"), override=True)
truststore.inject_into_ssl()

if backend_project_dir not in sys.path:
    sys.path.insert(0, backend_project_dir)

from metod_observations.config import load_config  # noqa: E402
from metod_observations.pipeline import run_observation_pipeline  # noqa: E402

# COMMAND ----------

base_config = load_config(os.path.join(backend_project_dir, ".env"))
user_base_dir = get_widget("user_base_dir")
metod_id = get_widget("metod_id", "BBDD1").upper()

if not user_base_dir:
    raise ValueError("Indica la carpeta del usuario en el widget user_base_dir.")

config = replace(
    base_config,
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
