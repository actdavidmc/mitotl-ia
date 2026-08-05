"""Normalización e ingeniería de variables corporales."""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

from .schemas import PoseFrame, PoseSequence


LANDMARK_IDS = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}

LANDMARK_NAMES = {
    0: "nose", 1: "left_eye_inner", 2: "left_eye", 3: "left_eye_outer",
    4: "right_eye_inner", 5: "right_eye", 6: "right_eye_outer", 7: "left_ear",
    8: "right_ear", 9: "mouth_left", 10: "mouth_right", 11: "left_shoulder",
    12: "right_shoulder", 13: "left_elbow", 14: "right_elbow", 15: "left_wrist",
    16: "right_wrist", 17: "left_pinky", 18: "right_pinky", 19: "left_index",
    20: "right_index", 21: "left_thumb", 22: "right_thumb", 23: "left_hip",
    24: "right_hip", 25: "left_knee", 26: "right_knee", 27: "left_ankle",
    28: "right_ankle", 29: "left_heel", 30: "right_heel", 31: "left_foot_index",
    32: "right_foot_index",
}

BODY_PARTS = {
    "head": set(range(0, 11)),
    "torso": {11, 12, 23, 24},
    "left_arm": {13, 15, 17, 19, 21},
    "right_arm": {14, 16, 18, 20, 22},
    "left_leg": {25, 27, 29, 31},
    "right_leg": {26, 28, 30, 32},
}
LANDMARK_TO_BODY_PART = {
    landmark_id: body_part
    for body_part, landmark_ids in BODY_PARTS.items()
    for landmark_id in landmark_ids
}

ANGLE_DEFINITIONS = {
    "left_elbow": (11, 13, 15),
    "right_elbow": (12, 14, 16),
    "left_shoulder": (13, 11, 23),
    "right_shoulder": (14, 12, 24),
    "left_knee": (23, 25, 27),
    "right_knee": (24, 26, 28),
    "left_hip": (11, 23, 25),
    "right_hip": (12, 24, 26),
}

VELOCITY_LANDMARKS = {
    "left_wrist": LANDMARK_IDS["left_wrist"],
    "right_wrist": LANDMARK_IDS["right_wrist"],
    "left_ankle": LANDMARK_IDS["left_ankle"],
    "right_ankle": LANDMARK_IDS["right_ankle"],
}


def get_landmark(frame: Mapping[str, Any] | PoseFrame, landmark_id: int) -> dict[str, Any] | None:
    """Obtiene un landmark por ID desde un frame detectado."""

    detected = frame.detected if isinstance(frame, PoseFrame) else frame.get("detected", False)
    landmarks = frame.landmarks if isinstance(frame, PoseFrame) else frame.get("landmarks")
    if not detected or landmarks is None:
        return None
    return next((landmark for landmark in landmarks if landmark["landmark_id"] == landmark_id), None)


def _midpoint(point_a: Mapping[str, float], point_b: Mapping[str, float]) -> dict[str, float]:
    return {
        coordinate: (float(point_a[coordinate]) + float(point_b[coordinate])) / 2
        for coordinate in ("x", "y", "z")
    }


def _euclidean_distance_xy(point_a: Mapping[str, float], point_b: Mapping[str, float]) -> float:
    return math.sqrt(
        (float(point_a["x"]) - float(point_b["x"])) ** 2
        + (float(point_a["y"]) - float(point_b["y"])) ** 2
    )


def normalize_frame(frame: PoseFrame | Mapping[str, Any]) -> dict[str, Any]:
    """Normaliza un frame usando caderas como origen y torso como escala."""

    frame_index = frame.frame_index if isinstance(frame, PoseFrame) else frame["frame_index"]
    timestamp_sec = frame.timestamp_sec if isinstance(frame, PoseFrame) else frame["timestamp_sec"]
    landmarks = frame.landmarks if isinstance(frame, PoseFrame) else frame.get("landmarks")
    detected = frame.detected if isinstance(frame, PoseFrame) else frame.get("detected", False)

    result: dict[str, Any] = {
        "frame_index": frame_index,
        "timestamp_sec": timestamp_sec,
        "detected": bool(detected),
        "torso_scale": None,
        "hip_center": None,
        "shoulder_center": None,
        "landmarks": None,
    }
    if not detected or landmarks is None:
        return result

    landmarks_by_id = {landmark["landmark_id"]: landmark for landmark in landmarks}
    required_ids = {
        LANDMARK_IDS["left_shoulder"], LANDMARK_IDS["right_shoulder"],
        LANDMARK_IDS["left_hip"], LANDMARK_IDS["right_hip"],
    }
    if not required_ids.issubset(landmarks_by_id):
        result["detected"] = False
        return result

    shoulder_center = _midpoint(
        landmarks_by_id[LANDMARK_IDS["left_shoulder"]],
        landmarks_by_id[LANDMARK_IDS["right_shoulder"]],
    )
    hip_center = _midpoint(
        landmarks_by_id[LANDMARK_IDS["left_hip"]],
        landmarks_by_id[LANDMARK_IDS["right_hip"]],
    )
    torso_scale = _euclidean_distance_xy(shoulder_center, hip_center)
    if torso_scale == 0:
        result["detected"] = False
        return result

    result.update({"torso_scale": torso_scale, "hip_center": hip_center, "shoulder_center": shoulder_center})
    result["landmarks"] = [
        {
            "landmark_id": landmark["landmark_id"],
            "landmark_name": LANDMARK_NAMES.get(landmark["landmark_id"], "unknown"),
            "x": (float(landmark["x"]) - hip_center["x"]) / torso_scale,
            "y": (float(landmark["y"]) - hip_center["y"]) / torso_scale,
            "z": (float(landmark["z"]) - hip_center["z"]) / torso_scale,
            "visibility": float(landmark.get("visibility", 0.0)),
        }
        for landmark in landmarks
    ]
    return result


def normalize_pose_sequence(sequence: PoseSequence) -> dict[str, Any]:
    """Normaliza todos los frames y conserva la metadata del video."""

    frames = [normalize_frame(frame) for frame in sequence.frames]
    return {
        "source_video": sequence.source_video,
        "video_role": sequence.video_role,
        "fps": sequence.fps,
        "frame_count": sequence.frame_count,
        "landmark_count": sequence.landmark_count,
        "normalization": {
            "origin": "midpoint_of_hips",
            "scale": "shoulder_center_to_hip_center_distance",
            "coordinates": "normalized_relative_coordinates",
        },
        "frames": frames,
    }


def calculate_angle(
    point_a: Mapping[str, float],
    point_b: Mapping[str, float],
    point_c: Mapping[str, float],
) -> float | None:
    """Calcula el ángulo ABC en grados usando x, y y z."""

    vector_ba = [float(point_a[c]) - float(point_b[c]) for c in ("x", "y", "z")]
    vector_bc = [float(point_c[c]) - float(point_b[c]) for c in ("x", "y", "z")]
    magnitude_ba = math.sqrt(sum(value**2 for value in vector_ba))
    magnitude_bc = math.sqrt(sum(value**2 for value in vector_bc))
    if magnitude_ba == 0 or magnitude_bc == 0:
        return None
    cosine = sum(vector_ba[index] * vector_bc[index] for index in range(3)) / (magnitude_ba * magnitude_bc)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def calculate_frame_angles(frame: Mapping[str, Any]) -> dict[str, Any]:
    """Calcula los ocho ángulos articulares definidos en el notebook 03."""

    angles: dict[str, float | None] = {angle_name: None for angle_name in ANGLE_DEFINITIONS}
    if frame.get("detected") and frame.get("landmarks") is not None:
        for angle_name, (point_a_id, point_b_id, point_c_id) in ANGLE_DEFINITIONS.items():
            point_a = get_landmark(frame, point_a_id)
            point_b = get_landmark(frame, point_b_id)
            point_c = get_landmark(frame, point_c_id)
            if point_a and point_b and point_c:
                angles[angle_name] = calculate_angle(point_a, point_b, point_c)
    return {
        "frame_index": frame["frame_index"],
        "timestamp_sec": frame["timestamp_sec"],
        "detected": frame.get("detected", False),
        "angles": angles,
    }


def calculate_angular_velocities(
    angle_frames: Iterable[Mapping[str, Any]],
    angle_names: Iterable[str] = ANGLE_DEFINITIONS.keys(),
) -> list[dict[str, Any]]:
    """Calcula velocidad angular por segundo; el primer valor queda en None."""

    names = list(angle_names)
    velocity_frames: list[dict[str, Any]] = []
    previous_frame: Mapping[str, Any] | None = None
    for current_frame in angle_frames:
        velocities: dict[str, float | None] = {}
        for angle_name in names:
            current_angle = current_frame["angles"].get(angle_name)
            previous_angle = previous_frame["angles"].get(angle_name) if previous_frame else None
            delta_time = (
                current_frame["timestamp_sec"] - previous_frame["timestamp_sec"]
                if previous_frame else 0
            )
            velocities[angle_name] = (
                (current_angle - previous_angle) / delta_time
                if current_angle is not None and previous_angle is not None and delta_time > 0
                else None
            )
        velocity_frames.append({
            "frame_index": current_frame["frame_index"],
            "timestamp_sec": current_frame["timestamp_sec"],
            "detected": current_frame.get("detected", False),
            "angular_velocity_deg_sec": velocities,
        })
        previous_frame = current_frame
    return velocity_frames


def calculate_landmark_velocities(
    frames: Iterable[Mapping[str, Any]],
    landmark_names: Mapping[str, int] = VELOCITY_LANDMARKS,
) -> list[dict[str, Any]]:
    """Calcula velocidad lineal 3D de muñecas y tobillos normalizados."""

    velocity_frames: list[dict[str, Any]] = []
    previous_frame: Mapping[str, Any] | None = None
    for current_frame in frames:
        velocities: dict[str, dict[str, float] | None] = {}
        for landmark_name, landmark_id in landmark_names.items():
            current_landmark = get_landmark(current_frame, landmark_id)
            previous_landmark = get_landmark(previous_frame, landmark_id) if previous_frame else None
            delta_time = (
                current_frame["timestamp_sec"] - previous_frame["timestamp_sec"]
                if previous_frame else 0
            )
            if current_landmark is None or previous_landmark is None or delta_time <= 0:
                velocities[landmark_name] = None
                continue
            deltas = {
                coordinate: current_landmark[coordinate] - previous_landmark[coordinate]
                for coordinate in ("x", "y", "z")
            }
            displacement = math.sqrt(sum(delta**2 for delta in deltas.values()))
            velocities[landmark_name] = {
                "vx": deltas["x"] / delta_time,
                "vy": deltas["y"] / delta_time,
                "vz": deltas["z"] / delta_time,
                "speed": displacement / delta_time,
            }
        velocity_frames.append({
            "frame_index": current_frame["frame_index"],
            "timestamp_sec": current_frame["timestamp_sec"],
            "detected": current_frame.get("detected", False),
            "landmark_velocity": velocities,
        })
        previous_frame = current_frame
    return velocity_frames


def build_features(normalized_data: Mapping[str, Any]) -> dict[str, Any]:
    """Construye el contrato de features a partir de datos normalizados."""

    frames = list(normalized_data["frames"])
    angle_frames = [calculate_frame_angles(frame) for frame in frames]
    angular_velocity_frames = calculate_angular_velocities(angle_frames)
    landmark_velocity_frames = calculate_landmark_velocities(frames)
    feature_frames: list[dict[str, Any]] = []

    for normalized_frame, angle_frame, angular_velocity_frame, linear_velocity_frame in zip(
        frames, angle_frames, angular_velocity_frames, landmark_velocity_frames
    ):
        enriched_landmarks = None
        if normalized_frame["landmarks"] is not None:
            enriched_landmarks = [
                {**landmark, "body_part": LANDMARK_TO_BODY_PART.get(landmark["landmark_id"], "unknown")}
                for landmark in normalized_frame["landmarks"]
            ]
        feature_frames.append({
            "frame_index": normalized_frame["frame_index"],
            "timestamp_sec": normalized_frame["timestamp_sec"],
            "detected": normalized_frame["detected"],
            "torso_scale": normalized_frame["torso_scale"],
            "landmarks": enriched_landmarks,
            "angles": angle_frame["angles"],
            "angular_velocity_deg_sec": angular_velocity_frame["angular_velocity_deg_sec"],
            "landmark_velocity": linear_velocity_frame["landmark_velocity"],
        })

    return {
        "source_video": normalized_data["source_video"],
        "video_role": normalized_data.get("video_role", "unknown"),
        "source_normalized_file": normalized_data.get("source_normalized_file"),
        "fps": normalized_data["fps"],
        "frame_count": normalized_data["frame_count"],
        "landmark_count": normalized_data["landmark_count"],
        "feature_groups": [
            "normalized_landmarks", "body_parts", "angles", "angular_velocity", "landmark_velocity",
        ],
        "frames": feature_frames,
    }


def build_features_from_pose(sequence: PoseSequence) -> dict[str, Any]:
    """Atajo productivo: pose → normalización → variables corporales."""

    normalized_data = normalize_pose_sequence(sequence)
    return build_features(normalized_data)
