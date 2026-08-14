from __future__ import annotations

import os
from pathlib import Path

from .excel_loader import slugify
from .io_utils import ensure_dir, write_json
from .schemas import ControlSpec, PruebaSpec


def prueba_markdown_filename(prueba: PruebaSpec) -> str:
    return f"{prueba.prueba_id}_{slugify(prueba.nombre_prueba)}.md"


def prueba_to_markdown(prueba: PruebaSpec) -> str:
    lines = [
        "---",
        f"metod_id: {prueba.metod_id}",
        f"prueba_id: {prueba.prueba_id}",
        f"nombre_prueba: {prueba.nombre_prueba}",
        f"source: {prueba.source_file}",
        "---",
        "",
        f"# {prueba.nombre_prueba}",
        "",
    ]
    for control in prueba.controls:
        lines.extend(
            [
                f"## Control {control.control_id}",
                "",
                "### Detalle",
                control.detalle or "No especificado.",
                "",
                "### Prompt",
                control.prompt or "No especificado.",
                "",
                "### Limites",
                control.limites or "No especificado.",
                "",
                "### Criticidad",
                control.criticidad or "No especificado.",
                "",
                "### Excepciones",
                control.excepciones or "Sin excepciones.",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def control_profile_text(prueba: PruebaSpec, control: ControlSpec) -> str:
    """Query text of a single control: what its evidence retrieval searches for."""
    return "\n".join(
        [
            f"METOD: {prueba.metod_id}",
            f"Prueba: {prueba.nombre_prueba}",
            f"Control: {control.control_id}",
            f"Detalle: {control.detalle}",
            f"Prompt: {control.prompt}",
            f"Limites: {control.limites}",
            f"Criticidad: {control.criticidad}",
            f"Excepciones: {control.excepciones}",
        ]
    )


def prueba_profile_text(prueba: PruebaSpec) -> str:
    control_blocks = []
    for control in prueba.controls:
        control_blocks.append(
            "\n".join(
                [
                    f"Control: {control.control_id}",
                    f"Detalle: {control.detalle}",
                    f"Prompt: {control.prompt}",
                    f"Limites: {control.limites}",
                    f"Criticidad: {control.criticidad}",
                    f"Excepciones: {control.excepciones}",
                ]
            )
        )
    return "\n\n".join(
        [
            f"METOD: {prueba.metod_id}",
            f"Prueba: {prueba.nombre_prueba}",
            *control_blocks,
        ]
    )


def build_knowledge_from_pruebas(
    pruebas: list[PruebaSpec],
    knowledge_base_dir: str | Path,
) -> dict:
    if not pruebas:
        raise ValueError("No prueba specs were provided.")

    metod_id = pruebas[0].metod_id
    metod_dir = Path(knowledge_base_dir) / metod_id
    pruebas_dir = metod_dir / "pruebas"
    ensure_dir(pruebas_dir)

    manifest_pruebas = []
    for prueba in pruebas:
        md_name = prueba_markdown_filename(prueba)
        md_path = pruebas_dir / md_name
        md_path.write_text(prueba_to_markdown(prueba), encoding="utf-8")
        manifest_pruebas.append(
            {
                **prueba.to_dict(),
                "markdown_file": os.path.join("pruebas", md_name).replace("\\", "/"),
                "profile_text": prueba_profile_text(prueba),
            }
        )

    manifest = {
        "metod_id": metod_id,
        "source_file": pruebas[0].source_file,
        "pruebas_count": len(pruebas),
        "controls_count": sum(len(prueba.controls) for prueba in pruebas),
        "pruebas": manifest_pruebas,
    }
    write_json(metod_dir / "manifest.json", manifest)
    return manifest


def build_knowledge_for_all_metods(
    pruebas_by_metod: dict[str, list[PruebaSpec]],
    knowledge_base_dir: str | Path,
) -> dict[str, dict]:
    return {
        metod_id: build_knowledge_from_pruebas(pruebas, knowledge_base_dir)
        for metod_id, pruebas in pruebas_by_metod.items()
    }
