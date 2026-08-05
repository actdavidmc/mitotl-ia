"""Utilidades para visualizaciones comparativas de una sesión."""

from __future__ import annotations

import tempfile
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import cv2


class VisualizationError(RuntimeError):
    """Error al preparar una visualización o clip."""


# Conexiones principales de MediaPipe Pose para dibujar el esqueleto.
SKELETON_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (11, 23), (12, 24),
    (23, 24), (23, 25), (25, 27), (27, 29), (27, 31), (24, 26), (26, 28),
    (28, 30), (28, 32), (11, 24),
)


def _difference_to_similarity(difference: float) -> float:
    return 1.0 / (1.0 + max(float(difference), 0.0))


def _similarity_color(similarity: float) -> tuple[int, int, int]:
    """Devuelve BGR: rojo para diferencia, verde para similitud."""

    similarity = min(max(float(similarity), 0.0), 1.0)
    return (0, int(255 * similarity), int(255 * (1.0 - similarity)))


def select_high_severity_moments(
    findings: list[Mapping[str, Any]],
    *,
    max_moments: int = 3,
    grouping_window_sec: float = 0.45,
) -> list[dict[str, Any]]:
    """Agrupa hallazgos cercanos y conserva los momentos más representativos."""

    ordered = sorted(
        findings,
        key=lambda item: (
            0 if str(item.get("severidad", "")).lower() == "alta" else 1,
            -float(item.get("diferencia_xy", 0)),
        ),
    )
    selected: list[dict[str, Any]] = []
    for finding in ordered:
        reference_time = float(finding.get("reference_time_sec", 0))
        if any(abs(reference_time - item["reference_time_sec"]) <= grouping_window_sec for item in selected):
            continue
        selected.append({
            "reference_time_sec": reference_time,
            "execution_time_sec": float(finding.get("execution_time_sec", 0)),
            "reference_frame": int(finding.get("reference_frame", 0)),
            "execution_frame": int(finding.get("execution_frame", 0)),
            "landmark": finding.get("landmark", "—"),
            "body_part": finding.get("parte_cuerpo", finding.get("body_part", "—")),
            "difference": float(finding.get("diferencia_xy", finding.get("difference_xy", 0))),
            "severity": finding.get("severidad", "—"),
        })
        if len(selected) >= max_moments:
            break
    return selected


def _video_properties(video_path: str | Path) -> tuple[float, int, int, int]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise VisualizationError(f"No fue posible abrir el video: {Path(video_path).name}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    if fps <= 0 or width <= 0 or height <= 0 or frame_count <= 0:
        raise VisualizationError(f"Metadatos inválidos para: {Path(video_path).name}")
    return fps, width, height, frame_count


def _fit_frame(frame: Any, panel_width: int, panel_height: int) -> Any:
    """Ajusta un frame a un panel sin deformarlo."""

    source_height, source_width = frame.shape[:2]
    scale = min(panel_width / source_width, panel_height / source_height)
    width = max(2, int(round(source_width * scale)))
    height = max(2, int(round(source_height * scale)))
    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    panel = cv2.copyMakeBorder(
        resized,
        (panel_height - height) // 2,
        panel_height - height - (panel_height - height) // 2,
        (panel_width - width) // 2,
        panel_width - width - (panel_width - width) // 2,
        cv2.BORDER_CONSTANT,
        value=(18, 18, 18),
    )
    return panel


def _frame_map(frames: Sequence[Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
    return {int(frame["frame_index"]): frame for frame in frames}


def _dtw_execution_by_reference(alignment: Mapping[str, Any]) -> dict[int, int]:
    matches: dict[int, list[int]] = defaultdict(list)
    for pair in alignment.get("dtw_path", []):
        if len(pair) >= 2:
            matches[int(pair[0])].append(int(pair[1]))
    return {reference: int(round(median(executions))) for reference, executions in matches.items()}


def _records_by_pair(records: Sequence[Mapping[str, Any]]) -> dict[tuple[int, int], Mapping[str, Any]]:
    return {
        (int(record["reference_frame"]), int(record["execution_frame"])): record
        for record in records
    }


def _read_frame_monotonic(capture: cv2.VideoCapture, target_index: int, state: dict[str, int]) -> Any | None:
    """Lee un frame avanzando secuencialmente para evitar búsquedas costosas."""

    if target_index < state["next_index"]:
        capture.set(cv2.CAP_PROP_POS_FRAMES, target_index)
        state["next_index"] = target_index
    while state["next_index"] < target_index:
        success, _ = capture.read()
        if not success:
            return None
        state["next_index"] += 1
    success, frame = capture.read()
    if not success:
        return None
    state["next_index"] += 1
    return frame


def _draw_pose_overlay(
    panel: Any,
    pose_frame: Mapping[str, Any] | None,
    *,
    source_width: int,
    source_height: int,
    landmark_similarities: Mapping[int, float] | None = None,
    base_color: tuple[int, int, int] = (255, 190, 30),
    highlighted_landmarks: set[str] | None = None,
) -> None:
    if not pose_frame or not pose_frame.get("landmarks"):
        return
    points = {
        int(point["landmark_id"]): point
        for point in pose_frame["landmarks"]
    }
    panel_height, panel_width = panel.shape[:2]
    scale = min(panel_width / source_width, panel_height / source_height)
    content_width = max(2, int(round(source_width * scale)))
    content_height = max(2, int(round(source_height * scale)))
    offset_x = (panel_width - content_width) // 2
    offset_y = (panel_height - content_height) // 2
    pixel_points: dict[int, tuple[int, int]] = {}
    for landmark_id, point in points.items():
        x = min(max(int(offset_x + float(point["x"]) * content_width), 0), panel_width - 1)
        y = min(max(int(offset_y + float(point["y"]) * content_height), 0), panel_height - 1)
        pixel_points[landmark_id] = (x, y)

    for start_id, end_id in SKELETON_CONNECTIONS:
        if start_id in pixel_points and end_id in pixel_points:
            cv2.line(panel, pixel_points[start_id], pixel_points[end_id], base_color, 2, cv2.LINE_AA)

    for landmark_id, (x, y) in pixel_points.items():
        similarity = landmark_similarities.get(landmark_id, 1.0) if landmark_similarities else None
        color = _similarity_color(similarity) if similarity is not None else base_color
        cv2.circle(panel, (x, y), 5, color, -1, cv2.LINE_AA)
        cv2.circle(panel, (x, y), 6, (15, 15, 15), 1, cv2.LINE_AA)
        name = str(points[landmark_id].get("landmark_name", ""))
        if highlighted_landmarks and name in highlighted_landmarks:
            cv2.putText(panel, name, (x + 7, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)


def _draw_overlay_label(panel: Any, text: str, *, y: int = 24) -> None:
    cv2.rectangle(panel, (8, 8), (min(panel.shape[1] - 8, 390), y + 8), (12, 12, 12), -1)
    cv2.putText(panel, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (245, 245, 245), 1, cv2.LINE_AA)


def create_aligned_video(
    reference_path: str | Path,
    execution_path: str | Path,
    *,
    reference_frames: Sequence[Mapping[str, Any]],
    execution_frames: Sequence[Mapping[str, Any]],
    alignment: Mapping[str, Any],
    frame_similarity_records: Sequence[Mapping[str, Any]],
    reference_analysis_fps: float,
    execution_analysis_fps: float,
    output_dir: str | Path | None = None,
    output_fps: float = 30.0,
    panel_width: int = 640,
    panel_height: int = 480,
    start_reference_time_sec: float = 0.0,
    end_reference_time_sec: float | None = None,
    highlighted_landmarks: set[str] | None = None,
) -> Path:
    """Genera un MP4 compuesto y sincronizado mediante DTW."""

    if reference_analysis_fps <= 0 or execution_analysis_fps <= 0:
        raise VisualizationError("Los FPS de análisis deben ser positivos")
    reference_source_fps, _, _, reference_source_count = _video_properties(reference_path)
    execution_source_fps, _, _, execution_source_count = _video_properties(execution_path)
    if not reference_frames or not execution_frames:
        raise VisualizationError("No hay frames de pose para construir la visualización")

    execution_by_reference = _dtw_execution_by_reference(alignment)
    records_by_pair = _records_by_pair(frame_similarity_records)
    reference_frame_map = _frame_map(reference_frames)
    execution_frame_map = _frame_map(execution_frames)
    analysis_duration = len(reference_frames) / reference_analysis_fps
    end_time = min(end_reference_time_sec or analysis_duration, analysis_duration)
    start_index = max(0, int(round(start_reference_time_sec * reference_analysis_fps)))
    end_index = min(len(reference_frames), max(start_index + 1, int(round(end_time * reference_analysis_fps))))
    actual_output_fps = min(float(output_fps), float(reference_analysis_fps))
    step = max(1, int(round(reference_analysis_fps / actual_output_fps)))

    target_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="mitotl_visual_"))
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = "full" if start_index == 0 and end_index == len(reference_frames) else f"{start_index}_{end_index}"
    output_path = target_dir / f"mitotl_aligned_{suffix}.mp4"
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        actual_output_fps,
        (panel_width * 2, panel_height),
    )
    if not writer.isOpened():
        raise VisualizationError(f"No fue posible crear: {output_path.name}")

    reference_capture = cv2.VideoCapture(str(reference_path))
    execution_capture = cv2.VideoCapture(str(execution_path))
    reference_state = {"next_index": 0}
    execution_state = {"next_index": 0}
    written = 0
    try:
        for reference_index in range(start_index, end_index, step):
            execution_index = execution_by_reference.get(reference_index)
            if execution_index is None:
                continue
            reference_source_index = min(reference_source_count - 1, int(round(reference_index / reference_analysis_fps * reference_source_fps)))
            execution_source_index = min(execution_source_count - 1, int(round(execution_index / execution_analysis_fps * execution_source_fps)))
            reference_frame = _read_frame_monotonic(reference_capture, reference_source_index, reference_state)
            execution_frame = _read_frame_monotonic(execution_capture, execution_source_index, execution_state)
            if reference_frame is None or execution_frame is None:
                continue

            reference_panel = _fit_frame(reference_frame, panel_width, panel_height)
            execution_panel = _fit_frame(execution_frame, panel_width, panel_height)
            pair_record = records_by_pair.get((reference_index, execution_index), {})
            landmark_similarities = {
                int(landmark_id): _difference_to_similarity(data.get("difference_xy", data.get("difference", 0)))
                for landmark_id, data in pair_record.get("landmarks", {}).items()
            }
            _draw_pose_overlay(
                reference_panel,
                reference_frame_map.get(reference_index),
                source_width=reference_frame.shape[1],
                source_height=reference_frame.shape[0],
                base_color=(255, 190, 30),
                highlighted_landmarks=highlighted_landmarks,
            )
            _draw_pose_overlay(
                execution_panel,
                execution_frame_map.get(execution_index),
                source_width=execution_frame.shape[1],
                source_height=execution_frame.shape[0],
                landmark_similarities=landmark_similarities,
                base_color=(220, 220, 220),
                highlighted_landmarks=highlighted_landmarks,
            )
            reference_time = reference_index / reference_analysis_fps
            execution_time = execution_index / execution_analysis_fps
            _draw_overlay_label(reference_panel, f"Referencia | {reference_time:.2f} s")
            _draw_overlay_label(execution_panel, f"Ejecucion | {execution_time:.2f} s")
            cv2.putText(execution_panel, "Verde: parecido | Rojo: diferencia", (16, panel_height - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (245, 245, 245), 1, cv2.LINE_AA)
            writer.write(cv2.hconcat([reference_panel, execution_panel]))
            written += 1
    finally:
        reference_capture.release()
        execution_capture.release()
        writer.release()

    if written == 0 or not output_path.exists() or output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise VisualizationError("No se pudieron renderizar frames alineados")
    return output_path


def create_aligned_clip(
    reference_path: str | Path,
    execution_path: str | Path,
    *,
    center_reference_time_sec: float,
    clip_duration_sec: float = 2.5,
    **kwargs: Any,
) -> Path:
    """Genera un clip compuesto alrededor de un momento de referencia."""

    half_duration = clip_duration_sec / 2
    return create_aligned_video(
        reference_path,
        execution_path,
        start_reference_time_sec=max(0.0, center_reference_time_sec - half_duration),
        end_reference_time_sec=center_reference_time_sec + half_duration,
        **kwargs,
    )


def create_video_clip(
    video_path: str | Path,
    center_time_sec: float,
    *,
    output_dir: str | Path | None = None,
    clip_duration_sec: float = 2.5,
) -> Path:
    """Extrae una ventana corta alrededor de un momento del video."""

    video_path = Path(video_path)
    fps, width, height, frame_count = _video_properties(video_path)
    start_frame = max(0, int((center_time_sec - clip_duration_sec / 2) * fps))
    end_frame = min(frame_count, int((center_time_sec + clip_duration_sec / 2) * fps))
    target_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="mitotl_clips_"))
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"{video_path.stem}_{center_time_sec:.2f}s_clip.mp4"
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise VisualizationError(f"No fue posible crear el clip: {output_path.name}")
    capture = cv2.VideoCapture(str(video_path))
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        for _ in range(start_frame, end_frame):
            success, frame = capture.read()
            if not success:
                break
            writer.write(frame)
    finally:
        capture.release()
        writer.release()
    if not output_path.exists() or output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise VisualizationError(f"El clip quedó vacío: {output_path.name}")
    return output_path
