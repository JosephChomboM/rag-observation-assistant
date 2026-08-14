from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import ensure_dir
from .schemas import ObservationResult

CRITICALITY_ORDER = ["Critico", "Relevante", "Moderado", "Baja", "Potencial"]


def utc_run_id(metod_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{metod_id}_run_{stamp}"


def observations_to_markdown(metod_id: str, run_id: str, observations: list[ObservationResult]) -> str:
    """One section per prueba, one subsection per control inside it."""
    lines = [f"# Observaciones {metod_id}", "", f"Run ID: `{run_id}`", ""]
    current_prueba = ""
    for observation in observations:
        if observation.prueba_id != current_prueba:
            current_prueba = observation.prueba_id
            lines.extend([f"## {observation.prueba_id} - {observation.nombre_prueba}", ""])
        lines.extend(
            [
                f"### Control {observation.control_id}",
                "",
                observation.detalle or "Sin detalle.",
                "",
                f"**Hay observacion:** {'Si' if observation.hay_observacion else 'No'}",
                "",
                f"**Criticidad:** {observation.criticidad or 'No aplica'}",
                "",
                "**Observacion**",
                observation.observacion or "No se genero observacion.",
                "",
                "**Sustento**",
                observation.sustento or "Sin sustento suficiente.",
                "",
                "**Informacion faltante**",
                "\n".join(f"- {item}" for item in observation.informacion_faltante) or "No reportada.",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def run_summary_text(result: dict[str, Any]) -> str:
    """Plain-language recap of a run, for the validator instead of raw JSON."""
    observations = result.get("observations", [])
    usage = result.get("usage_summary", {})
    with_finding = [item for item in observations if item.get("hay_observacion")]
    counts = Counter(item.get("criticidad") or "Sin criticidad" for item in with_finding)
    sin_sustento = sum(
        1 for item in with_finding if not item.get("sustento_suficiente", True)
    )

    lines = [
        f"METOD {result.get('metod_id', '')} - corrida {result.get('run_id', '')}",
        "",
        f"Pruebas           : {usage.get('pruebas_processed', 0)}",
        f"Controles evaluados: {len(observations)}",
        f"Con observacion   : {len(with_finding)}",
    ]
    for criticidad in CRITICALITY_ORDER:
        if counts.get(criticidad):
            detalle = ""
            if criticidad == "Critico" and sin_sustento:
                detalle = f"  ({sin_sustento} por falta de evidencia)"
            lines.append(f"    {criticidad:<10}: {counts[criticidad]}{detalle}")
    for criticidad in sorted(set(counts) - set(CRITICALITY_ORDER)):
        lines.append(f"    {criticidad:<10}: {counts[criticidad]}")
    lines.append(f"Sin observacion   : {len(observations) - len(with_finding)}")
    lines.append(f"Pruebas afectadas : {len({item.get('prueba_id') for item in with_finding})}")

    evidence_chunks = usage.get("evidence_chunks", 0)
    created = usage.get("evidence_embeddings_created", 0)
    reused = usage.get("evidence_embeddings_reused", 0)
    lines.extend(
        [
            "",
            f"Evidencia         : {usage.get('evidence_files', 0)} archivo(s) del METOD, "
            f"{usage.get('global_context_files', 0)} de contexto global",
            f"Fragmentos        : {evidence_chunks} "
            f"({created} embebidos en esta corrida, {reused} reutilizados del cache)",
            f"Archivos al modelo: {usage.get('prompt_files_sent', 0)} adjuntos",
            f"Llamadas al modelo: {usage.get('llm_generation_requests', 0)}",
        ]
    )
    skipped = usage.get("prompt_files_skipped_by_size", 0)
    if skipped:
        lines.append(f"Omitidos por peso : {skipped} archivo(s)")

    markdown_path = result.get("output_paths", {}).get("markdown", "")
    lines.extend(["", f"Markdown: {Path(markdown_path).name if markdown_path else 'no generado'}"])
    if markdown_path:
        lines.append(f"En      : {Path(markdown_path).parent}")
    return "\n".join(lines)


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
