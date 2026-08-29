from __future__ import annotations

from typing import Any, Callable

from .schemas import (
    ControlSpec,
    ObservationResult,
    ObservationPayload,
    PruebaSpec,
)


OBSERVATION_INSTRUCTIONS = """
Eres un validador metodologico.

- Evalua un unico control y devuelve una sola observacion para ese control.
- No evalues otros controles de la prueba ni consolides resultados: la prueba solo agrupa controles.
- No inventes evidencia ni valores. Usa solo la evidencia recuperada que sustente el resultado.
- Analiza los archivos y las imagenes adjuntos directamente, pero usalos solo cuando sean relevantes.
- Usa el contexto global para interpretar variables y parametros; no lo trates como evidencia de cumplimiento o incumplimiento.
- No incluyas archivos de contexto global en evidencias_usadas.
- Usa solamente el control_id y los IDs de evidencia proporcionados en la solicitud.
- sustento_suficiente indica si la evidencia recuperada alcanza para evaluar este control y concluir su criticidad.
- insumo_parcial indica si se presento algun insumo relevante para este control (por ejemplo una captura, un grafico o un archivo relacionado) aunque no alcance para concluir.
- Cuando la evidencia no alcance, decide entre estos dos casos:
  1. Hay insumo parcial relevante pero insuficiente para derivar el resultado (por ejemplo llega una captura de un grafico pero faltan los datos para calcular las bandas): devuelve sustento_suficiente=false, insumo_parcial=true, hay_observacion=false, criticidad="No concluyente" y observacion="". No concluyas la criticidad ni inventes un hallazgo; detalla en informacion_faltante exactamente que se necesita subir para poder concluir.
  2. No se presento ningun insumo relevante para el control: devuelve sustento_suficiente=false, insumo_parcial=false. El control se reporta como Critico automaticamente por falta de sustento; no inventes un hallazgo para justificarlo, solo detalla en informacion_faltante que evidencia falta.
- Si la evidencia alcanza y el control se cumple, devuelve sustento_suficiente=true, insumo_parcial=true, hay_observacion=false, criticidad=null y observacion="".
- Cumple estrictamente el esquema de salida solicitado.
""".strip()

SIN_SUSTENTO_OBSERVACION = (
    "No se presento evidencia suficiente para evaluar este control. "
    "Se reporta como Critico por falta de sustento."
)

NO_CONCLUYENTE_OBSERVACION = (
    "No se puede concluir la observacion ni la criticidad con el insumo presentado. "
    "Revisa 'informacion faltante' para saber que se debe subir."
)


def validate_observation_payload(
    parsed: ObservationPayload,
    prueba: PruebaSpec,
    control: ControlSpec,
) -> ObservationResult:
    if not parsed.sustento_suficiente:
        if parsed.insumo_parcial:
            # Hubo insumo relevante pero no alcanza para concluir. No se fuerza
            # criticidad: queda "No concluyente" y se pide lo que falta subir.
            return ObservationResult(
                prueba_id=prueba.prueba_id,
                nombre_prueba=prueba.nombre_prueba,
                control_id=control.control_id,
                detalle=control.detalle,
                hay_observacion=False,
                criticidad="No concluyente",
                observacion=parsed.observacion or NO_CONCLUYENTE_OBSERVACION,
                sustento=parsed.sustento,
                evidencias_usadas=[item.model_dump() for item in parsed.evidencias_usadas],
                informacion_faltante=parsed.informacion_faltante or [NO_CONCLUYENTE_OBSERVACION],
                sustento_suficiente=False,
                insumo_parcial=True,
            )
        # Sin ningun insumo que lo sustente, el control se trata como si no se
        # hubieran presentado inputs: observacion Critica, no un "sin hallazgo".
        return ObservationResult(
            prueba_id=prueba.prueba_id,
            nombre_prueba=prueba.nombre_prueba,
            control_id=control.control_id,
            detalle=control.detalle,
            hay_observacion=True,
            criticidad="Critico",
            observacion=parsed.observacion or SIN_SUSTENTO_OBSERVACION,
            sustento=parsed.sustento,
            evidencias_usadas=[item.model_dump() for item in parsed.evidencias_usadas],
            informacion_faltante=parsed.informacion_faltante or [SIN_SUSTENTO_OBSERVACION],
            sustento_suficiente=False,
            insumo_parcial=False,
        )

    return ObservationResult(
        prueba_id=prueba.prueba_id,
        nombre_prueba=prueba.nombre_prueba,
        control_id=control.control_id,
        detalle=control.detalle,
        hay_observacion=parsed.hay_observacion,
        criticidad=parsed.criticidad if parsed.hay_observacion else None,
        observacion=parsed.observacion if parsed.hay_observacion else "",
        sustento=parsed.sustento,
        evidencias_usadas=[item.model_dump() for item in parsed.evidencias_usadas],
        informacion_faltante=parsed.informacion_faltante,
        insumo_parcial=parsed.insumo_parcial,
    )


def generate_observation(
    input_text: str,
    prueba: PruebaSpec,
    control: ControlSpec,
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
    return validate_observation_payload(parsed, prueba, control)
