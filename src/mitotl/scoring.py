"""Cálculo de score corporal, score temporal y fórmula general del MVP."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


BODY_PART_GROUPS = {
    "arms": ["left_arm", "right_arm"],
    "legs": ["left_leg", "right_leg"],
    "torso": ["torso"],
    "head": ["head"],
}


@dataclass(frozen=True, slots=True)
class ScoreConfig:
    """Pesos explícitos del score general."""

    body_weight: float = 0.80
    temporal_weight: float = 0.20

    def validate(self) -> None:
        if self.body_weight < 0 or self.temporal_weight < 0:
            raise ScoreError("Los pesos del score no pueden ser negativos")
        if abs((self.body_weight + self.temporal_weight) - 1.0) > 1e-9:
            raise ScoreError("Los pesos del score deben sumar 1.0")


class ScoreError(ValueError):
    """Error en los insumos o en la configuración del score."""


def difference_to_similarity(difference: float) -> float:
    """Convierte una diferencia no negativa a similitud en [0, 1]."""

    return 1.0 / (1.0 + max(float(difference), 0.0))


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ScoreError("No hay valores para calcular el promedio")
    return sum(values) / len(values)


def _build_pair_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[tuple[int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_pair[(int(record["reference_frame"]), int(record["execution_frame"]))].append(record)

    pair_records: list[dict[str, Any]] = []
    for (reference_frame, execution_frame), pair_landmarks in sorted(by_pair.items()):
        body_xy: dict[str, list[float]] = defaultdict(list)
        body_xyz: dict[str, list[float]] = defaultdict(list)
        landmarks: dict[str, dict[str, Any]] = {}
        for landmark in pair_landmarks:
            body_part = str(landmark["body_part"])
            difference_xy = float(landmark["difference_xy"])
            difference_xyz = float(landmark["difference_xyz"])
            body_xy[body_part].append(difference_xy)
            body_xyz[body_part].append(difference_xyz)
            landmarks[str(landmark["landmark_id"])] = {
                "landmark_name": landmark["landmark_name"],
                "body_part": body_part,
                "difference_xy": difference_xy,
                "difference_xyz": difference_xyz,
                "difference": difference_xy,
            }
        body_differences_xy = {part: _mean(values) for part, values in body_xy.items()}
        body_differences_xyz = {part: _mean(values) for part, values in body_xyz.items()}
        frame_difference_xy = _mean(list(body_differences_xy.values()))
        frame_difference_xyz = _mean(list(body_differences_xyz.values()))
        first = pair_landmarks[0]
        pair_records.append({
            "reference_frame": reference_frame,
            "execution_frame": execution_frame,
            "reference_time_sec": float(first["reference_timestamp_sec"]),
            "execution_time_sec": float(first["execution_timestamp_sec"]),
            "body_differences_xy": body_differences_xy,
            "body_differences_xyz": body_differences_xyz,
            "frame_difference_xy": frame_difference_xy,
            "frame_difference_xyz": frame_difference_xyz,
            "frame_similarity": difference_to_similarity(frame_difference_xy),
            "frame_similarity_xyz": difference_to_similarity(frame_difference_xyz),
            "landmarks": landmarks,
        })
    return pair_records


def _reference_frame_summary(pair_records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for record in pair_records:
        grouped[int(record["reference_frame"])].append(record)
    summaries: list[dict[str, Any]] = []
    for reference_frame, records in sorted(grouped.items()):
        body_parts = records[0]["body_differences_xy"].keys()
        body_difference_xy = {
            part: _mean([float(record["body_differences_xy"][part]) for record in records])
            for part in body_parts
        }
        body_difference_xyz = {
            part: _mean([float(record["body_differences_xyz"][part]) for record in records])
            for part in records[0]["body_differences_xyz"]
        }
        frame_difference_xy = _mean([float(record["frame_difference_xy"]) for record in records])
        frame_difference_xyz = _mean([float(record["frame_difference_xyz"]) for record in records])
        summaries.append({
            "reference_frame": reference_frame,
            "reference_time_sec": records[0]["reference_time_sec"],
            "aligned_pair_count": len(records),
            "body_differences_xy": body_difference_xy,
            "body_differences_xyz": body_difference_xyz,
            "frame_difference_xy": frame_difference_xy,
            "frame_difference_xyz": frame_difference_xyz,
            "frame_similarity": difference_to_similarity(frame_difference_xy),
            "frame_similarity_xyz": difference_to_similarity(frame_difference_xyz),
        })
    return summaries


def _body_similarities(reference_summary: Sequence[Mapping[str, Any]]) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    if not reference_summary:
        raise ScoreError("No hay frames resumidos para calcular similitud corporal")
    body_parts = reference_summary[0]["body_differences_xy"].keys()
    differences_xy = {
        part: _mean([float(record["body_differences_xy"][part]) for record in reference_summary])
        for part in body_parts
    }
    differences_xyz = {
        part: _mean([float(record["body_differences_xyz"][part]) for record in reference_summary])
        for part in reference_summary[0]["body_differences_xyz"]
    }
    similarities_xy = {part: difference_to_similarity(value) for part, value in differences_xy.items()}
    similarities_xyz = {part: difference_to_similarity(value) for part, value in differences_xyz.items()}
    return differences_xy, differences_xyz, similarities_xy, similarities_xyz


def _group_scores(similarities: Mapping[str, float]) -> dict[str, float]:
    missing = {
        part for parts in BODY_PART_GROUPS.values() for part in parts
        if part not in similarities
    }
    if missing:
        raise ScoreError(f"Faltan partes corporales para el score: {sorted(missing)}")
    return {
        group: _mean([float(similarities[body_part]) for body_part in body_parts]) * 100
        for group, body_parts in BODY_PART_GROUPS.items()
    }


def _segment_scores(
    alignment: Mapping[str, Any],
    dtw_matches: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    matches_by_reference: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for match in dtw_matches:
        matches_by_reference[int(match["reference_frame"])].append(match)
    segment_scores: list[dict[str, Any]] = []
    for segment in alignment.get("segments", []):
        reference_frames = range(
            int(segment["reference_start_frame"]),
            int(segment["reference_end_frame"]) + 1,
        )
        segment_matches = [match for frame in reference_frames for match in matches_by_reference.get(frame, [])]
        reference_times = [float(match["reference_time_sec"]) for match in segment_matches]
        execution_times = [float(match["execution_time_sec"]) for match in segment_matches]
        segment_scores.append({
            "segment": int(segment["segment"]),
            "reference_start_frame": int(segment["reference_start_frame"]),
            "reference_end_frame": int(segment["reference_end_frame"]),
            "execution_start_frame": int(segment["execution_start_frame"]),
            "execution_end_frame": int(segment["execution_end_frame"]),
            "reference_start_time_sec": min(reference_times) if reference_times else None,
            "reference_end_time_sec": max(reference_times) if reference_times else None,
            "execution_start_time_sec": min(execution_times) if execution_times else None,
            "execution_end_time_sec": max(execution_times) if execution_times else None,
            "reference_duration_sec": float(segment["reference_duration_sec"]),
            "execution_duration_sec": float(segment["execution_duration_sec"]),
            "temporal_similarity": float(segment["temporal_similarity"]),
            "duration_ratio": float(segment["duration_ratio"]),
            "time_shift_sec": float(segment["time_shift_sec"]),
            "alignment_count": int(segment["alignment_count"]),
        })
    if not segment_scores:
        raise ScoreError("El resultado DTW no contiene segmentos")
    return segment_scores


def calculate_score(
    comparison: Mapping[str, Any],
    alignment: Mapping[str, Any],
    *,
    config: ScoreConfig | None = None,
) -> dict[str, Any]:
    """Calcula score corporal, temporal y general sobre resultados alineados."""

    config = config or ScoreConfig()
    config.validate()
    records = comparison.get("coordinate_difference_records", [])
    if not records:
        raise ScoreError("La comparación no contiene diferencias por landmark")
    dtw_matches = alignment.get("dtw_matches", [])
    if not dtw_matches:
        raise ScoreError("La alineación no contiene pares DTW")

    pair_records = _build_pair_records(records)
    reference_summary = _reference_frame_summary(pair_records)
    differences_xy, differences_xyz, similarities_xy, similarities_xyz = _body_similarities(reference_summary)
    body_scores_xy = {group: round(score, 2) for group, score in _group_scores(similarities_xy).items()}
    body_scores_xyz = {group: round(score, 2) for group, score in _group_scores(similarities_xyz).items()}
    # El score general usa los cuatro grupos del MVP (brazos, piernas, torso
    # y cabeza), no el promedio directo de las seis partes izquierda/derecha.
    grouped_body_scores_xy = _group_scores(similarities_xy)
    body_similarity_overall = _mean([score / 100 for score in grouped_body_scores_xy.values()])
    temporal_similarity = float(alignment["temporal_similarity"])
    score_general = 100 * (
        config.body_weight * body_similarity_overall
        + config.temporal_weight * temporal_similarity
    )
    segment_scores = _segment_scores(alignment, dtw_matches)

    return {
        "reference_video": comparison.get("reference_video"),
        "execution_video": comparison.get("execution_video"),
        "score_general": round(score_general, 2),
        "weights": {"body": config.body_weight, "temporal": config.temporal_weight},
        "body_scores_xy": body_scores_xy,
        "body_scores_xyz": body_scores_xyz,
        "body_similarity_overall": body_similarity_overall,
        "coordinate_differences_xy": differences_xy,
        "coordinate_differences_xyz": differences_xyz,
        "body_similarity_by_part_xy": similarities_xy,
        "body_similarity_by_part_xyz": similarities_xyz,
        "temporal_similarity": temporal_similarity,
        "segment_scores": segment_scores,
        "frame_similarity_records": pair_records,
        "reference_frame_summary": reference_summary,
        "status": "preliminary",
    }
