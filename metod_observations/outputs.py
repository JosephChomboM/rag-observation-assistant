from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from .io_utils import ensure_dir
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
    metod_id: str,
    run_id: str,
    observations: list[ObservationResult],
) -> dict[str, str]:
    """Write the observation markdown. It is the only file a run leaves on disk.

    The structured payload, the usage summary and the retrieval debug stay in
    the object returned by `run_observation_pipeline`.
    """
    ensure_dir(outputs_base_dir)
    md_path = Path(outputs_base_dir) / f"{run_id}.md"
    md_path.write_text(observations_to_markdown(metod_id, run_id, observations), encoding="utf-8")
    return {"markdown": os.fspath(md_path)}
