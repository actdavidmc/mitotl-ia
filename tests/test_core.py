"""Pruebas unitarias e integración ligera de la lógica productiva."""

from __future__ import annotations

import sys
import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mitotl.alignment import AlignmentError, align_features  # noqa: E402
from mitotl.comparison import build_comparison  # noqa: E402
from mitotl.feedback import build_feedback  # noqa: E402
from mitotl.pipeline import analyze_session  # noqa: E402
from mitotl.schemas import PoseFrame, PoseSequence, VideoMetadata  # noqa: E402
from mitotl.scoring import ScoreConfig, ScoreError, calculate_score  # noqa: E402
from mitotl.video import (  # noqa: E402
    VideoPreparationConfig,
    VideoValidationError,
    inspect_video,
    prepare_video_for_analysis,
    validate_video_file,
)
from mitotl.features import build_features_from_pose  # noqa: E402


def make_landmarks(offset: float = 0.0) -> list[dict[str, float]]:
    landmarks = [
        {
            "landmark_id": landmark_id,
            "x": 0.40 + (landmark_id % 5) * 0.01 + offset,
            "y": 0.20 + (landmark_id % 7) * 0.01,
            "z": (landmark_id % 3) * 0.01,
            "visibility": 0.99,
        }
        for landmark_id in range(33)
    ]
    landmarks[11].update(x=0.45, y=0.30)
    landmarks[12].update(x=0.55, y=0.30)
    landmarks[23].update(x=0.47, y=0.60)
    landmarks[24].update(x=0.53, y=0.60)
    return landmarks


def make_pose(name: str, role: str, offset: float = 0.0, frame_count: int = 4) -> PoseSequence:
    return PoseSequence(
        source_video=name,
        video_role=role,
        model="MediaPipe Pose",
        model_complexity=1,
        landmark_count=33,
        fps=60.0,
        frame_count=frame_count,
        frames=[
            PoseFrame(
                frame_index=index,
                timestamp_sec=index / 60.0,
                detected=True,
                landmarks=make_landmarks(offset + index * 0.001),
            )
            for index in range(frame_count)
        ],
    )


class VideoTests(unittest.TestCase):
    def test_missing_video_is_rejected(self) -> None:
        with self.assertRaises(VideoValidationError):
            validate_video_file("data/raw/reference/does-not-exist.mp4", "reference")

    def test_invalid_extension_is_rejected_before_open(self) -> None:
        with self.assertRaises(VideoValidationError):
            validate_video_file("archivo.txt", "reference")

    def test_preparation_creates_480p_30fps_copy_without_modifying_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.mp4"
            writer = cv2.VideoWriter(
                str(source_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                60.0,
                (320, 240),
            )
            for index in range(60):
                frame = np.full((240, 320, 3), index % 255, dtype=np.uint8)
                writer.write(frame)
            writer.release()
            original_size = source_path.stat().st_size
            source_metadata = inspect_video(source_path, "reference")

            prepared = prepare_video_for_analysis(
                source_path,
                "reference",
                metadata=source_metadata,
                config=VideoPreparationConfig(max_height=120, target_fps=30.0),
            )
            try:
                self.assertEqual(prepared.target_fps, 30.0)
                self.assertTrue(prepared.resized)
                self.assertEqual(prepared.prepared_metadata.height, 120)
                self.assertEqual(prepared.prepared_metadata.width, 160)
                self.assertEqual(prepared.prepared_metadata.frame_count, 30)
                self.assertEqual(source_path.stat().st_size, original_size)
            finally:
                prepared.cleanup()


class FeatureAlignmentComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference = build_features_from_pose(make_pose("reference.mp4", "reference"))
        cls.execution = build_features_from_pose(make_pose("execution.mp4", "execution", offset=0.02))
        cls.alignment = align_features(cls.reference, cls.execution)
        cls.comparison = build_comparison(cls.reference, cls.execution, cls.alignment)

    def test_features_preserve_33_landmarks_and_eight_angles(self) -> None:
        frame = self.reference["frames"][0]
        self.assertEqual(len(frame["landmarks"]), 33)
        self.assertEqual(len(frame["angles"]), 8)

    def test_alignment_has_endpoints_and_segments(self) -> None:
        self.assertEqual(self.alignment["dtw_path"][0], [0, 0])
        self.assertEqual(self.alignment["dtw_path"][-1], [3, 3])
        self.assertGreaterEqual(len(self.alignment["segments"]), 1)

    def test_comparison_uses_all_landmarks_in_each_pair(self) -> None:
        self.assertEqual(len(self.comparison["coordinate_difference_records"]), 4 * 33)
        self.assertEqual(self.comparison["dtw_pair_count"], 4)
        self.assertIn("mean_difference_xy", self.comparison["coordinate_difference_by_body_part"]["right_arm"])


class ScoringFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference = build_features_from_pose(make_pose("reference.mp4", "reference"))
        cls.execution = build_features_from_pose(make_pose("execution.mp4", "execution", offset=0.02))
        cls.alignment = align_features(cls.reference, cls.execution)
        cls.comparison = build_comparison(cls.reference, cls.execution, cls.alignment)
        cls.score = calculate_score(cls.comparison, cls.alignment)
        cls.feedback = build_feedback(cls.score)

    def test_weights_must_sum_one(self) -> None:
        with self.assertRaises(ScoreError):
            calculate_score(self.comparison, self.alignment, config=ScoreConfig(0.7, 0.2))

    def test_score_is_between_zero_and_one_hundred(self) -> None:
        self.assertGreaterEqual(self.score["score_general"], 0)
        self.assertLessEqual(self.score["score_general"], 100)

    def test_feedback_keeps_all_findings_and_summary(self) -> None:
        self.assertEqual(self.feedback["all_findings_count"], 4 * 33)
        self.assertEqual(len(self.feedback["top_findings"]), 20)
        self.assertGreater(self.feedback["recommendations_count"], 0)


class PipelineTests(unittest.TestCase):
    def test_golden_session_contract_is_documented(self) -> None:
        golden_path = PROJECT_ROOT / "tests" / "golden_session.json"
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        self.assertEqual(golden["reference_frames"], 719)
        self.assertEqual(golden["execution_frames"], 947)
        self.assertEqual(golden["dtw_pairs"], 1098)
        self.assertEqual(golden["score_general_percent"], 66.03)
        self.assertEqual(golden["weakest_segment"], 2)

    def test_pipeline_reports_stage_for_invalid_input(self) -> None:
        with self.assertRaisesRegex(Exception, "video_validation"):
            analyze_session("missing.mp4", "missing.mov")

    def test_pipeline_orchestrates_all_stages_with_fixtures(self) -> None:
        reference_pose = make_pose("reference.mp4", "reference")
        execution_pose = make_pose("execution.mp4", "execution", offset=0.02)

        def metadata(name: str, role: str) -> VideoMetadata:
            return VideoMetadata(name, name, role, ".mp4", 4, 60.0, 1920, 1080, 4 / 60)

        with patch("mitotl.pipeline.validate_video_file", side_effect=[metadata("ref.mp4", "reference"), metadata("exec.mp4", "execution")]), \
             patch(
                 "mitotl.pipeline.prepare_video_for_analysis",
                 side_effect=[
                     SimpleNamespace(
                         prepared_path="ref-analysis.mp4",
                         target_fps=30.0,
                         resized=True,
                         original_duration_sec=4 / 60,
                         prepared_metadata=metadata("ref-analysis.mp4", "reference"),
                         warning=None,
                         cleanup=lambda: None,
                     ),
                     SimpleNamespace(
                         prepared_path="exec-analysis.mp4",
                         target_fps=30.0,
                         resized=True,
                         original_duration_sec=4 / 60,
                         prepared_metadata=metadata("exec-analysis.mp4", "execution"),
                         warning=None,
                         cleanup=lambda: None,
                     ),
                 ],
             ), \
             patch("mitotl.pipeline.extract_pose", side_effect=[reference_pose, execution_pose]):
            result = analyze_session("ref.mp4", "exec.mp4")

        self.assertTrue(result["pipeline_completed"])
        self.assertIn("score", result)
        self.assertIn("feedback", result)
        self.assertIn("alignment", result)
        self.assertIn("preparation", result)


if __name__ == "__main__":
    unittest.main()
