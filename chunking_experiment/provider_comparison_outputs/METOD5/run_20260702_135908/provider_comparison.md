# Provider Comparison

Use the provider folders to inspect generated observations side by side.

```json
{
  "providers": [
    {
      "provider": "azure_ai_foundry",
      "output_dir": "C:\\Projects\\projects-ai\\gestor_observaciones\\chunking_experiment\\provider_comparison_outputs\\METOD5\\run_20260702_135908\\azure_ai_foundry",
      "dry_run": true
    },
    {
      "provider": "databricks_model_serving",
      "output_dir": "C:\\Projects\\projects-ai\\gestor_observaciones\\chunking_experiment\\provider_comparison_outputs\\METOD5\\run_20260702_135908\\databricks_model_serving",
      "dry_run": true
    }
  ],
  "decision_rubric": [
    "Compare retrieval quality first: relevant sources and less noisy selected chunks.",
    "Then compare observation quality: valid JSON, specific evidence, useful risk and action plan.",
    "Then compare operations: latency, token usage, authentication, governance, and endpoint ownership."
  ]
}
```
