"""Extracción de landmarks corporales con MediaPipe Pose."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp

from .schemas import PoseFrame, PoseSequence, VideoRole
from .video import iter_video_frames, inspect_video


@dataclass(frozen=True, slots=True)
class PoseConfig:
    """Configuración reproducible del modelo usado por el MVP."""

    model_complexity: int = 0
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    expected_landmark_count: int = 33


class PoseExtractionError(RuntimeError):
    """Error durante la extracción de pose."""


def _landmarks_from_result(result: object) -> list[dict[str, float]] | None:
    pose_landmarks = getattr(result, "pose_landmarks", None)
    if pose_landmarks is None:
        return None
    return [
        {
            "landmark_id": landmark_id,
            "x": float(landmark.x),
            "y": float(landmark.y),
            "z": float(landmark.z),
            "visibility": float(landmark.visibility),
        }
        for landmark_id, landmark in enumerate(pose_landmarks.landmark)
    ]


def extract_pose(
    video_path: str | Path,
    role: VideoRole,
    *,
    config: PoseConfig | None = None,
    max_frames: int | None = None,
) -> PoseSequence:
    """Extrae pose y conserva todos los frames de la secuencia temporal."""

    config = config or PoseConfig()
    metadata = inspect_video(video_path, role)
    if metadata.fps <= 0:
        raise PoseExtractionError("El video no tiene un FPS válido")

    frames: list[PoseFrame] = []
    pose_module = mp.solutions.pose
    try:
        with pose_module.Pose(
            static_image_mode=False,
            model_complexity=config.model_complexity,
            enable_segmentation=False,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        ) as pose_model:
            for frame_index, timestamp_sec, frame in iter_video_frames(
                video_path,
                max_frames=max_frames,
            ):
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose_model.process(frame_rgb)
                landmarks = _landmarks_from_result(result)
                frames.append(
                    PoseFrame(
                        frame_index=frame_index,
                        timestamp_sec=round(timestamp_sec, 6),
                        detected=landmarks is not None,
                        landmarks=landmarks,
                    )
                )
    except Exception as error:
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        raise PoseExtractionError(
            f"No fue posible extraer pose de {Path(video_path).name}: {error}"
        ) from error

    return PoseSequence(
        source_video=Path(video_path).name,
        video_role=role,
        model="MediaPipe Pose",
        model_complexity=config.model_complexity,
        landmark_count=config.expected_landmark_count,
        fps=metadata.fps,
        frame_count=metadata.frame_count if max_frames is None else len(frames),
        frames=frames,
    )


def validate_pose_sequence(
    sequence: PoseSequence,
    *,
    expected_landmark_count: int = 33,
) -> list[str]:
    """Comprueba continuidad temporal y estructura de landmarks."""

    errors: list[str] = []
    frame_indices = [frame.frame_index for frame in sequence.frames]
    expected_indices = list(range(len(sequence.frames)))
    if frame_indices != expected_indices:
        errors.append("Los índices de frame no son consecutivos desde cero")
    timestamps = [frame.timestamp_sec for frame in sequence.frames]
    if timestamps != sorted(timestamps):
        errors.append("Los timestamps no están ordenados")
    if sequence.fps <= 0:
        errors.append("El FPS de la secuencia debe ser positivo")

    for frame in sequence.frames:
        if not frame.detected:
            if frame.landmarks is not None:
                errors.append(f"Frame {frame.frame_index} no detectado con landmarks")
            continue
        if frame.landmarks is None:
            errors.append(f"Frame {frame.frame_index} marcado como detectado sin landmarks")
            continue
        if len(frame.landmarks) != expected_landmark_count:
            errors.append(
                f"Frame {frame.frame_index} tiene {len(frame.landmarks)} landmarks; "
                f"se esperaban {expected_landmark_count}"
            )
    return errors
