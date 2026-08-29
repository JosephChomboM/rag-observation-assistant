from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from pydantic import BaseModel


Criticality = Literal[
    "Critico", "Relevante", "Moderado", "Baja", "Potencial", "No concluyente"
]


class EvidenceReference(BaseModel):
    archivo: str
    chunk_id: str
    score: float


class ObservationPayload(BaseModel):
    control_id: str
    sustento_suficiente: bool
    insumo_parcial: bool
    hay_observacion: bool
    criticidad: Criticality | None
    observacion: str
    sustento: str
    evidencias_usadas: list[EvidenceReference]
    informacion_faltante: list[str]



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
    """One observation per control. Pruebas only group controls for reading."""

    prueba_id: str
    nombre_prueba: str
    control_id: str
    detalle: str
    hay_observacion: bool
    criticidad: str | None
    observacion: str
    sustento: str
    evidencias_usadas: list[dict[str, Any]]
    informacion_faltante: list[str]
    sustento_suficiente: bool = True
    insumo_parcial: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
