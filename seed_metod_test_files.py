# Databricks notebook source
"""
Seed test files for the METOD RAG Observation Generator MVP.

Run this notebook once in Databricks before running
metod_rag_observation_generator.py with:
- metod_id = METOD1
- rebuild_index = true

The seeded files include unique probe tokens and invented metrics so you can
verify that the final answer came from retrieved RAG chunks, not from generic
chat-model knowledge.
"""

# COMMAND ----------

import os

USER_EMAIL = "josephchombo@company.com"
WORKSPACE_BASE_DIR = f"/Workspace/Users/{USER_EMAIL}/softia_mvp"
KNOWLEDGE_BASE_DIR = "/dbfs/FileStore/softia_mvp/knowledge"

METOD_ID = "METOD1"

KNOWLEDGE_DIR = f"{KNOWLEDGE_BASE_DIR}/{METOD_ID}"
INPUT_DIR = f"{WORKSPACE_BASE_DIR}/inputs/{METOD_ID}"

os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
os.makedirs(INPUT_DIR, exist_ok=True)

print("Knowledge dir:", KNOWLEDGE_DIR)
print("Input dir:", INPUT_DIR)

# COMMAND ----------

rules_md = """# METOD1 - Gini Discriminatory Power Review

RAG_TEST_KNOWLEDGE_TOKEN: KNO-METOD1-AX17

## Objective
Evaluate whether the model has enough discriminatory power for its intended use.

## What to analyze
- Development Gini.
- Validation Gini.
- Out-of-time Gini.
- Segment-level Gini.
- Difference between development and validation performance.
- Whether deterioration is material.

## Required evidence
- Table or text with Gini or AUC values.
- Description of samples and periods.
- Segment-level performance if available.
- Internal acceptance threshold if available.

## Criticality rules
- Critical: validation Gini is below 0.20 or the model cannot be used for its intended risk-ranking purpose.
- High: validation Gini is below 0.30, or deterioration versus development Gini is 0.18 or more without valid justification.
- Medium: validation Gini is between 0.30 and 0.39, or deterioration versus development Gini is between 0.10 and 0.17.
- Low: validation Gini is 0.40 or higher, deterioration is below 0.10, and evidence is complete.

## Special MVP probe rule
If the evidence mentions RAG_TEST_EVIDENCE_TOKEN EVD-METOD1-BX92 and validation Gini 0.29,
the observation must cite source file gini_validation_evidence.md and must mention that the
retrieved METOD rule KNO-METOD1-AX17 classifies the case as High criticality.

## When to generate an observation
Generate an observation if:
- Validation Gini is below the expected level.
- There is material deterioration.
- Required performance evidence is missing.
- Segment-level performance reveals instability.
- There is inconsistency between report narrative and evidence values.

## When not to generate an observation
Do not generate an observation if:
- Performance is stable.
- Evidence is complete.
- No relevant issue is supported by the files.

## Action plan guidance
- Request an explanation for performance deterioration.
- Review whether recalibration is needed.
- Request segment-level validation if it is missing.
- Define enhanced monitoring until stability is confirmed.
"""

criteria_md = """# METOD1 Criteria Notes

RAG_TEST_CRITERIA_TOKEN: CRT-METOD1-QZ55

For this MVP, a strong observation should contain:
- The exact Gini values found in the evidence.
- The deterioration between development and validation.
- The criticality rule used.
- The operational action plan.
- The source files used.

The reviewer must not invent missing segment-level metrics. If segment-level evidence is not present,
the missing_information field should say that segment-level Gini evidence is missing.
"""

gini_evidence_md = """# Model Validation Evidence - Gini Review

RAG_TEST_EVIDENCE_TOKEN: EVD-METOD1-BX92

Model reviewed: MVP Credit Risk Scorecard
Validation date: 2026-06-10

## Performance table

| Sample | Period | Gini |
| --- | --- | --- |
| Development | 2024-01 to 2024-12 | 0.51 |
| Validation | 2025-01 to 2025-06 | 0.29 |
| Out-of-time | 2025-07 to 2025-12 | 0.31 |

## Reviewer notes

The validation Gini is 0.29. The deterioration versus development is 0.22.
The file does not include segment-level Gini values.
The model report says performance is stable, but the table shows material deterioration.
"""

model_report_txt = """Model report extract

RAG_TEST_REPORT_TOKEN: REP-METOD1-LM04

The model owner states that discriminatory power remains acceptable.
No detailed explanation is provided for the decrease from development Gini 0.51
to validation Gini 0.29.

The report does not include a segment-level Gini table.
"""

irrelevant_md = """# Unrelated operational note

This file is intentionally unrelated to Gini performance.
It discusses meeting logistics and should receive a lower retrieval score than
the files containing RAG_TEST_EVIDENCE_TOKEN EVD-METOD1-BX92.
"""

files_to_write = {
    f"{KNOWLEDGE_DIR}/rules.md": rules_md,
    f"{KNOWLEDGE_DIR}/criteria.md": criteria_md,
    f"{INPUT_DIR}/gini_validation_evidence.md": gini_evidence_md,
    f"{INPUT_DIR}/model_report_extract.txt": model_report_txt,
    f"{INPUT_DIR}/irrelevant_note.md": irrelevant_md,
    f"{INPUT_DIR}/unsupported_file.tmp": "This file should be skipped with a warning.",
}

for file_path, content in files_to_write.items():
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)
    print("Wrote:", file_path)

print("Seed files created. Now run metod_rag_observation_generator.py with METOD1 and rebuild_index=true.")

