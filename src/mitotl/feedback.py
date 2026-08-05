"""Reglas trazables de severidad, prioridades y recomendaciones educativas."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .scoring import difference_to_similarity


RECOMMENDATIONS_BY_BODY_PART = {
    "head": "Revisar la orientación de la cabeza.",
    "torso": "Revisar la inclinación y estabilidad del torso.",
    "left_arm": "Revisar la trayectoria del brazo izquierdo.",
    "right_arm": "Revisar la trayectoria del brazo derecho.",
    "left_leg": "Revisar la posición y trayectoria de la pierna izquierda.",
    "right_leg": "Revisar la posición y trayectoria de la pierna derecha.",
}


@dataclass(frozen=True, slots=True)
class FeedbackConfig:
    """Parámetros de presentación de hallazgos y reglas."""

    top_findings_count: int = 20
    weak_segment_threshold: float = 0.60
    top_landmarks_per_body_part: int = 3


class FeedbackError(ValueError):
    """Error en los datos necesarios para generar feedback."""


def _percentile(values: Sequence[float], proportion: float) -> float:
    if not values:
        raise FeedbackError("No hay diferencias para calcular severidades")
    if not 0 <= proportion <= 1:
        raise FeedbackError("La proporción del percentil debe estar entre 0 y 1")
    index = int((len(values) - 1) * proportion)
    return sorted(values)[index]


def _classify_difference(value: float, medium_threshold: float, high_threshold: float) -> str:
    if value >= high_threshold:
        return "Alta"
    if value >= medium_threshold:
        return "Media"
    return "Baja"


def _flatten_findings(score: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for record in score.get("frame_similarity_records", []):
        for landmark_id, landmark_data in record.get("landmarks", {}).items():
            body_part = landmark_data.get("body_part", "unknown")
            if body_part not in RECOMMENDATIONS_BY_BODY_PART:
                continue
            findings.append({
                "reference_frame": int(record["reference_frame"]),
                "execution_frame": int(record["execution_frame"]),
                "reference_time_sec": float(record["reference_time_sec"]),
                "execution_time_sec": float(record["execution_time_sec"]),
                "landmark_id": int(landmark_id),
                "landmark": landmark_data["landmark_name"],
                "body_part": body_part,
                "difference_xy": float(landmark_data["difference_xy"]),
                "difference_xyz": float(landmark_data["difference_xyz"]),
            })
    if not findings:
        raise FeedbackError("No hay diferencias por landmark para generar hallazgos")
    return sorted(findings, key=lambda finding: finding["difference_xy"], reverse=True)


def build_findings(score: Mapping[str, Any], *, config: FeedbackConfig | None = None) -> dict[str, Any]:
    """Clasifica todos los hallazgos y devuelve un resumen principal."""

    config = config or FeedbackConfig()
    if config.top_findings_count < 1 or config.top_landmarks_per_body_part < 1:
        raise FeedbackError("Las cantidades de hallazgos y landmarks deben ser positivas")
    sorted_findings = _flatten_findings(score)
    difference_values = [finding["difference_xy"] for finding in sorted_findings]
    medium_threshold = _percentile(difference_values, 0.50)
    high_threshold = _percentile(difference_values, 0.80)
    all_findings = [
        {
            "reference_frame": finding["reference_frame"],
            "execution_frame": finding["execution_frame"],
            "reference_time_sec": round(finding["reference_time_sec"], 3),
            "execution_time_sec": round(finding["execution_time_sec"], 3),
            "landmark": finding["landmark"],
            "parte_cuerpo": finding["body_part"],
            "diferencia_xy": round(finding["difference_xy"], 4),
            "diferencia_xyz": round(finding["difference_xyz"], 4),
            "severidad": _classify_difference(finding["difference_xy"], medium_threshold, high_threshold),
            "recomendacion_candidata": RECOMMENDATIONS_BY_BODY_PART[finding["body_part"]],
        }
        for finding in sorted_findings
    ]
    return {
        "all_findings": all_findings,
        "top_findings": all_findings[:config.top_findings_count],
        "severity_thresholds": {
            "medium": medium_threshold,
            "high": high_threshold,
        },
    }


def build_recommendations(
    score: Mapping[str, Any],
    *,
    findings: Mapping[str, Any] | None = None,
    config: FeedbackConfig | None = None,
) -> list[dict[str, Any]]:
    """Genera recomendaciones corporales y temporales mediante reglas."""

    config = config or FeedbackConfig()
    findings = findings or build_findings(score, config=config)
    all_findings = findings.get("all_findings", [])
    by_body_part: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in all_findings:
        by_body_part[finding["parte_cuerpo"]].append(finding)

    recommendations: list[dict[str, Any]] = []
    for body_part, body_findings in by_body_part.items():
        mean_difference = sum(item["diferencia_xy"] for item in body_findings) / len(body_findings)
        high_findings = [item for item in body_findings if item["severidad"] == "Alta"]
        by_landmark: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for finding in body_findings:
            by_landmark[finding["landmark"]].append(finding)
        landmark_summary = []
        for landmark_name, landmark_findings in by_landmark.items():
            landmark_summary.append({
                "landmark": landmark_name,
                "mean_difference_xy": sum(item["diferencia_xy"] for item in landmark_findings) / len(landmark_findings),
                "max_difference_xy": max(item["diferencia_xy"] for item in landmark_findings),
                "aligned_pairs_affected": len(landmark_findings),
                "reference_frames_affected": len({item["reference_frame"] for item in landmark_findings}),
                "execution_frames_affected": len({item["execution_frame"] for item in landmark_findings}),
            })
        landmark_summary.sort(key=lambda item: item["mean_difference_xy"], reverse=True)
        recommendations.append({
            "type": "body_part",
            "body_part": body_part,
            "mean_difference_xy": round(mean_difference, 4),
            "similarity_xy_percent": round(difference_to_similarity(mean_difference) * 100, 2),
            "high_severity_count": len(high_findings),
            "top_landmarks": landmark_summary[:config.top_landmarks_per_body_part],
            "recommendation": RECOMMENDATIONS_BY_BODY_PART[body_part],
        })

    recommendations.sort(key=lambda item: item["mean_difference_xy"], reverse=True)
    for segment in score.get("segment_scores", []):
        if float(segment["temporal_similarity"]) < config.weak_segment_threshold:
            recommendations.append({
                "type": "temporal_segment",
                "segment": int(segment["segment"]),
                "temporal_similarity": float(segment["temporal_similarity"]),
                "reference_start_time_sec": segment.get("reference_start_time_sec"),
                "reference_end_time_sec": segment.get("reference_end_time_sec"),
                "execution_start_time_sec": segment.get("execution_start_time_sec"),
                "execution_end_time_sec": segment.get("execution_end_time_sec"),
                "recommendation": "Revisar el ritmo y la sincronización en este segmento.",
            })
    return recommendations


def build_feedback(score: Mapping[str, Any], *, config: FeedbackConfig | None = None) -> dict[str, Any]:
    """Construye hallazgos y recomendaciones listos para la plataforma."""

    findings = build_findings(score, config=config)
    recommendations = build_recommendations(score, findings=findings, config=config)
    return {
        **findings,
        "recommendations": recommendations,
        "all_findings_count": len(findings["all_findings"]),
        "recommendations_count": len(recommendations),
    }
