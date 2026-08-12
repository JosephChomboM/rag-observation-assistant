from __future__ import annotations

from typing import Any, Callable

from .schemas import (
    ObservationResult,
    ObservationPayload,
    PruebaSpec,
)


OBSERVATION_INSTRUCTIONS = """
Eres un validador metodologico.

- Evalua todos los controles y devuelve una sola observacion consolidada por prueba.
- No inventes evidencia ni valores. Usa solo la evidencia recuperada que sustente el resultado.
- Analiza los archivos y las imagenes adjuntos directamente, pero usalos solo cuando sean relevantes.
- Usa el contexto global para interpretar variables y parametros; no lo trates como evidencia de cumplimiento o incumplimiento.
- No incluyas archivos de contexto global en evidencias_usadas.
- Usa solamente los IDs de controles y evidencias proporcionados en la solicitud.
- sustento_suficiente indica si la evidencia recuperada alcanza para evaluar la prueba.
- Si no alcanza, devuelve sustento_suficiente=false y detalla en informacion_faltante que evidencia falta. La prueba se reporta como Critico automaticamente: no inventes un hallazgo para justificarlo.
- Si alcanza y la prueba se cumple, devuelve sustento_suficiente=true, hay_observacion=false, criticidad=null y observacion="".
- Cumple estrictamente el esquema de salida solicitado.
""".strip()

SIN_SUSTENTO_OBSERVACION = (
    "No se presento evidencia suficiente para evaluar esta prueba. "
    "Se reporta como Critico por falta de sustento."
)


def validate_observation_payload(
    parsed: ObservationPayload,
    prueba: PruebaSpec,
) -> ObservationResult:
    controles_validos = {control.control_id for control in prueba.controls}
    controles_evaluados = parsed.controles_evaluados or [c.control_id for c in prueba.controls]
    controles_origen = parsed.controles_que_originan_observacion

    controles_evaluados = [control for control in controles_evaluados if control in controles_validos]
    controles_origen = [control for control in controles_origen if control in controles_validos]
    controles_evaluados = controles_evaluados or [c.control_id for c in prueba.controls]

    if not parsed.sustento_suficiente:
        # Sin evidencia que la sustente, la prueba se trata como si no se
        # hubieran presentado inputs: observacion Critica, no un "sin hallazgo".
        return ObservationResult(
            prueba_id=prueba.prueba_id,
            nombre_prueba=prueba.nombre_prueba,
            hay_observacion=True,
            criticidad="Critico",
            observacion=parsed.observacion or SIN_SUSTENTO_OBSERVACION,
            sustento=parsed.sustento,
            controles_evaluados=controles_evaluados,
            controles_que_originan_observacion=controles_origen or controles_evaluados,
            evidencias_usadas=[item.model_dump() for item in parsed.evidencias_usadas],
            informacion_faltante=parsed.informacion_faltante or [SIN_SUSTENTO_OBSERVACION],
            sustento_suficiente=False,
        )

    return ObservationResult(
        prueba_id=prueba.prueba_id,
        nombre_prueba=prueba.nombre_prueba,
        hay_observacion=parsed.hay_observacion,
        criticidad=parsed.criticidad if parsed.hay_observacion else None,
        observacion=parsed.observacion if parsed.hay_observacion else "",
        sustento=parsed.sustento,
        controles_evaluados=controles_evaluados,
        controles_que_originan_observacion=controles_origen,
        evidencias_usadas=[item.model_dump() for item in parsed.evidencias_usadas],
        informacion_faltante=parsed.informacion_faltante,
    )


def generate_observation(
    input_text: str,
    prueba: PruebaSpec,
    chat_fn: Callable[..., ObservationPayload],
    file_inputs: list[dict[str, Any]] | None = None,
    image_data_urls: list[str] | None = None,
) -> ObservationResult:
    parsed = chat_fn(
        input_text,
        instructions=OBSERVATION_INSTRUCTIONS,
        text_format=ObservationPayload,
        file_inputs=file_inputs,
        image_data_urls=image_data_urls,
    )
    return validate_observation_payload(parsed, prueba)
