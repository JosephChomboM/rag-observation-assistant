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
- admin knowledge and stable embeddings from RAG_KNOWLEDGE_BASE_DIR

And writes:
- the observation markdown to <user_base_dir>/outputs/
- the embedding cache to <user_base_dir>/indexes/

The markdown is the only file a run leaves on disk. Each run stamps it with its
own run_id, so previous runs are never overwritten. The structured payload, the
usage summary and the retrieval debug come back in `result`, in memory.

Run the cells in order: the "Preparar carpetas de entrada" cell creates one input
folder per METOD in METOD_IDS plus the shared one, and nothing else. The run
covers the single METOD picked in the widget and creates whatever it needs.

Model deployments, reasoning, retrieval and chunking settings come from .env.
"""

# COMMAND ----------

import os
import sys
from dataclasses import replace
from pathlib import Path

import truststore
from dotenv import load_dotenv

# Configure this path before distributing the notebook to users.
# The folder must contain metod_observations/ and the .env file.
BACKEND_PROJECT_DIR = "/Workspace/Users/<admin>/<cualquier_nombre>"

# Every METOD the user can run. The prepare cell creates one input folder for
# each, so the user sees the full set at once. Keep it in sync with the sheets
# of the master Excel.
METOD_IDS = ["BBDD1", "BBDD2", *(f"METOD{number}" for number in range(1, 9))]

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
from metod_observations.outputs import run_summary_text  # noqa: E402
from metod_observations.pipeline import (  # noqa: E402
    prepare_user_workspace,
    run_observation_pipeline,
)

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
    outputs_base_dir=os.path.join(user_base_dir, "outputs"),
)

print("METOD:", metod_id)
print("Deployment GPT-5.4:", config.chat_deployment)
print("Deployment text-embedding-3-small:", config.embedding_deployment)
print("Evidencias:", os.path.join(config.inputs_base_dir, metod_id))
print("Contexto global:", os.path.join(config.inputs_base_dir, "_global"))
print("Resultados (solo markdown):", config.outputs_base_dir)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preparar carpetas de entrada
# MAGIC Crea la carpeta de todos los METOD y la compartida. El resto lo crea la corrida.

# COMMAND ----------

workspace = prepare_user_workspace(METOD_IDS, config=config)

print("Contexto compartido para todos los METOD:", workspace["global_input_dir"])
print("Evidencia por METOD:")
for metod, input_dir in workspace["input_dirs"].items():
    print(f"  {metod}: {input_dir}")

# COMMAND ----------

result = run_observation_pipeline(
    metod_id=metod_id,
    config=config,
)

print(run_summary_text(result))
