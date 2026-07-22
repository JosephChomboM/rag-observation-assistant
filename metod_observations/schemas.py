from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


VALID_CRITICALITIES = {"Critico", "Relevante", "Moderado", "Baja", "Potencial"}

OBSERVATION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "prueba_id": {"type": "string"},
        "nombre_prueba": {"type": "string"},
        "hay_observacion": {"type": "boolean"},
        "criticidad": {
            "type": ["string", "null"],
            "enum": [*sorted(VALID_CRITICALITIES), None],
        },
        "observacion": {"type": "string"},
        "sustento": {"type": "string"},
        "controles_evaluados": {
            "type": "array",
            "items": {"type": "string"},
        },
        "controles_que_originan_observacion": {
            "type": "array",
            "items": {"type": "string"},
        },
        "evidencias_usadas": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "archivo": {"type": "string"},
                    "chunk_id": {"type": "string"},
                    "score": {"type": "number"},
                },
                "required": ["archivo", "chunk_id", "score"],
            },
        },
        "informacion_faltante": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "prueba_id",
        "nombre_prueba",
        "hay_observacion",
        "criticidad",
        "observacion",
        "sustento",
        "controles_evaluados",
        "controles_que_originan_observacion",
        "evidencias_usadas",
        "informacion_faltante",
    ],
}



@dataclass(frozen=True)
class ControlSpec:
    metod_id: str
    prueba_id: str
    control_id: str
    nombre_prueba: str
    detalle: str
    prompt: str
    limites: str
    criticidad: str
    excepciones: str
    row_number: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PruebaSpec:
    metod_id: str
    prueba_id: str
    nombre_prueba: str
    controls: list[ControlSpec]
    source_file: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metod_id": self.metod_id,
            "prueba_id": self.prueba_id,
            "nombre_prueba": self.nombre_prueba,
            "source_file": self.source_file,
            "controls": [control.to_dict() for control in self.controls],
        }


@dataclass(frozen=True)
class ParsedDocument:
    source_file: str
    content_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceChunk:
    chunk_id: str
    source_file: str
    text: str
    metadata: dict[str, Any]
    text_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    source_file: str
    score: float
    text: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObservationResult:
    prueba_id: str
    nombre_prueba: str
    hay_observacion: bool
    criticidad: str | None
    observacion: str
    sustento: str
    controles_evaluados: list[str]
    controles_que_originan_observacion: list[str]
    evidencias_usadas: list[dict[str, Any]]
    informacion_faltante: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
