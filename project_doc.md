# Project Documentation

## METOD-Based RAG Observation Generator MVP in Databricks Notebooks

## 1. Role

Act as a senior AI engineer and Databricks solution architect.

Help me build a Databricks notebook MVP for a METOD-based RAG observation generator.

The MVP must run inside Databricks notebooks.

Do not build a full web application.
Do not use Streamlit.
Do not use Databricks Apps.
Do not use FastAPI.
Do not use Delta tables.
Do not use an external vector database.
Do not overengineer the architecture.
Do not build an autonomous agent.

The goal is to validate the end-to-end RAG logic using Databricks notebooks, Workspace Files, FileStore or Blob Storage, and Azure OpenAI.

---

# 2. Business Goal

I want to create an AI reviewer that generates validation observations for model review workflows.

The reviewer should behave as if it already knows what to analyze for each methodology folder.

The system will have around eight methodology folders:

```text
METOD1
METOD2
METOD3
METOD4
METOD5
METOD6
METOD7
METOD8
```

Each METOD represents a specific methodology, control family, or review topic.

Example:

```text
METOD1 = Gini / discriminatory power review
METOD2 = PSI / stability review
METOD3 = bivariate analysis review
METOD4 = segmentation review
METOD5 = documentation consistency review
METOD6 = variable selection review
METOD7 = implementation/code consistency review
METOD8 = monitoring/evidence completeness review
```

The exact business meaning of each METOD can change later.

The final output should be a structured observation for the selected METOD.

---

# 3. Core Idea

Each METOD has two types of information:

## A. Stable METOD Knowledge

This is the methodology context or “memory” of the system.

It defines:

* What should be analyzed.
* What rules apply.
* What thresholds matter.
* What evidence is required.
* How to assign criticality.
* What a good observation should contain.
* What action plan should be recommended.
* When not to generate an observation.
* What missing information should be flagged.

This knowledge should live outside the notebook runtime folder.

For the MVP, stable METOD knowledge should be stored in FileStore or Blob Storage.

Default MVP path:

```text
/dbfs/FileStore/gestor_obs/knowledge/METOD1/
/dbfs/FileStore/gestor_obs/knowledge/METOD2/
...
```

Example files:

```text
rules.md
methodology.docx
thresholds.xlsx
criteria.md
examples.md
```

## B. Runtime Evidence

This is the evidence to analyze in the current execution.

It includes files such as:

```text
.docx
.xlsx
.png
.jpg
.jpeg
.html
.txt
.md
.py
.sql
.sas
```

Runtime evidence should live in Databricks Workspace Files under the user workspace folder.

Default MVP path:

```text
/Workspace/Users/your.name@example.com/rag_observations/inputs/METOD1/
/Workspace/Users/your.name@example.com/rag_observations/inputs/METOD2/
...
```

The system should analyze the files inside the selected METOD input folder.

---

# 4. Storage Design

The MVP must use two different storage zones.

## 4.1 Workspace Files for Runtime Artifacts

Inputs, indexes, and outputs must be stored in Databricks Workspace Files under the user workspace path.

Base workspace path:

```text
/Workspace/Users/your.name@example.com/rag_observations/
```

Use this path with normal Python file operations:

```python
open()
os.listdir()
os.makedirs()
json.dump()
json.load()
python-docx
openpyxl
BeautifulSoup
PIL
```

Runtime folders:

```text
/Workspace/Users/your.name@example.com/rag_observations/
│
├── inputs/
│   ├── METOD1/
│   ├── METOD2/
│   ├── METOD3/
│   ├── METOD4/
│   ├── METOD5/
│   ├── METOD6/
│   ├── METOD7/
│   └── METOD8/
│
├── indexes/
│   ├── METOD1/
│   │   └── chunks_with_embeddings.json
│   ├── METOD2/
│   │   └── chunks_with_embeddings.json
│   └── ...
│
└── outputs/
    └── generated_observations/
        ├── METOD1_observation_YYYYMMDD_HHMMSS.json
        └── METOD1_observation_YYYYMMDD_HHMMSS.md
```

The notebook should read evidence files from:

```text
/Workspace/Users/your.name@example.com/rag_observations/inputs/METODX/
```

The notebook should save indexes to:

```text
/Workspace/Users/your.name@example.com/rag_observations/indexes/METODX/
```

The notebook should save outputs to:

```text
/Workspace/Users/your.name@example.com/rag_observations/outputs/generated_observations/
```

## 4.2 FileStore or Blob Storage for Stable METOD Knowledge

Stable METOD knowledge should not live inside the notebook execution workspace.

It should live in FileStore or Blob Storage.

For the MVP, use FileStore:

```text
/dbfs/FileStore/gestor_obs/knowledge/
```

Knowledge folder structure:

```text
/dbfs/FileStore/gestor_obs/knowledge/
│
├── METOD1/
│   ├── rules.md
│   ├── methodology.docx
│   └── thresholds.xlsx
│
├── METOD2/
│   ├── rules.md
│   └── methodology.docx
│
├── METOD3/
│   └── rules.md
│
└── ...
```

The knowledge base path must be configurable:

```python
KNOWLEDGE_BASE_DIR = "/dbfs/FileStore/gestor_obs/knowledge"
```

If Blob Storage or ADLS is available later, the path should be easy to replace:

```python
KNOWLEDGE_BASE_DIR = "/mnt/rag-knowledge/knowledge"
```

or another approved workplace storage path.

## 4.3 Storage Separation Principle

Use this separation:

```text
Workspace Files = runtime artifacts
FileStore / Blob Storage = stable METOD knowledge
```

More specifically:

```text
Workspace Files:
- current input files
- JSON indexes
- generated outputs

FileStore / Blob Storage:
- METOD rules
- methodology documents
- thresholds
- criteria
- stable review instructions
```

This distinction matters because runtime artifacts may change frequently, while METOD knowledge should be stable and reusable across executions.

---

# 5. Important Databricks Path Rule

The notebook must distinguish between three path types.

## 5.1 Python Workspace File Paths

Use:

```text
/Workspace/Users/your.name@example.com/rag_observations/...
```

Use these with:

```python
open()
os.listdir()
os.makedirs()
json.dump()
json.load()
python-docx
openpyxl
BeautifulSoup
PIL
```

## 5.2 Databricks or Spark Workspace File URIs

Use:

```text
file:/Workspace/Users/your.name@example.com/rag_observations/...
```

Use these only if a Databricks or Spark API requires a URI.

The MVP should avoid Spark for file reading unless necessary.

## 5.3 DBFS / FileStore Knowledge Paths

Use:

```text
/dbfs/FileStore/gestor_obs/knowledge/METODX/
```

Use these with normal Python file operations.

Do not confuse these paths with Workspace Files.

---

# 6. Required Folder Structure

The MVP should use this folder structure.

## 6.1 Workspace Files: Inputs, Indexes, Outputs

```text
/Workspace/Users/your.name@example.com/rag_observations/
│
├── inputs/
│   ├── METOD1/
│   │   ├── evidence.xlsx
│   │   ├── model_report.docx
│   │   └── screenshot.png
│   │
│   ├── METOD2/
│   │   ├── stability_results.xlsx
│   │   └── validation_report.docx
│   │
│   ├── METOD3/
│   │   └── ...
│   │
│   └── METOD8/
│       └── ...
│
├── indexes/
│   ├── METOD1/
│   │   └── chunks_with_embeddings.json
│   │
│   ├── METOD2/
│   │   └── chunks_with_embeddings.json
│   │
│   └── ...
│
└── outputs/
    └── generated_observations/
        ├── METOD1_observation_YYYYMMDD_HHMMSS.json
        └── METOD1_observation_YYYYMMDD_HHMMSS.md
```

## 6.2 FileStore or Blob Storage: METOD Knowledge

```text
/dbfs/FileStore/gestor_obs/knowledge/
│
├── METOD1/
│   ├── rules.md
│   ├── methodology.docx
│   └── thresholds.xlsx
│
├── METOD2/
│   ├── rules.md
│   └── methodology.docx
│
├── METOD3/
│   └── rules.md
│
└── ...
```

---

# 7. Notebook Widgets

The Databricks notebook should use widgets to let the reviewer select the METOD and enter model information.

Required widgets:

```python
metod_id
model_name
model_type
business_objective
population
target_variable
additional_notes
```

Example:

```python
dbutils.widgets.dropdown(
    name="metod_id",
    defaultValue="METOD1",
    choices=["METOD1", "METOD2", "METOD3", "METOD4", "METOD5", "METOD6", "METOD7", "METOD8"],
    label="METOD folder"
)

dbutils.widgets.text("model_name", "", "Model name")
dbutils.widgets.text("model_type", "Scoring model", "Model type")
dbutils.widgets.text("business_objective", "", "Business objective")
dbutils.widgets.text("population", "", "Population")
dbutils.widgets.text("target_variable", "", "Target variable")
dbutils.widgets.text("additional_notes", "", "Additional notes")
```

These widget values become runtime model context.

Example runtime model context:

```python
MODEL_CONTEXT = {
    "model_name": dbutils.widgets.get("model_name"),
    "model_type": dbutils.widgets.get("model_type"),
    "business_objective": dbutils.widgets.get("business_objective"),
    "population": dbutils.widgets.get("population"),
    "target_variable": dbutils.widgets.get("target_variable"),
    "additional_notes": dbutils.widgets.get("additional_notes")
}
```

---

# 8. Path Configuration

Use this storage configuration.

```python
# ============================================================
# STORAGE CONFIGURATION
# ============================================================

USER_EMAIL = "your.name@example.com"

# Runtime artifacts live in Workspace Files.
# Use this with normal Python file operations.
WORKSPACE_BASE_DIR = f"/Workspace/Users/{USER_EMAIL}/rag_observations"

# Use this only if a Databricks API requires file:/ paths.
WORKSPACE_BASE_URI = f"file:{WORKSPACE_BASE_DIR}"

# Stable METOD knowledge lives in FileStore or Blob/ADLS.
# MVP default: FileStore.
KNOWLEDGE_BASE_DIR = "/dbfs/FileStore/gestor_obs/knowledge"

# If Blob/ADLS is mounted later, replace with something like:
# KNOWLEDGE_BASE_DIR = "/mnt/rag-knowledge/knowledge"

INPUTS_BASE_DIR = f"{WORKSPACE_BASE_DIR}/inputs"
INDEXES_BASE_DIR = f"{WORKSPACE_BASE_DIR}/indexes"
OUTPUTS_BASE_DIR = f"{WORKSPACE_BASE_DIR}/outputs/generated_observations"

METOD_ID = dbutils.widgets.get("metod_id")

KNOWLEDGE_DIR = f"{KNOWLEDGE_BASE_DIR}/{METOD_ID}"
INPUT_DIR = f"{INPUTS_BASE_DIR}/{METOD_ID}"
INDEX_DIR = f"{INDEXES_BASE_DIR}/{METOD_ID}"

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)
os.makedirs(OUTPUTS_BASE_DIR, exist_ok=True)

print("Selected METOD:", METOD_ID)
print("Knowledge folder:", KNOWLEDGE_DIR)
print("Input folder:", INPUT_DIR)
print("Index folder:", INDEX_DIR)
print("Output folder:", OUTPUTS_BASE_DIR)
```

---

# 9. RAG Design

The system should implement a simple local RAG loop without Delta tables.

The RAG flow should be:

```text
1. Select METOD from notebook widget.
2. Load knowledge files from FileStore or Blob Storage under /knowledge/METODX.
3. Load input evidence files from Workspace Files under /inputs/METODX.
4. Parse the files into text chunks.
5. Label chunks as either:
   - knowledge
   - evidence
6. Generate embeddings with Azure OpenAI.
7. Save chunks and embeddings to JSON under Workspace Files /indexes/METODX.
8. Retrieve the most relevant knowledge chunks.
9. Retrieve the most relevant evidence chunks.
10. Build a context package.
11. Send the context package to Azure OpenAI chat model.
12. Generate structured observation JSON.
13. Save output JSON and Markdown files under Workspace Files /outputs/generated_observations.
```

---

# 10. Important Design Principle

Do not send all files blindly to the LLM.

The system must separate:

```text
METOD knowledge = what the AI should know
METOD evidence = what the AI should analyze
Widget model info = what changes per execution
```

The final LLM prompt must include only:

```text
selected METOD knowledge
+
selected METOD evidence
+
model widget context
```

This prevents the prompt from becoming too large, generic, and unstable.

---

# 11. File Parsers Required

Implement parsers for the following file types.

## 11.1 DOCX

Use `python-docx`.

Extract:

* Paragraphs.
* Tables.

## 11.2 XLSX

Use `openpyxl`.

Extract:

* Sheet names.
* Rows.
* Tables as text.
* Row ranges as metadata.

## 11.3 HTML

Use `BeautifulSoup`.

Extract:

* Visible text.
* Tables if possible.
* Headings if possible.

## 11.4 Text and Scripts

For:

```text
.txt
.md
.py
.sql
.sas
```

Read as plain text and chunk.

## 11.5 Images

For:

```text
.png
.jpg
.jpeg
```

Use an Azure OpenAI vision-capable chat model to generate a text description of the image.

The image description should focus on:

* Tables.
* Metrics.
* Charts.
* Warnings.
* Visible output.
* Model validation evidence.
* Any anomaly relevant to generating an observation.

The image description then becomes a normal evidence chunk.

---

# 12. Supported File Extensions

The MVP should support:

```python
SUPPORTED_EXTENSIONS = {
    ".docx",
    ".xlsx",
    ".html",
    ".htm",
    ".txt",
    ".md",
    ".py",
    ".sql",
    ".sas",
    ".png",
    ".jpg",
    ".jpeg"
}
```

Unsupported files should not crash the whole run. They should be skipped with a warning.

---

# 13. Chunk Format

Each chunk should be represented as a Python dictionary.

```python
{
    "chunk_id": "...",
    "metod_id": "METOD1",
    "chunk_role": "knowledge" or "evidence",
    "text": "...",
    "metadata": {
        "source_file": "...",
        "file_path": "...",
        "file_type": "...",
        "content_type": "...",
        "sheet_name": "... optional",
        "row_start": "... optional",
        "row_end": "... optional",
        "char_start": "... optional",
        "char_end": "... optional"
    },
    "embedding": [...],
    "created_at": "..."
}
```

Do not use Spark DataFrames or Delta tables for the MVP unless explicitly requested later.

Use Python lists and JSON files for storage.

---

# 14. Embedding Storage

Since Delta tables are not allowed, store embeddings in JSON files.

For each METOD, save:

```text
/Workspace/Users/your.name@example.com/rag_observations/indexes/METOD1/chunks_with_embeddings.json
```

The file should contain a list of chunk dictionaries.

The notebook should support two modes:

```python
REBUILD_INDEX = True
```

If `REBUILD_INDEX = True`, parse files again and recreate embeddings.

If `REBUILD_INDEX = False`, load the saved JSON embeddings index.

Suggested widget:

```python
dbutils.widgets.dropdown(
    name="rebuild_index",
    defaultValue="true",
    choices=["true", "false"],
    label="Rebuild index"
)

REBUILD_INDEX = dbutils.widgets.get("rebuild_index").lower() == "true"
```

---

# 15. Retrieval Logic

Implement simple cosine similarity retrieval.

Required functions:

```python
get_embedding(text: str) -> List[float]

cosine_similarity(a: List[float], b: List[float]) -> float

retrieve_chunks(
    query: str,
    chunks: List[Dict],
    chunk_role: str,
    top_k: int
) -> List[Dict]
```

The retrieval should separately retrieve:

```text
top knowledge chunks
top evidence chunks
```

Recommended defaults:

```python
top_k_knowledge = 6
top_k_evidence = 8
```

The retrieval should not mix knowledge and evidence in one undifferentiated pool.

---

# 16. Context Builder

Create a function:

```python
build_metod_context(
    metod_id: str,
    model_context: dict,
    chunks: list,
    top_k_knowledge: int = 6,
    top_k_evidence: int = 8
) -> dict
```

It should return:

```python
{
    "metod_id": metod_id,
    "model_context": model_context,
    "retrieved_knowledge": [...],
    "retrieved_evidence": [...]
}
```

The knowledge retrieval query should focus on:

```text
methodology, rules, thresholds, criteria, required analysis steps, criticality rules, action plan guidance
```

The evidence retrieval query should focus on:

```text
relevant evidence from uploaded files to generate a validation observation for the selected METOD
```

The evidence query should include the runtime model context from the widgets.

---

# 17. Prompt Requirements

Create a function:

```python
build_observation_prompt(context: dict) -> str
```

The prompt must instruct the model to:

* Generate a validation observation for the selected METOD.
* Use the METOD knowledge as the review criteria.
* Use the input files as evidence.
* Use the widget model information as model context.
* Not invent facts.
* Say when evidence is insufficient.
* Return valid JSON only.
* Cite source files used.
* Generate a specific observation, not a generic one.
* If no issue is supported by the evidence, say no observation is supported.
* Justify criticality using the retrieved knowledge.
* Recommend a concrete operational action plan.

---

# 18. Required Output JSON

The model must return this structure:

```json
{
  "metod_id": "METOD1",
  "observation": "...",
  "criticality": "Low | Medium | High | Critical",
  "evidence": "...",
  "risk": "...",
  "action_plan": "...",
  "missing_information": ["..."],
  "confidence": 0.0,
  "sources": [
    {
      "source_file": "...",
      "content_type": "...",
      "reason_used": "..."
    }
  ]
}
```

The notebook should save:

```text
.json output
.md human-readable output
```

The Markdown output should be easy to read inside Databricks.

---

# 19. Azure OpenAI Requirements

Use Azure OpenAI.

The notebook should define these variables:

```python
AZURE_OPENAI_API_VERSION = "2024-10-21"
EMBEDDING_DEPLOYMENT = "text-embedding-3-small"
CHAT_DEPLOYMENT = "gpt-4o-mini"
```

The actual deployment names may be changed by the user.

The code should make deployment names easy to configure.

---

# 20. Functions to Implement

Implement the notebook using modular functions.

```python
list_supported_files(folder_path: str) -> List[str]

split_text_into_chunks(
    text: str,
    source_file: str,
    content_type: str,
    chunk_size: int = 1800,
    overlap: int = 200
) -> List[Dict]

parse_docx(file_path: str) -> List[Dict]

parse_xlsx(file_path: str) -> List[Dict]

parse_html(file_path: str) -> List[Dict]

parse_text_or_script(file_path: str) -> List[Dict]

describe_image(file_path: str) -> List[Dict]

parse_file(file_path: str) -> List[Dict]

build_chunks_for_metod(
    metod_id: str,
    knowledge_files: List[str],
    input_files: List[str]
) -> List[Dict]

get_embedding(text: str) -> List[float]

save_chunks_index(metod_id: str, chunks: List[Dict]) -> str

load_chunks_index(metod_id: str) -> List[Dict]

cosine_similarity(a: List[float], b: List[float]) -> float

retrieve_chunks(
    query: str,
    chunks: List[Dict],
    chunk_role: str,
    top_k: int
) -> List[Dict]

build_metod_context(
    metod_id: str,
    model_context: Dict,
    chunks: List[Dict],
    top_k_knowledge: int = 6,
    top_k_evidence: int = 8
) -> Dict

build_observation_prompt(context: Dict) -> str

generate_observation(context: Dict) -> Dict

save_observation_outputs(observation: Dict) -> Dict

display_observation(observation: Dict) -> None
```

---

# 21. Notebook Execution Flow

The notebook should execute in this order:

```text
1. Install required libraries.
2. Import dependencies.
3. Configure Azure OpenAI.
4. Create widgets.
5. Read widget values.
6. Define workspace and knowledge paths.
7. Create runtime folders if they do not exist.
8. Discover knowledge files and input files.
9. Validate that the selected METOD has knowledge files.
10. Validate that the selected METOD has input files.
11. If REBUILD_INDEX = True:
    - parse knowledge files
    - parse input files
    - create chunks
    - generate embeddings
    - save chunks and embeddings to JSON index
12. If REBUILD_INDEX = False:
    - load chunks and embeddings from JSON index
13. Retrieve relevant knowledge chunks.
14. Retrieve relevant evidence chunks.
15. Build METOD context.
16. Generate observation using Azure OpenAI.
17. Validate model output JSON.
18. Save JSON output.
19. Save Markdown output.
20. Display final observation inside the notebook.
```

---

# 22. Error Handling

The notebook should raise clear errors when:

* The selected METOD folder does not exist.
* No knowledge files exist for the selected METOD.
* No input files exist for the selected METOD.
* Azure OpenAI credentials are missing.
* The JSON index does not exist and `REBUILD_INDEX = False`.
* The model returns invalid JSON.

Unsupported files should not crash the whole run. They should be skipped with a warning.

Each skipped file should be printed with:

```text
WARNING: Unsupported file skipped: <file_path>
```

Each failed parser should be printed with:

```text
WARNING: Failed to parse file: <file_path>. Reason: <error>
```

---

# 23. Output Saving

The notebook should save the observation as JSON and Markdown.

## JSON Output

Path:

```text
/Workspace/Users/your.name@example.com/rag_observations/outputs/generated_observations/METODX_observation_YYYYMMDD_HHMMSS.json
```

## Markdown Output

Path:

```text
/Workspace/Users/your.name@example.com/rag_observations/outputs/generated_observations/METODX_observation_YYYYMMDD_HHMMSS.md
```

The Markdown file should contain:

```markdown
# Generated Observation

## METOD
METOD1

## Observation
...

## Criticality
...

## Evidence
...

## Risk
...

## Action Plan
...

## Missing Information
...

## Confidence
...

## Sources
- source_file: ...
  content_type: ...
  reason_used: ...
```

---

# 24. MVP Scope

The MVP should support:

```text
METOD1-METOD8
DOCX
XLSX
HTML
TXT
MD
PY
SQL
SAS
PNG
JPG
JPEG
Azure OpenAI embeddings
Azure OpenAI chat generation
File-based JSON vector index
JSON output
Markdown output
Databricks widgets
Workspace Files for runtime artifacts
FileStore or Blob Storage for stable knowledge
```

The MVP should not include:

```text
Delta tables
Streamlit
Databricks Apps
FastAPI
External vector databases
LangChain-heavy architecture
Autonomous agents
Complex permissions
Production-grade monitoring
Batch processing for all METODs
```

---

# 25. Example METOD Knowledge File

Each METOD should have a `rules.md` file.

Example for `METOD1/rules.md`:

```markdown
# METOD1 - Gini / Discriminatory Power Review

## Objective
Evaluate whether the model has enough discriminatory power for its intended use.

## What to analyze
- Development Gini.
- Validation Gini.
- Out-of-time Gini, if available.
- Segment-level Gini.
- Difference between development and validation performance.
- Whether deterioration is material.

## Required evidence
- Table with Gini or AUC values.
- Description of samples.
- Development period.
- Validation period.
- Segment-level performance, if available.
- Internal acceptance threshold, if available.

## Criticality rules
- High: validation performance is materially below the expected threshold and there is no valid justification.
- Medium: there is moderate deterioration, but the model remains usable with monitoring.
- Low: performance is stable and evidence is complete.

## When to generate an observation
Generate an observation if:
- There is material deterioration.
- Required performance evidence is missing.
- Segment-level performance reveals instability.
- Validation performance is below the expected level.
- There is inconsistency between the report and the evidence file.

## When not to generate an observation
Do not generate an observation if:
- Performance is stable.
- Evidence is complete.
- No relevant issue is supported by the files.

## Action plan guidance
- Request an explanation for performance deterioration.
- Review whether recalibration is needed.
- Request segment-level validation if it is missing.
- Recommend future monitoring if deterioration is moderate.
```

---

# 26. Expected Final Result

At the end of the notebook, the user should see a structured generated observation like this:

```json
{
  "metod_id": "METOD1",
  "observation": "The available evidence indicates a deterioration in discriminatory power in the validation sample compared with the development sample.",
  "criticality": "Medium",
  "evidence": "The Gini table in evidence.xlsx shows a lower validation Gini than the development Gini. The model documentation does not provide a sufficient explanation for the deterioration.",
  "risk": "Reduced discriminatory power may affect the model's ability to rank clients according to risk.",
  "action_plan": "Request an explanation for the deterioration, review segment-level performance, and evaluate whether recalibration or additional monitoring is required.",
  "missing_information": [],
  "confidence": 0.78,
  "sources": [
    {
      "source_file": "evidence.xlsx",
      "content_type": "xlsx_table",
      "reason_used": "Contains Gini values used to assess discriminatory power."
    },
    {
      "source_file": "rules.md",
      "content_type": "md_content",
      "reason_used": "Defines the METOD1 review criteria and criticality rules."
    }
  ]
}
```

Also save:

```text
/Workspace/Users/your.name@example.com/rag_observations/outputs/generated_observations/METOD1_observation_YYYYMMDD_HHMMSS.json

/Workspace/Users/your.name@example.com/rag_observations/outputs/generated_observations/METOD1_observation_YYYYMMDD_HHMMSS.md
```

---

# 27. Future Improvements

After the MVP works, possible improvements include:

1. Move indexes from Workspace Files JSON to Blob Storage or ADLS.
2. Replace JSON cosine similarity with Databricks Vector Search if available.
3. Add reviewer feedback.
4. Add observation approval or rejection.
5. Add Excel export.
6. Add Word export.
7. Add batch generation for all METOD folders.
8. Add better evidence quality checks.
9. Add source citation validation.
10. Add reusable prompt templates per METOD.
11. Add a configuration file for each METOD.
12. Add a human review loop.
13. Add MLflow or Langfuse tracing if allowed.
14. Add versioning for METOD knowledge.
15. Add audit metadata for each run.

---

# 28. Development Style

Generate clean, readable Databricks notebook code.

Keep the code modular.

Avoid overengineering.

Use comments to explain why each section exists.

The first goal is not production.

The first goal is to validate this end-to-end RAG logic:

```text
METOD knowledge
+
METOD evidence
+
model widget context
→
generated observation
```

Once this works, storage, retrieval, evaluation, monitoring, and exports can be improved.

---

# 29. Critical Implementation Warning

The system should not behave like a generic chatbot.

The notebook should behave like a METOD-specific observation generator.

The central component is not the LLM.

The central component is the context-building pipeline:

```text
selected METOD
→ load stable METOD knowledge
→ load runtime evidence
→ parse files
→ retrieve relevant chunks
→ assemble context
→ generate structured observation
```

If the METOD knowledge files are vague, the generated observations will be vague.

Therefore, the quality of `rules.md`, `methodology.docx`, and `thresholds.xlsx` matters more than the LLM prompt itself.

---

# 30. What I Want You To Produce

Produce a complete Databricks notebook implementation that follows this documentation.

The notebook should include:

* dependency installation
* imports
* Azure OpenAI client setup
* Databricks widgets
* path configuration
* file discovery
* parsers
* image description logic
* chunking
* embeddings
* JSON index save/load
* cosine similarity retrieval
* METOD context builder
* prompt builder
* observation generation
* output saving
* final display

Use simple Python functions.

Do not use Delta tables.

Do not use Spark DataFrames unless absolutely necessary.

Do not use Streamlit.

Do not use Databricks Apps.

Do not use FastAPI.

Do not use LangChain unless there is a very specific reason. The MVP should be understandable without a framework.

The output should be a notebook-style implementation with clear cells.
