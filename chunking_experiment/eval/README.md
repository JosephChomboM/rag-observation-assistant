# Evaluation Labels

Use `golden_labels.jsonl` to compute objective retrieval metrics such as
`recall@k`, `hit@1`, and `mrr`.

Copy the example file:

```bash
cp chunking_experiment/eval/golden_labels.example.jsonl chunking_experiment/eval/golden_labels.jsonl
```

Then replace `image_name` values with real image filenames from:

```text
chunking_experiment/inputs/METOD5/
```

Each row describes what the RAG pipeline should retrieve for one image.

## Schema

```json
{
  "image_name": "real_image.png",
  "expected": [
    {
      "relative_path": "METOD5/acceptance.md",
      "heading_contains": "Muestras Train, Dev y Test"
    }
  ],
  "notes": "Optional human note."
}
```

Supported expected fields:

- `relative_path`: expected knowledge source file.
- `source_file`: expected basename, for example `acceptance.md`.
- `chunk_id`: exact expected chunk id, if known.
- `heading_contains`: text expected inside dynamic `heading_path`.

Use `relative_path` for simple source-level evaluation. Use
`heading_contains` when you want section-level evaluation.

