"""Comparación corporal de secuencias alineadas por DTW."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Mapping, Sequence


BODY_PART_ORDER = ["head", "torso", "left_arm", "right_arm", "left_leg", "right_leg"]


class ComparisonError(ValueError):
    """Error en las secuencias o correspondencias comparadas."""


def landmarks_by_id(frame: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    """Indexa los landmarks de un frame por su identificador técnico."""

    landmarks = frame.get("landmarks")
    if landmarks is None:
        return {}
    return {int(landmark["landmark_id"]): dict(landmark) for landmark in landmarks}


def euclidean_2d(point_a: Mapping[str, float], point_b: Mapping[str, float]) -> float:
    """Distancia euclidiana en el plano visible normalizado XY."""

    return math.sqrt(
        (float(point_a["x"]) - float(point_b["x"])) ** 2
        + (float(point_a["y"]) - float(point_b["y"])) ** 2
    )


def euclidean_3d(point_a: Mapping[str, float], point_b: Mapping[str, float]) -> float:
    """Distancia euclidiana XYZ usada como diagnóstico espacial."""

    return math.sqrt(
        (float(point_a["x"]) - float(point_b["x"])) ** 2
        + (float(point_a["y"]) - float(point_b["y"])) ** 2
        + (float(point_a["z"]) - float(point_b["z"])) ** 2
    )


def _frame_lookup(feature_data: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    frames = {
        int(frame["frame_index"]): frame
        for frame in feature_data.get("frames", [])
    }
    if not frames:
        raise ComparisonError("Las features no contienen frames")
    return frames


def compare_aligned_frames(
    reference_features: Mapping[str, Any],
    execution_features: Mapping[str, Any],
    dtw_matches: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Compara todos los landmarks de cada par DTW, incluidos pares repetidos."""

    reference_frames = _frame_lookup(reference_features)
    execution_frames = _frame_lookup(execution_features)
    records: list[dict[str, Any]] = []

    for match in dtw_matches:
        reference_frame_index = int(match["reference_frame"])
        execution_frame_index = int(match["execution_frame"])
        reference_frame = reference_frames.get(reference_frame_index)
        execution_frame = execution_frames.get(execution_frame_index)
        if reference_frame is None or execution_frame is None:
            raise ComparisonError(
                f"El par DTW ({reference_frame_index}, {execution_frame_index}) no existe en features"
            )
        reference_landmarks = landmarks_by_id(reference_frame)
        execution_landmarks = landmarks_by_id(execution_frame)
        common_landmark_ids = sorted(set(reference_landmarks) & set(execution_landmarks))
        if not common_landmark_ids:
            continue

        for landmark_id in common_landmark_ids:
            reference_landmark = reference_landmarks[landmark_id]
            execution_landmark = execution_landmarks[landmark_id]
            records.append({
                "reference_frame": reference_frame_index,
                "execution_frame": execution_frame_index,
                "reference_timestamp_sec": float(match["reference_time_sec"]),
                "execution_timestamp_sec": float(match["execution_time_sec"]),
                "landmark_id": landmark_id,
                "landmark_name": reference_landmark.get("landmark_name", "unknown"),
                "body_part": reference_landmark.get("body_part", "unknown"),
                "difference_xy": euclidean_2d(reference_landmark, execution_landmark),
                "difference_xyz": euclidean_3d(reference_landmark, execution_landmark),
                "reference_visibility": float(reference_landmark.get("visibility", 0.0)),
                "execution_visibility": float(execution_landmark.get("visibility", 0.0)),
            })
    if not records:
        raise ComparisonError("No se pudieron comparar landmarks en los pares DTW")
    return records


def summarize_coordinate_differences(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Resume diferencias XY/XYZ por frame, parte corporal y landmark."""

    by_body_part: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_landmark: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_reference_frame: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_body_part[str(record["body_part"])].append(record)
        by_landmark[str(record["landmark_name"])].append(record)
        by_reference_frame[int(record["reference_frame"])].append(record)

    def summary(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        xy_values = [float(item["difference_xy"]) for item in items]
        xyz_values = [float(item["difference_xyz"]) for item in items]
        return {
            "mean_difference_xy": sum(xy_values) / len(xy_values),
            "max_difference_xy": max(xy_values),
            "mean_difference_xyz": sum(xyz_values) / len(xyz_values),
            "max_difference_xyz": max(xyz_values),
            "comparisons": len(items),
        }

    body_summary = {body_part: summary(items) for body_part, items in by_body_part.items()}
    landmark_summary = {landmark: summary(items) for landmark, items in by_landmark.items()}
    frame_summary = [
        {
            "reference_frame": frame_index,
            "reference_timestamp_sec": items[0]["reference_timestamp_sec"],
            "mean_difference_xy": sum(float(item["difference_xy"]) for item in items) / len(items),
            "max_difference_xy": max(float(item["difference_xy"]) for item in items),
            "mean_difference_xyz": sum(float(item["difference_xyz"]) for item in items) / len(items),
            "max_difference_xyz": max(float(item["difference_xyz"]) for item in items),
            "landmarks_compared": len(items),
        }
        for frame_index, items in sorted(by_reference_frame.items())
    ]
    return {
        "coordinate_difference_by_body_part": body_summary,
        "coordinate_difference_by_landmark": landmark_summary,
        "frame_difference_summary": frame_summary,
    }


def compare_angles(
    reference_features: Mapping[str, Any],
    execution_features: Mapping[str, Any],
    dtw_matches: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Resume diferencias absolutas de los ángulos en cada par DTW."""

    reference_frames = _frame_lookup(reference_features)
    execution_frames = _frame_lookup(execution_features)
    values_by_angle: dict[str, list[float]] = defaultdict(list)
    for match in dtw_matches:
        reference_frame = reference_frames[int(match["reference_frame"])]
        execution_frame = execution_frames[int(match["execution_frame"])]
        for angle_name in set(reference_frame.get("angles", {})) & set(execution_frame.get("angles", {})):
            reference_angle = reference_frame["angles"].get(angle_name)
            execution_angle = execution_frame["angles"].get(angle_name)
            if reference_angle is not None and execution_angle is not None:
                values_by_angle[angle_name].append(abs(float(reference_angle) - float(execution_angle)))
    return {
        angle_name: {
            "mean_difference_deg": sum(values) / len(values),
            "max_difference_deg": max(values),
            "frames_compared": len(values),
        }
        for angle_name, values in sorted(values_by_angle.items())
        if values
    }


def shoulder_orientation_deg(frame: Mapping[str, Any]) -> float | None:
    """Calcula la orientación visible de la línea de hombros."""

    landmarks = landmarks_by_id(frame)
    left = next((point for point in landmarks.values() if point.get("landmark_name") == "left_shoulder"), None)
    right = next((point for point in landmarks.values() if point.get("landmark_name") == "right_shoulder"), None)
    if left is None or right is None:
        return None
    return math.degrees(math.atan2(float(right["y"]) - float(left["y"]), float(right["x"]) - float(left["x"])))


def compare_orientation(
    reference_features: Mapping[str, Any],
    execution_features: Mapping[str, Any],
    dtw_matches: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Resume orientación de hombros y diferencia angular absoluta."""

    reference_frames = _frame_lookup(reference_features)
    execution_frames = _frame_lookup(execution_features)
    records: list[dict[str, Any]] = []
    for match in dtw_matches:
        reference_orientation = shoulder_orientation_deg(reference_frames[int(match["reference_frame"])])
        execution_orientation = shoulder_orientation_deg(execution_frames[int(match["execution_frame"])])
        if reference_orientation is None or execution_orientation is None:
            continue
        records.append({
            "reference_frame": int(match["reference_frame"]),
            "execution_frame": int(match["execution_frame"]),
            "reference_timestamp_sec": float(match["reference_time_sec"]),
            "execution_timestamp_sec": float(match["execution_time_sec"]),
            "reference_orientation_deg": reference_orientation,
            "execution_orientation_deg": execution_orientation,
            "absolute_difference_deg": abs(reference_orientation - execution_orientation),
        })
    differences = [record["absolute_difference_deg"] for record in records]
    return {
        "mean_difference_deg": sum(differences) / len(differences) if differences else None,
        "max_difference_deg": max(differences) if differences else None,
        "frames_compared": len(records),
        "records": records,
    }


def build_comparison(
    reference_features: Mapping[str, Any],
    execution_features: Mapping[str, Any],
    alignment: Mapping[str, Any],
) -> dict[str, Any]:
    """Construye el resumen de comparación usando todos los pares DTW."""

    dtw_matches = alignment.get("dtw_matches", [])
    if not dtw_matches:
        raise ComparisonError("El resultado DTW no contiene correspondencias")
    records = compare_aligned_frames(reference_features, execution_features, dtw_matches)
    coordinate_summary = summarize_coordinate_differences(records)
    angle_summary = compare_angles(reference_features, execution_features, dtw_matches)
    orientation_summary = compare_orientation(reference_features, execution_features, dtw_matches)

    top_findings = sorted(records, key=lambda item: item["difference_xy"], reverse=True)[:20]
    return {
        "reference_video": reference_features.get("source_video"),
        "execution_video": execution_features.get("source_video"),
        "reference_role": reference_features.get("video_role"),
        "execution_role": execution_features.get("video_role"),
        "reference_frame_count": reference_features.get("frame_count"),
        "execution_frame_count": execution_features.get("frame_count"),
        "reference_fps": reference_features.get("fps"),
        "execution_fps": execution_features.get("fps"),
        "common_frame_count": min(
            int(reference_features.get("frame_count", 0)),
            int(execution_features.get("frame_count", 0)),
        ),
        "comparable_frame_count": len({record["reference_frame"] for record in records}),
        "dtw_pair_count": len(dtw_matches),
        "coordinate_difference_records": records,
        **coordinate_summary,
        "angle_difference_summary": angle_summary,
        "orientation_summary": orientation_summary,
        "preliminary_findings": top_findings,
        "notes": [
            "Las diferencias corporales se calcularon sobre pares alineados por DTW.",
            "XY es la medida corporal visible principal; XYZ es diagnóstica y relativa.",
            "La comparación no evalúa calidad artística profesional.",
        ],
    }
