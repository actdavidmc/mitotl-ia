"""Contratos de datos compartidos por el pipeline de Mitotl IA.

Los nombres técnicos conservan la estructura de los notebooks. Las etiquetas
en español se reservan para la interfaz y el agente.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence


VideoRole = Literal["reference", "execution"]
LandmarkMap = dict[str, dict[str, float]]
MetricMap = dict[str, float]


@dataclass(slots=True)
class VideoMetadata:
    """Metadatos técnicos de un video leído correctamente."""

    file_name: str
    path: str
    role: VideoRole
    extension: str
    frame_count: int
    fps: float
    width: int
    height: int
    duration_sec: float
    opened: bool = True
    file_size_bytes: int | None = None
    url: str | None = None


@dataclass(slots=True)
class PoseFrame:
    """Pose detectada o ausente, conservando la secuencia temporal."""

    frame_index: int
    timestamp_sec: float
    detected: bool
    landmarks: list[dict[str, float]] | None


@dataclass(slots=True)
class PoseSequence:
    """Secuencia completa de pose asociada a un video."""

    source_video: str
    video_role: VideoRole
    model: str
    model_complexity: int
    landmark_count: int
    fps: float
    frame_count: int
    frames: list[PoseFrame] = field(default_factory=list)


@dataclass(slots=True)
class FeatureFrame:
    """Variables corporales calculadas para un frame."""

    frame_index: int
    timestamp_sec: float
    normalized_landmarks: list[dict[str, float]] | None
    body_parts: dict[str, list[int]] = field(default_factory=dict)
    angles: MetricMap = field(default_factory=dict)
    angular_velocity: MetricMap = field(default_factory=dict)
    landmark_velocity: MetricMap = field(default_factory=dict)


@dataclass(slots=True)
class DTWMatch:
    """Correspondencia entre un frame de referencia y uno de ejecución."""

    reference_frame: int
    execution_frame: int
    reference_time_sec: float
    execution_time_sec: float


@dataclass(slots=True)
class DTWSegment:
    """Segmento temporal derivado del camino DTW."""

    segment: int
    reference_start_frame: int
    reference_end_frame: int
    execution_start_frame: int
    execution_end_frame: int
    reference_duration_sec: float
    execution_duration_sec: float
    time_shift_sec: float
    alignment_count: int
    duration_ratio: float | None = None
    temporal_similarity: float | None = None


@dataclass(slots=True)
class BodyScore:
    """Score corporal por grupo, manteniendo XY y XYZ separados."""

    body_part: str
    similarity_xy_percent: float
    similarity_xyz_percent: float | None = None
    mean_difference_xy: float | None = None
    mean_difference_xyz: float | None = None


@dataclass(slots=True)
class Finding:
    """Diferencia puntual alineada y su severidad."""

    reference_frame: int
    execution_frame: int
    reference_time_sec: float
    execution_time_sec: float
    landmark: str
    body_part: str
    difference_xy: float
    difference_xyz: float | None
    severity: str
    candidate_recommendation: str | None = None


@dataclass(slots=True)
class Recommendation:
    """Recomendación educativa generada por reglas."""

    recommendation_type: str
    recommendation: str
    body_part: str | None = None
    segment: int | None = None
    similarity_xy_percent: float | None = None
    temporal_similarity: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SessionScore:
    """Resultado cuantitativo de una sesión completa."""

    score_general: float
    weights: dict[str, float]
    body_scores_xy: dict[str, float]
    body_scores_xyz: dict[str, float]
    temporal_similarity: float
    segment_scores: list[DTWSegment] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    top_findings: list[Finding] = field(default_factory=list)
    all_findings_count: int = 0
    status: str = "preliminary"


@dataclass(slots=True)
class AgentContext:
    """Contexto compacto y controlado que recibe el agente."""

    reference_video: str
    execution_video: str
    score_general: float
    weights: dict[str, float]
    body_scores_xy: dict[str, float]
    body_scores_xyz: dict[str, float]
    temporal_similarity: float
    segment_scores: list[dict[str, Any]]
    top_findings: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    all_findings_count: int
    status: str


@dataclass(slots=True)
class SessionResult:
    """Contrato JSON-compatible del análisis completo."""

    reference: VideoMetadata
    execution: VideoMetadata
    pose: dict[str, list[PoseFrame]] = field(default_factory=dict)
    features: dict[str, list[FeatureFrame]] = field(default_factory=dict)
    dtw_matches: list[DTWMatch] = field(default_factory=list)
    dtw_segments: list[DTWSegment] = field(default_factory=list)
    comparison: dict[str, Any] = field(default_factory=dict)
    score: SessionScore | None = None
    agent_context: AgentContext | None = None
    agent_response: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    status: str = "created"


def to_jsonable(value: Any) -> Any:
    """Convierte contratos y contenedores anidados a estructuras JSON."""

    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_jsonable(item) for item in value]
    return value
