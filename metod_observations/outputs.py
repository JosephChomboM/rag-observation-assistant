from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import ensure_dir, write_json, write_jsonl
from .schemas import ObservationResult


def utc_run_id(metod_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{metod_id}_run_{stamp}"


def observations_to_markdown(metod_id: str, run_id: str, observations: list[ObservationResult]) -> str:
    lines = [f"# Observaciones {metod_id}", "", f"Run ID: `{run_id}`", ""]
    for observation in observations:
        lines.extend(
            [
                f"## {observation.prueba_id} - {observation.nombre_prueba}",
                "",
                f"**Hay observacion:** {'Si' if observation.hay_observacion else 'No'}",
                "",
                f"**Criticidad:** {observation.criticidad or 'No aplica'}",
                "",
                "### Observacion",
                observation.observacion or "No se genero observacion.",
                "",
                "### Sustento",
                observation.sustento or "Sin sustento suficiente.",
                "",
                "### Controles evaluados",
                ", ".join(observation.controles_evaluados) or "No especificado.",
                "",
                "### Controles que originan observacion",
                ", ".join(observation.controles_que_originan_observacion) or "No aplica.",
                "",
                "### Informacion faltante",
                "\n".join(f"- {item}" for item in observation.informacion_faltante) or "No reportada.",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def save_run_outputs(
    outputs_base_dir: str | Path,
    run_details_dir: str | Path,
    metod_id: str,
    run_id: str,
    observations: list[ObservationResult],
    retrieval_debug_rows: list[dict[str, Any]],
    usage_summary: dict[str, Any],
) -> dict[str, str]:
    """Write the markdown to `outputs_base_dir` and everything else elsewhere.

    `outputs_base_dir` is the user-facing deliverable folder and must hold only
    the observation markdown. The run JSON and the retrieval debug go to
    `run_details_dir`.
    """
    ensure_dir(outputs_base_dir)
    ensure_dir(run_details_dir)
    base = Path(outputs_base_dir)
    details = Path(run_details_dir)
    payload = {
        "metod_id": metod_id,
        "run_id": run_id,
        "usage_summary": usage_summary,
        "pruebas": [observation.to_dict() for observation in observations],
    }
    md_path = base / f"{run_id}.md"
    json_path = details / f"{run_id}.json"
    debug_path = details / f"retrieval_debug_{run_id}.jsonl"

    write_json(json_path, payload)
    md_path.write_text(observations_to_markdown(metod_id, run_id, observations), encoding="utf-8")
    write_jsonl(debug_path, retrieval_debug_rows)
    return {
        "json": os.fspath(json_path),
        "markdown": os.fspath(md_path),
        "retrieval_debug": os.fspath(debug_path),
    }
