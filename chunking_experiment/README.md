# Chunking Experiment

This folder compares static and dynamic chunking over the managed `knowledge/`
folder. It does not create embeddings yet. The goal is to produce comparable
chunk datasets and simple metrics before deciding which strategy should feed
the production embedding index.

## Scope

- Applies to `knowledge/` Markdown files.
- Does not process user inputs in this first experiment.
- Does not chunk raw image JSON outputs directly.
- Produces JSONL chunks and JSON metric summaries.

For user images, the recommended later flow is:

```text
image -> visual extraction JSON -> normalized evidence text -> evidence chunks -> embeddings
```

If the normalized text for one image is short, keep it as one evidence chunk.
Only split image-derived evidence when a JSON extraction contains multiple
tables, findings, pages, or semantically independent evidence blocks.

## Run Locally

From the project root:

```bash
python chunking_experiment/run_experiment.py
```

## Run In Databricks

Example from a notebook:

```python
import sys
sys.path.append("/Workspace/Users/<user>/gestor_observaciones/chunking_experiment")

from run_experiment import main
main()
```

## Outputs

```text
chunking_experiment/outputs/
  static/
    chunks_static.jsonl
    metrics_static.json
  dynamic/
    chunks_dynamic.jsonl
    metrics_dynamic.json
  comparison_summary.json
```

These outputs are intentionally separated from future user evidence chunks and
embeddings.

## RAG Retrieval Pipeline

After generating static and dynamic chunks, run the pipeline from a Databricks
notebook with normal Python parameters. Do not pass command-line arguments.

```python
import sys
sys.path.append("/Workspace/Users/josephchombo@company.com/DEV/gestor_observaciones/chunking_experiment")

from rag_chunking_pipeline import main

main(dry_run=True)
```

Run the full image-to-retrieval pipeline after configuring Azure OpenAI
environment variables:

```python
main(metod_id="METOD5", top_k=5)
```

Required environment variables:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_API_VERSION
MODEL_NAME_GPT4
DEPLOYMENT_GPT4
MODEL_NAME_EMB_SMALL
DEPLOYMENT_EMB_SMALL
```

The full pipeline:

```text
image -> vision JSON -> normalized query text -> query embedding -> vector search
```

Chunk embeddings are stored beside each strategy:

```text
outputs/static/chunks_static_embeddings.jsonl
outputs/dynamic/chunks_dynamic_embeddings.jsonl
```

Per-run retrieval outputs are stored separately:

```text
rag_outputs/METOD5/<run_id>/
  image_descriptions.jsonl
  image_queries.jsonl
  retrieval_results.jsonl
  retrieval_results.csv
  retrieval_summary.json
  evaluation_metrics.json
  observation_static.json
  observation_static.md
  observation_dynamic.json
  observation_dynamic.md
  observation_comparison.json
```

`retrieval_results.csv` is for human inspection and debugging. The objective
comparison between static and dynamic chunking should use
`evaluation_metrics.json` and `observation_comparison.json`.

To compute `recall@k`, create labels:

```bash
cp chunking_experiment/eval/golden_labels.example.jsonl chunking_experiment/eval/golden_labels.jsonl
```

Then edit `golden_labels.jsonl` with the expected source/section for each real
image. The pipeline will compute:

- `source_hit_at_1`
- `source_recall_at_k`
- `source_mrr`
- `section_hit_at_1`
- `section_recall_at_k`
- `section_mrr`

The pipeline also generates one observation with static chunks and one with
dynamic chunks. `observation_comparison.json` chooses the better observation
using labeled retrieval metrics first, because a better observation should be
grounded in more relevant retrieved knowledge.

Run with labels:

```python
main(
    metod_id="METOD5",
    top_k=5,
    eval_labels_path="/Workspace/Users/josephchombo@company.com/DEV/gestor_observaciones/chunking_experiment/eval/golden_labels.jsonl",
)
```

## Azure AI Foundry vs Databricks Model Serving

Use the Databricks notebook version for this comparison:

```text
chunking_experiment/notebooks/02_provider_comparison.py
```

Recommended Databricks flow:

```python
# In a Databricks notebook cell
%run /Workspace/Users/<user>/DEV/gestor_observaciones/chunking_experiment/notebooks/02_provider_comparison
```

Or import the notebook source as a regular workspace file if your repo is synced
into Databricks Repos.

Important widgets:

```text
chunking_dir                  /Workspace/Users/<user>/DEV/gestor_observaciones/chunking_experiment
metod_id                      METOD5
dry_run                       true | false
providers                     azure_ai_foundry,databricks_model_serving
include_images_in_observation true | false
image_detail                  low | high | auto
fixed_context                 dynamic_top_7 (uses dynamic chunks and the top 7 retrieved chunks)
```

Azure variables reuse the current setup:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_API_VERSION
MODEL_NAME_GPT4
DEPLOYMENT_GPT4
MODEL_NAME_EMB_SMALL
DEPLOYMENT_EMB_SMALL
```

Databricks Model Serving variables:

```text
DATABRICKS_EMBEDDING_ENDPOINT=databricks-qwen3-embedding-0-6b
DATABRICKS_CHAT_ENDPOINT=databricks-claude-haiku-4-5
```

When running inside Databricks, `mlflow.deployments.get_deploy_client("databricks")`
uses the active workspace context. For local execution, configure Databricks auth
separately.

The notebook uses a single fixed context strategy: `dynamic_top_7`. It reads only `outputs/dynamic/chunks_dynamic.jsonl`, retrieves the top 7 knowledge chunks globally, and writes one folder per provider:

```text
provider_comparison_outputs/METOD5/<run_id>/
  azure_ai_foundry/
    context_comparison.json
    llm_call_log.jsonl
    llm_usage_summary.json
    observation_dynamic_top_7.md
  databricks_model_serving/
    context_comparison.json
    llm_call_log.jsonl
    llm_usage_summary.json
    observation_dynamic_top_7.md
  provider_comparison.json
  provider_comparison.md
```

Use `context_comparison.json` and the generated observations to compare
grounding quality. Use `llm_usage_summary.json` to compare calls, tokens, and
latency.

