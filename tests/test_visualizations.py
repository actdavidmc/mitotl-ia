"""Pruebas de visualizaciones comparativas."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from mitotl.visualizations import create_aligned_video


def _make_pose_frame(frame_index: int, *, offset: float = 0.0) -> dict:
    landmarks = [
        {
            "landmark_id": landmark_id,
            "landmark_name": "nose" if landmark_id == 0 else f"landmark_{landmark_id}",
            "x": 0.5 + offset,
            "y": 0.5,
            "z": 0.0,
            "visibility": 1.0,
        }
        for landmark_id in range(33)
    ]
    return {"frame_index": frame_index, "detected": True, "landmarks": landmarks}


class VisualizationTests(unittest.TestCase):
    def test_aligned_video_has_two_equal_panels_and_landmark_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reference_path = Path(temp_dir) / "reference.mp4"
            execution_path = Path(temp_dir) / "execution.mp4"
            for path, color in ((reference_path, (255, 0, 0)), (execution_path, (0, 0, 255))):
                writer = cv2.VideoWriter(
                    str(path),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    2.0,
                    (64, 64),
                )
                for _ in range(4):
                    writer.write(np.full((64, 64, 3), color, dtype=np.uint8))
                writer.release()

            records = []
            for frame_index in range(4):
                records.append({
                    "reference_frame": frame_index,
                    "execution_frame": frame_index,
                    "landmarks": {
                        str(landmark_id): {"difference_xy": 0.1, "difference": 0.1}
                        for landmark_id in range(33)
                    },
                })
            alignment = {"dtw_path": [[index, index] for index in range(4)]}
            reference_frames = [_make_pose_frame(index) for index in range(4)]
            execution_frames = [_make_pose_frame(index, offset=0.02) for index in range(4)]

            output_path = create_aligned_video(
                reference_path,
                execution_path,
                reference_frames=reference_frames,
                execution_frames=execution_frames,
                alignment=alignment,
                frame_similarity_records=records,
                reference_analysis_fps=2.0,
                execution_analysis_fps=2.0,
                output_dir=temp_dir,
                output_fps=2.0,
                panel_width=64,
                panel_height=64,
            )

            capture = cv2.VideoCapture(str(output_path))
            try:
                self.assertTrue(capture.isOpened())
                self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), 128)
                self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)), 64)
                self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 4)
            finally:
                capture.release()


if __name__ == "__main__":
    unittest.main()
