"""Orquestación del análisis completo de una sesión de Mitotl IA."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .alignment import DTWConfig, align_features
from .comparison import build_comparison
from .feedback import FeedbackConfig, build_feedback
from .features import build_features_from_pose
from .pose import PoseConfig, extract_pose
from .scoring import ScoreConfig, calculate_score
from .schemas import to_jsonable
from .video import (
    VideoPreparationConfig,
    VideoValidationConfig,
    prepare_video_for_analysis,
    validate_video_file,
)


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Configuración conjunta de las etapas analíticas."""

    video: VideoValidationConfig = VideoValidationConfig()
    preparation: VideoPreparationConfig = VideoPreparationConfig()
    pose: PoseConfig = PoseConfig()
    dtw: DTWConfig = DTWConfig()
    score: ScoreConfig = ScoreConfig()
    feedback: FeedbackConfig = FeedbackConfig()


class PipelineError(RuntimeError):
    """Error contextualizado por etapa del pipeline."""

    def __init__(self, stage: str, message: str, *, cause: Exception | None = None):
        self.stage = stage
        self.cause = cause
        super().__init__(f"[{stage}] {message}")


ProgressCallback = Callable[[str, float], None]


def analyze_session(
    reference_path: str | Path,
    execution_path: str | Path,
    *,
    config: PipelineConfig | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Procesa una sesión completa y devuelve un resultado JSON-compatible."""

    config = config or PipelineConfig()

    def notify(stage: str, progress: float) -> None:
        if progress_callback is not None:
            progress_callback(stage, progress)

    notify("Validando videos", 0.05)
    try:
        reference_metadata = validate_video_file(reference_path, "reference", config=config.video)
        execution_metadata = validate_video_file(execution_path, "execution", config=config.video)
    except Exception as error:
        raise PipelineError("video_validation", str(error), cause=error) from error

    notify("Preparando videos para el análisis", 0.09)
    try:
        reference_prepared = prepare_video_for_analysis(
            reference_path,
            "reference",
            metadata=reference_metadata,
            config=config.preparation,
        )
        execution_prepared = prepare_video_for_analysis(
            execution_path,
            "execution",
            metadata=execution_metadata,
            config=config.preparation,
        )
    except Exception as error:
        raise PipelineError("video_preparation", str(error), cause=error) from error

    preparation_summary = {
        "reference": {
            "target_fps": reference_prepared.target_fps,
            "resized": reference_prepared.resized,
            "original_duration_sec": reference_prepared.original_duration_sec,
            "prepared_metadata": to_jsonable(reference_prepared.prepared_metadata),
            "warning": reference_prepared.warning,
        },
        "execution": {
            "target_fps": execution_prepared.target_fps,
            "resized": execution_prepared.resized,
            "original_duration_sec": execution_prepared.original_duration_sec,
            "prepared_metadata": to_jsonable(execution_prepared.prepared_metadata),
            "warning": execution_prepared.warning,
        },
    }

    with ExitStack() as cleanup:
        cleanup.callback(reference_prepared.cleanup)
        cleanup.callback(execution_prepared.cleanup)

        notify("Extrayendo pose corporal", 0.12)
        try:
            reference_pose = extract_pose(reference_prepared.prepared_path, "reference", config=config.pose)
            execution_pose = extract_pose(execution_prepared.prepared_path, "execution", config=config.pose)
            reference_pose.source_video = reference_metadata.file_name
            execution_pose.source_video = execution_metadata.file_name
        except Exception as error:
            raise PipelineError("pose_extraction", str(error), cause=error) from error

        notify("Calculando variables corporales", 0.58)
        try:
            reference_features = build_features_from_pose(reference_pose)
            execution_features = build_features_from_pose(execution_pose)
        except Exception as error:
            raise PipelineError("feature_engineering", str(error), cause=error) from error

        notify("Alineando secuencias con DTW", 0.68)
        try:
            alignment = align_features(reference_features, execution_features, config=config.dtw)
        except Exception as error:
            raise PipelineError("temporal_alignment", str(error), cause=error) from error

        notify("Comparando movimiento corporal", 0.82)
        try:
            comparison = build_comparison(reference_features, execution_features, alignment)
        except Exception as error:
            raise PipelineError("body_comparison", str(error), cause=error) from error

        notify("Calculando score y recomendaciones", 0.93)
        try:
            score = calculate_score(comparison, alignment, config=config.score)
            feedback = build_feedback(score, config=config.feedback)
        except Exception as error:
            raise PipelineError("scoring_feedback", str(error), cause=error) from error

        notify("Análisis completado", 1.0)
        return {
            "status": "preliminary",
            "pipeline_completed": True,
            "reference": to_jsonable(reference_metadata),
            "execution": to_jsonable(execution_metadata),
            "preparation": preparation_summary,
            "pose": {
                "reference": to_jsonable(reference_pose),
                "execution": to_jsonable(execution_pose),
            },
            "features": {
                "reference": reference_features,
                "execution": execution_features,
            },
            "alignment": alignment,
            "comparison": comparison,
            "score": score,
            "feedback": feedback,
            "warnings": [
                warning
                for warning in (reference_prepared.warning, execution_prepared.warning)
                if warning
            ],
            "errors": [],
            "config": {
                "video": asdict(config.video),
                "preparation": asdict(config.preparation),
                "pose": asdict(config.pose),
                "dtw": asdict(config.dtw),
                "score": asdict(config.score),
                "feedback": asdict(config.feedback),
            },
        }
