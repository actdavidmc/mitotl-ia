"""Alineación temporal y segmentación con Dynamic Time Warping."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from statistics import mean, pstdev
from typing import Any, Mapping, Sequence

import numpy as np
from dtaidistance import dtw_ndim

from .schemas import DTWMatch, DTWSegment


ANGLE_ORDER = [
    "left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
    "left_knee", "right_knee", "left_hip", "right_hip",
]

MAX_INTERPOLATED_GAP_SEC = 2.0


@dataclass(frozen=True, slots=True)
class DTWConfig:
    """Parámetros configurables de la alineación temporal."""

    window: int | None = None
    use_pruning: bool = False
    segment_duration_sec: float = 2.0


class AlignmentError(ValueError):
    """Error en las entradas o en el cálculo de la alineación."""


def build_angle_sequence(feature_data: Mapping[str, Any]) -> tuple[list[int], list[float], list[list[float]]]:
    """Construye ángulos y rellena ausencias breves entre frames válidos.

    MediaPipe puede perder una detección aislada aunque el video sea utilizable.
    Esas ausencias se interpolan temporalmente; los huecos largos se rechazan
    para no fabricar una trayectoria corporal poco confiable.
    """

    frame_indices: list[int] = []
    timestamps: list[float] = []
    raw_vectors: list[list[float] | None] = []
    for frame in feature_data.get("frames", []):
        missing_angles = [
            angle_name for angle_name in ANGLE_ORDER
            if frame.get("angles", {}).get(angle_name) is None
        ]
        frame_indices.append(int(frame["frame_index"]))
        timestamps.append(float(frame["timestamp_sec"]))
        raw_vectors.append(
            None
            if not frame.get("detected") or missing_angles
            else [float(frame["angles"][angle_name]) for angle_name in ANGLE_ORDER]
        )

    if not raw_vectors:
        raise AlignmentError("La secuencia de features no contiene frames")

    valid_positions = [index for index, vector in enumerate(raw_vectors) if vector is not None]
    if not valid_positions:
        raise AlignmentError("La secuencia no contiene frames con ángulos válidos")

    angle_vectors: list[list[float]] = []
    missing_runs: list[tuple[int, int]] = []
    run_start: int | None = None
    for index, vector in enumerate(raw_vectors):
        if vector is None and run_start is None:
            run_start = index
        elif vector is not None and run_start is not None:
            missing_runs.append((run_start, index - 1))
            run_start = None
    if run_start is not None:
        missing_runs.append((run_start, len(raw_vectors) - 1))

    interpolated: dict[int, list[float]] = {}
    for start, end in missing_runs:
        left = start - 1 if start > 0 else None
        right = end + 1 if end + 1 < len(raw_vectors) else None
        left_time = timestamps[left] if left is not None else timestamps[right]  # type: ignore[index]
        right_time = timestamps[right] if right is not None else timestamps[left]  # type: ignore[index]
        gap_duration = abs(float(right_time) - float(left_time))
        if gap_duration > MAX_INTERPOLATED_GAP_SEC:
            raise AlignmentError(
                f"Hueco de pose demasiado largo ({gap_duration:.2f} s) entre los frames "
                f"{frame_indices[start]} y {frame_indices[end]}"
            )

        left_vector = raw_vectors[left] if left is not None else None
        right_vector = raw_vectors[right] if right is not None else None
        for index in range(start, end + 1):
            if left_vector is not None and right_vector is not None:
                ratio = (timestamps[index] - timestamps[left]) / (timestamps[right] - timestamps[left])
                interpolated[index] = [
                    left_value + ratio * (right_value - left_value)
                    for left_value, right_value in zip(left_vector, right_vector)
                ]
            elif left_vector is not None:
                interpolated[index] = list(left_vector)
            elif right_vector is not None:
                interpolated[index] = list(right_vector)

    for index, vector in enumerate(raw_vectors):
        angle_vectors.append(list(vector) if vector is not None else interpolated[index])

    return frame_indices, timestamps, angle_vectors


def standardize_angle_sequences(
    reference_sequence: Sequence[Sequence[float]],
    execution_sequence: Sequence[Sequence[float]],
) -> tuple[list[list[float]], list[list[float]], dict[str, dict[str, float]]]:
    """Estandariza cada ángulo usando media y desviación combinadas."""

    if not reference_sequence or not execution_sequence:
        raise AlignmentError("Ambas secuencias deben contener datos")
    combined = list(reference_sequence) + list(execution_sequence)
    stats: dict[str, dict[str, float]] = {}
    for angle_index, angle_name in enumerate(ANGLE_ORDER):
        values = [float(vector[angle_index]) for vector in combined]
        standard_deviation = pstdev(values)
        stats[angle_name] = {
            "mean": mean(values),
            "std": standard_deviation if standard_deviation > 0 else 1.0,
        }

    def scale(sequence: Sequence[Sequence[float]]) -> list[list[float]]:
        return [
            [
                (float(value) - stats[angle_name]["mean"]) / stats[angle_name]["std"]
                for angle_name, value in zip(ANGLE_ORDER, vector)
            ]
            for vector in sequence
        ]

    return scale(reference_sequence), scale(execution_sequence), stats


def calculate_dtw(
    reference_sequence: Sequence[Sequence[float]],
    execution_sequence: Sequence[Sequence[float]],
    config: DTWConfig | None = None,
) -> tuple[float, list[tuple[int, int]]]:
    """Calcula distancia y camino DTW sobre secuencias angulares escaladas."""

    config = config or DTWConfig()
    if config.window is not None and config.window < 1:
        raise AlignmentError("La ventana DTW debe ser positiva o None")
    if config.segment_duration_sec <= 0:
        raise AlignmentError("segment_duration_sec debe ser positivo")

    reference_array = np.asarray(reference_sequence, dtype=np.double)
    execution_array = np.asarray(execution_sequence, dtype=np.double)
    if reference_array.ndim != 2 or execution_array.ndim != 2:
        raise AlignmentError("Las secuencias DTW deben ser matrices 2D")
    if reference_array.shape[1] != len(ANGLE_ORDER) or execution_array.shape[1] != len(ANGLE_ORDER):
        raise AlignmentError("La representación DTW debe contener exactamente 8 ángulos")

    distance = float(
        dtw_ndim.distance_fast(
            reference_array,
            execution_array,
            window=config.window,
            use_pruning=config.use_pruning,
        )
    )
    path = [(int(reference_index), int(execution_index)) for reference_index, execution_index in dtw_ndim.warping_path(reference_array, execution_array)]
    if not path:
        raise AlignmentError("DTW devolvió un camino vacío")
    return distance, path


def build_dtw_matches(
    path: Sequence[tuple[int, int]],
    reference_indices: Sequence[int],
    reference_timestamps: Sequence[float],
    execution_indices: Sequence[int],
    execution_timestamps: Sequence[float],
) -> list[DTWMatch]:
    """Convierte índices internos de DTW en correspondencias temporales."""

    matches: list[DTWMatch] = []
    for reference_position, execution_position in path:
        try:
            matches.append(
                DTWMatch(
                    reference_frame=int(reference_indices[reference_position]),
                    execution_frame=int(execution_indices[execution_position]),
                    reference_time_sec=float(reference_timestamps[reference_position]),
                    execution_time_sec=float(execution_timestamps[execution_position]),
                )
            )
        except IndexError as error:
            raise AlignmentError("El camino DTW contiene un índice fuera de rango") from error
    return matches


def build_segments(
    matches: Sequence[DTWMatch],
    reference_timestamps: Sequence[float],
    reference_frame_count: int,
    *,
    segment_duration_sec: float = 2.0,
) -> list[DTWSegment]:
    """Divide la referencia en segmentos temporales y proyecta el camino DTW."""

    if not matches or not reference_timestamps or reference_frame_count < 1:
        raise AlignmentError("No hay información suficiente para construir segmentos")
    if segment_duration_sec <= 0:
        raise AlignmentError("segment_duration_sec debe ser positivo")

    segment_count = math.ceil(reference_timestamps[-1] / segment_duration_sec)
    segment_size = reference_frame_count / segment_count
    segments: list[DTWSegment] = []

    for segment_index in range(segment_count):
        start_frame = int(segment_index * segment_size)
        end_frame = (
            reference_frame_count - 1
            if segment_index == segment_count - 1
            else int((segment_index + 1) * segment_size) - 1
        )
        segment_matches = [
            match for match in matches
            if start_frame <= match.reference_frame <= end_frame
        ]
        if not segment_matches:
            continue

        reference_times = [match.reference_time_sec for match in segment_matches]
        execution_times = [match.execution_time_sec for match in segment_matches]
        reference_duration = max(reference_times) - min(reference_times)
        execution_duration = max(execution_times) - min(execution_times)
        reference_midpoint = (min(reference_times) + max(reference_times)) / 2
        execution_midpoint = (min(execution_times) + max(execution_times)) / 2
        ratio = execution_duration / reference_duration if reference_duration > 0 else 1.0

        segments.append(
            DTWSegment(
                segment=segment_index + 1,
                reference_start_frame=start_frame,
                reference_end_frame=end_frame,
                execution_start_frame=segment_matches[0].execution_frame,
                execution_end_frame=segment_matches[-1].execution_frame,
                reference_duration_sec=reference_duration,
                execution_duration_sec=execution_duration,
                time_shift_sec=execution_midpoint - reference_midpoint,
                alignment_count=len(segment_matches),
                duration_ratio=ratio,
                temporal_similarity=min(ratio, 1 / ratio) if ratio > 0 else 0.0,
            )
        )
    return segments


def align_features(
    reference_features: Mapping[str, Any],
    execution_features: Mapping[str, Any],
    *,
    config: DTWConfig | None = None,
) -> dict[str, Any]:
    """Ejecuta el flujo completo de DTW y devuelve un resultado JSON-compatible."""

    config = config or DTWConfig()
    if reference_features.get("video_role") != "reference":
        raise AlignmentError("Las features de referencia no tienen el rol esperado")
    if execution_features.get("video_role") != "execution":
        raise AlignmentError("Las features de ejecución no tienen el rol esperado")

    required_groups = {"normalized_landmarks", "angles", "angular_velocity", "landmark_velocity"}
    for feature_data, label in ((reference_features, "referencia"), (execution_features, "ejecución")):
        missing_groups = required_groups - set(feature_data.get("feature_groups", []))
        if missing_groups:
            raise AlignmentError(f"Faltan grupos en {label}: {sorted(missing_groups)}")

    reference_indices, reference_timestamps, reference_sequence = build_angle_sequence(reference_features)
    execution_indices, execution_timestamps, execution_sequence = build_angle_sequence(execution_features)
    reference_scaled, execution_scaled, scaling_stats = standardize_angle_sequences(
        reference_sequence, execution_sequence
    )
    distance, path = calculate_dtw(reference_scaled, execution_scaled, config)
    matches = build_dtw_matches(
        path,
        reference_indices,
        reference_timestamps,
        execution_indices,
        execution_timestamps,
    )
    segments = build_segments(
        matches,
        reference_timestamps,
        len(reference_sequence),
        segment_duration_sec=config.segment_duration_sec,
    )
    temporal_values = [segment.temporal_similarity for segment in segments if segment.temporal_similarity is not None]
    temporal_similarity = sum(temporal_values) / len(temporal_values) if temporal_values else 0.0

    return {
        "reference_file": reference_features.get("source_video"),
        "execution_file": execution_features.get("source_video"),
        "reference_frame_count": len(reference_sequence),
        "execution_frame_count": len(execution_sequence),
        "reference_fps": reference_features.get("fps"),
        "execution_fps": execution_features.get("fps"),
        "angle_order": ANGLE_ORDER,
        "angle_scaling_stats": scaling_stats,
        "dtw_window": config.window,
        "dtw_use_pruning": config.use_pruning,
        "dtw_distance": distance,
        "dtw_path": [list(pair) for pair in path],
        "dtw_matches": [asdict(match) for match in matches],
        "segments": [asdict(segment) for segment in segments],
        "temporal_similarity": temporal_similarity,
    }
