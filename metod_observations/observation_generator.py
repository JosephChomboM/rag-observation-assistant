from __future__ import annotations

import json
import re
from typing import Any, Callable

from .schemas import ObservationResult, PruebaSpec, VALID_CRITICALITIES


def strip_json_fence(text: str) -> str:
    clean = text.strip()
    clean = re.sub(r"^```(?:json)?", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"```$", "", clean).strip()
    return clean


def parse_json_object(text: str) -> dict[str, Any]:
    clean = strip_json_fence(text)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start >= 0 and end > start:
            return json.loads(clean[start : end + 1])
        raise


def validate_observation_payload(payload: dict[str, Any], prueba: PruebaSpec) -> ObservationResult:
    hay_observacion = bool(payload.get("hay_observacion", False))
    criticidad = payload.get("criticidad")
    if isinstance(criticidad, str) and criticidad.lower() == "null":
        criticidad = None

    if hay_observacion:
        if criticidad not in VALID_CRITICALITIES:
            raise ValueError(
                f"Invalid criticality '{criticidad}'. Expected one of {sorted(VALID_CRITICALITIES)}"
            )
    else:
        criticidad = None
        payload["observacion"] = ""

    controles_validos = {control.control_id for control in prueba.controls}
    controles_evaluados = payload.get("controles_evaluados") or [c.control_id for c in prueba.controls]
    controles_origen = payload.get("controles_que_originan_observacion") or []

    controles_evaluados = [control for control in controles_evaluados if control in controles_validos]
    controles_origen = [control for control in controles_origen if control in controles_validos]

    return ObservationResult(
        prueba_id=prueba.prueba_id,
        nombre_prueba=prueba.nombre_prueba,
        hay_observacion=hay_observacion,
        criticidad=criticidad,
        observacion=str(payload.get("observacion", "") or ""),
        sustento=str(payload.get("sustento", "") or ""),
        controles_evaluados=controles_evaluados or [c.control_id for c in prueba.controls],
        controles_que_originan_observacion=controles_origen,
        evidencias_usadas=list(payload.get("evidencias_usadas") or []),
        informacion_faltante=list(payload.get("informacion_faltante") or []),
    )


def generate_observation(
    prompt: str,
    prueba: PruebaSpec,
    chat_fn: Callable[..., str],
    image_data_urls: list[str] | None = None,
) -> ObservationResult:
    raw = chat_fn(prompt, image_data_urls=image_data_urls)
    payload = parse_json_object(raw)
    return validate_observation_payload(payload, prueba)

