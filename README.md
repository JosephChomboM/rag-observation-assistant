# RAG Observation Assistant

An AI reviewer that generates **methodological validation observations** for model-review
workflows. Given an arbitrary corpus of evidence that a reviewer uploads — `.pdf`, `.xlsx`,
`.docx`, `.csv`, `.sas`, `.sql`, `.py`, `.html`, and images — plus a shared methodology
knowledge base, the system produces, **per control**, a structured finding that states:

- whether there is an observation (`hay_observacion`),
- its criticality (`Critico`, `Relevante`, `Moderado`, `Baja`, `Potencial`), and
- the exact evidence that supports it (`evidencias_usadas`, each with its `chunk_id` and
  retrieval `score`).

The domain used here is **credit-risk model validation** (PD / LGD / EAD, backtesting,
calibration, stability), but the architecture is domain-agnostic: the methodology knowledge
and glossary are data, not code.

> This is a portfolio version of a production MVP. Organization-specific names, paths and
> data have been generalized.

---

## Why RAG (and not fine-tuning or plain long-context)

The input is not a question — it's a fresh corpus of evidence on every run, and each finding
must be **traceable to a specific fragment of a specific file**. That rules out fine-tuning
(the knowledge changes every run) and rules out naive long-context (unbounded cost and no
verifiable citations).

The design insight is that retrieval acts as a **router**, not a replacement for long context:
a retrieved chunk tells the system *which* documents deserve attention, and then the **whole
file** is attached to the model (via the Files API, PDFs at `detail="high"`). So it's not RAG
*instead of* long context — it's RAG *directing* long context, which bounds cost while keeping
citations exact. The full technical defense lives in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## How it works

```
Evidence files ──▶ parse ──▶ chunk ──▶ embed (cached by content hash)
                                              │
Methodology KB ──▶ per-control profiles ──────┤
Shared glossary ──────────────────────────────┤
                                              ▼
                        hybrid retrieval (+ optional listwise rerank)
                                              │
                                              ▼
            prompt builder: control profile + top-K evidence + glossary
                        + full source files attached as input_file
                                              │
                                              ▼
                 Azure OpenAI (Responses API, reasoning effort)
                                              │
                                              ▼
       structured observation per control  ──▶  JSON payload + Markdown report
```

Key properties:

- **Bounded context.** With `RAG_CHUNK_SIZE=1800` and `RAG_TOP_K_EVIDENCE=8`, retrieved
  context per control stays ~14K characters regardless of whether the user uploaded 5 files
  or 500. The corpus is embedded once and cached by hash, then reused until a file changes.
- **Verifiable citations.** Every finding carries the `chunk_id` and `score` of the evidence
  it used.
- **Knowledge as data.** Methodology folders and the glossary are rebuilt from a source of
  truth by an admin step; the pipeline code never hard-codes domain content.

---

## Project structure

```
metod_observations/            # the pipeline (source of truth)
├── config.py                  # env-driven AppConfig and per-methodology paths
├── parsers.py                 # file-type parsing (pdf/xlsx/docx/csv/html/code/images)
├── chunking.py                # text chunking
├── embeddings.py              # Azure embeddings + content-hash cache
├── retrieval.py               # hybrid retrieval
├── reranking.py               # optional listwise reranking
├── knowledge_builder.py       # builds methodology knowledge + profile embeddings
├── prompt_builder.py          # assembles the per-control prompt
├── observation_generator.py   # calls the model, parses structured output
├── outputs.py                 # JSON payload + Markdown report
├── schemas.py                 # Pydantic schemas for the observation result
├── pipeline.py                # end-to-end orchestration
├── excel_loader.py / io_utils.py

knowledge/                     # methodology knowledge base (data)
├── METOD5/                    # one folder per methodology (acceptance, boundaries, ...)
└── _shared/glossary_data.json # domain glossary

01_admin_build_knowledge.py                        # admin: build KB + stable embeddings
gestor_observaciones/02_generate_observations_by_prueba.py  # user: generate observations

ARCHITECTURE.md  ONBOARDING.md  PROJECT_HANDOFF.md  project_doc.md   # deeper docs
```

---

## Tech stack

- **Python 3.10+**, Pydantic v2 for structured output
- **Azure OpenAI** — embeddings + the Responses API (configurable reasoning effort)
- Document parsing: `openpyxl`, `python-docx`, `pypdf`, `beautifulsoup4`, `Pillow`
- `python-dotenv` + `truststore` for local config and corporate SSL trust
- Designed to run inside **Databricks notebooks** (no web app, no external vector DB —
  embeddings are cached as JSONL files)

---

## Configuration

Copy `.env.example` to `.env` and fill in your Azure OpenAI credentials. Retrieval and
model behavior are tuned entirely through environment variables:

| Variable | Purpose |
|---|---|
| `RAG_KNOWLEDGE_BASE_DIR` | Location of the admin-built knowledge base. |
| `RAG_REASONING_EFFORT` | Reasoning effort sent to the model (`high` by default). |
| `RAG_TOP_K_EVIDENCE` | Max evidence chunks per control. |
| `RAG_TOP_K_GLOBAL_CONTEXT` | Global context chunks per control. |
| `RAG_TOP_K_GLOSSARY` | Max glossary terms retrieved. |
| `RAG_MAX_PROMPT_FILES` | Max source files attached as `input_file` per control. |
| `RAG_MAX_PROMPT_IMAGES` | Max images attached per control. |
| `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` | Chunk size and overlap (characters). |
| `RAG_RETRIEVAL_MODE` | Retrieval mode (`hybrid` by default). |
| `RAG_ENABLE_RERANK` | Enable optional listwise reranking. |

---

## Running it

The workflow is two notebooks:

1. **Admin — build the knowledge base** ([`01_admin_build_knowledge.py`](01_admin_build_knowledge.py)):
   converts the methodology source of truth into per-control knowledge and stable embeddings.
   Run once, or whenever the methodology changes.

2. **User — generate observations**
   ([`gestor_observaciones/02_generate_observations_by_prueba.py`](gestor_observaciones/02_generate_observations_by_prueba.py)):
   pick a methodology and a workspace folder, drop evidence into the input folders, and run.
   Each run is stamped with its own `run_id`, so earlier runs are never overwritten.

```bash
pip install -r requirements.txt
```

---

## Further reading

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — end-to-end technical defense: why RAG, retrieval
  design, the router-over-long-context argument.
- [`ONBOARDING.md`](ONBOARDING.md) — how to set up and operate the system.
- [`PROJECT_HANDOFF.md`](PROJECT_HANDOFF.md) — operational handoff and run details.
- [`project_doc.md`](project_doc.md) — the original MVP specification.
