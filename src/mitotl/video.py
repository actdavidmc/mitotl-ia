"""Lectura, metadatos y validación de videos para Mitotl IA."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp
from typing import Iterator

import cv2
import numpy as np

from .schemas import VideoMetadata, VideoRole


SUPPORTED_VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".webm"})


@dataclass(frozen=True, slots=True)
class VideoValidationConfig:
    """Umbrales técnicos mínimos para aceptar una entrada del MVP."""

    min_duration_sec: float = 0.5
    min_fps: float = 1.0
    min_width: int = 64
    min_height: int = 64
    allowed_extensions: frozenset[str] = SUPPORTED_VIDEO_EXTENSIONS


@dataclass(frozen=True, slots=True)
class VideoPreparationConfig:
    """Configuración de la copia temporal usada para el análisis."""

    max_height: int = 480
    target_fps: float = 30.0
    long_video_threshold_sec: float = 60.0
    long_video_fps: float = 15.0


@dataclass(frozen=True, slots=True)
class PreparedVideo:
    """Video temporal normalizado y metadatos de su transformación."""

    source_path: str
    prepared_path: str
    source_metadata: VideoMetadata
    prepared_metadata: VideoMetadata
    target_fps: float
    resized: bool
    original_duration_sec: float
    warning: str | None = None

    def cleanup(self) -> None:
        """Elimina la copia temporal de análisis, si todavía existe."""

        prepared_path = Path(self.prepared_path)
        parent = prepared_path.parent
        try:
            prepared_path.unlink(missing_ok=True)
            parent.rmdir()
        except OSError:
            # El directorio puede contener archivos temporales adicionales.
            pass


class VideoValidationError(ValueError):
    """Error con una o más razones legibles para rechazar un video."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class VideoReadError(RuntimeError):
    """Error al abrir o leer frames de un video válido."""


def _scaled_dimensions(width: int, height: int, max_height: int) -> tuple[int, int, bool]:
    if height <= max_height:
        return width - (width % 2), height - (height % 2), False
    scale = max_height / height
    scaled_width = max(2, int(round(width * scale)))
    scaled_height = max(2, int(round(height * scale)))
    return scaled_width - (scaled_width % 2), scaled_height - (scaled_height % 2), True


def prepare_video_for_analysis(
    path: str | Path,
    role: VideoRole,
    *,
    metadata: VideoMetadata | None = None,
    config: VideoPreparationConfig | None = None,
) -> PreparedVideo:
    """Crea una copia temporal a resolución y FPS controlados.

    El original nunca se sobrescribe. El número de frames de salida se calcula
    a partir de la duración original para conservar la línea temporal.
    """

    config = config or VideoPreparationConfig()
    if config.max_height < 2 or config.target_fps <= 0 or config.long_video_fps <= 0:
        raise ValueError("La configuración de preparación de video no es válida")

    source_metadata = metadata or inspect_video(path, role)
    target_fps = (
        config.long_video_fps
        if source_metadata.duration_sec > config.long_video_threshold_sec
        else config.target_fps
    )
    warning = None
    if target_fps < config.target_fps:
        warning = (
            f"Video largo: se utilizó una frecuencia de análisis de {target_fps:.0f} FPS "
            f"en lugar de {config.target_fps:.0f} FPS."
        )

    output_width, output_height, resized = _scaled_dimensions(
        source_metadata.width,
        source_metadata.height,
        config.max_height,
    )
    output_frame_count = max(1, int(round(source_metadata.duration_sec * target_fps)))
    target_dir = Path(mkdtemp(prefix="mitotl_analysis_"))
    output_path = target_dir / f"{Path(path).stem}_analysis.mp4"
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        target_fps,
        (output_width, output_height),
    )
    if not writer.isOpened():
        target_dir.rmdir()
        raise VideoReadError(f"No fue posible crear la copia temporal: {output_path.name}")

    requested_sources: dict[int, list[int]] = {}
    for output_index in range(output_frame_count):
        source_index = min(
            source_metadata.frame_count - 1,
            max(0, int(round(output_index * source_metadata.fps / target_fps))),
        )
        requested_sources.setdefault(source_index, []).append(output_index)

    written = 0
    try:
        with open_video(path) as capture:
            source_index = 0
            while source_index < source_metadata.frame_count:
                success, frame = capture.read()
                if not success:
                    break
                output_indices = requested_sources.get(source_index, [])
                if output_indices:
                    if resized:
                        frame = cv2.resize(frame, (output_width, output_height), interpolation=cv2.INTER_AREA)
                    elif frame.shape[1] != output_width or frame.shape[0] != output_height:
                        frame = cv2.resize(frame, (output_width, output_height), interpolation=cv2.INTER_AREA)
                    for _ in output_indices:
                        writer.write(frame)
                        written += 1
                source_index += 1
    finally:
        writer.release()

    if written != output_frame_count or not output_path.exists() or output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        target_dir.rmdir()
        raise VideoReadError(
            f"La copia temporal quedó incompleta: {written}/{output_frame_count} frames"
        )

    prepared_metadata = inspect_video(output_path, role)
    return PreparedVideo(
        source_path=str(Path(path)),
        prepared_path=str(output_path),
        source_metadata=source_metadata,
        prepared_metadata=prepared_metadata,
        target_fps=target_fps,
        resized=resized,
        original_duration_sec=source_metadata.duration_sec,
        warning=warning,
    )


def _validate_role(role: VideoRole) -> None:
    if role not in {"reference", "execution"}:
        raise ValueError("role debe ser 'reference' o 'execution'")


def inspect_video(path: str | Path, role: VideoRole, *, url: str | None = None) -> VideoMetadata:
    """Lee metadatos técnicos sin cargar el video completo en memoria."""

    _validate_role(role)
    video_path = Path(path)
    if not video_path.exists():
        raise VideoValidationError([f"No existe el archivo de video: {video_path}"])
    if not video_path.is_file():
        raise VideoValidationError([f"La ruta no corresponde a un archivo: {video_path}"])

    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            raise VideoValidationError([f"No fue posible abrir el video: {video_path.name}"])

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = frame_count / fps if fps > 0 else 0.0

        return VideoMetadata(
            file_name=video_path.name,
            path=str(video_path),
            role=role,
            extension=video_path.suffix.lower(),
            frame_count=frame_count,
            fps=fps,
            width=width,
            height=height,
            duration_sec=duration_sec,
            opened=True,
            file_size_bytes=video_path.stat().st_size,
            url=url,
        )
    finally:
        capture.release()


def validate_video_metadata(
    metadata: VideoMetadata,
    config: VideoValidationConfig | None = None,
) -> list[str]:
    """Devuelve todas las advertencias técnicas que impiden usar el video."""

    config = config or VideoValidationConfig()
    errors: list[str] = []
    if not metadata.opened:
        errors.append("El video no pudo abrirse correctamente")
    if metadata.extension.lower() not in config.allowed_extensions:
        allowed = ", ".join(sorted(config.allowed_extensions))
        errors.append(f"Formato no soportado: {metadata.extension}. Permitidos: {allowed}")
    if metadata.frame_count <= 0:
        errors.append("El video no contiene frames")
    if metadata.fps < config.min_fps:
        errors.append(f"FPS insuficiente: {metadata.fps:.3f}; mínimo: {config.min_fps:.3f}")
    if metadata.duration_sec < config.min_duration_sec:
        errors.append(
            f"Duración insuficiente: {metadata.duration_sec:.3f} s; "
            f"mínimo: {config.min_duration_sec:.3f} s"
        )
    if metadata.width < config.min_width or metadata.height < config.min_height:
        errors.append(
            f"Resolución insuficiente: {metadata.width}x{metadata.height}; "
            f"mínimo: {config.min_width}x{config.min_height}"
        )
    return errors


def validate_video_file(
    path: str | Path,
    role: VideoRole,
    *,
    url: str | None = None,
    config: VideoValidationConfig | None = None,
) -> VideoMetadata:
    """Inspecciona y valida un archivo; devuelve metadatos si es aceptable."""

    video_path = Path(path)
    if video_path.suffix.lower() not in (config or VideoValidationConfig()).allowed_extensions:
        allowed = ", ".join(sorted((config or VideoValidationConfig()).allowed_extensions))
        raise VideoValidationError([f"Formato no soportado: {video_path.suffix}. Permitidos: {allowed}"])

    metadata = inspect_video(video_path, role, url=url)
    errors = validate_video_metadata(metadata, config=config)
    if errors:
        raise VideoValidationError(errors)
    return metadata


@contextmanager
def open_video(path: str | Path) -> Iterator[cv2.VideoCapture]:
    """Abre un video y garantiza liberar el recurso al terminar."""

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise VideoReadError(f"No fue posible abrir el video: {Path(path).name}")
    try:
        yield capture
    finally:
        capture.release()


def iter_video_frames(
    path: str | Path,
    *,
    start_frame: int = 0,
    max_frames: int | None = None,
) -> Iterator[tuple[int, float, np.ndarray]]:
    """Itera frames BGR con índice y timestamp, sin retener el video completo."""

    if start_frame < 0:
        raise ValueError("start_frame no puede ser negativo")
    if max_frames is not None and max_frames < 1:
        raise ValueError("max_frames debe ser positivo o None")

    with open_video(path) as capture:
        if start_frame:
            capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frame_index = start_frame
        yielded = 0
        while max_frames is None or yielded < max_frames:
            success, frame = capture.read()
            if not success:
                break
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            timestamp_sec = frame_index / fps if fps > 0 else 0.0
            yield frame_index, timestamp_sec, frame
            frame_index += 1
            yielded += 1
