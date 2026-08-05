import unittest

from mitotl.report import build_session_report


class ReportTests(unittest.TestCase):
    def test_build_session_report_returns_pdf(self):
        result = {
            "reference": {"file_name": "reference.mp4", "duration_sec": 12.0, "frame_count": 719},
            "execution": {"file_name": "execution.mov", "duration_sec": 15.8, "frame_count": 947},
            "score": {
                "score_general": 66.03,
                "body_scores_xy": {"arms": 47.49, "legs": 65.13, "torso": 74.21, "head": 78.91},
                "segment_scores": [],
            },
            "feedback": {
                "recommendations": [],
                "top_findings": [],
            },
        }
        pdf = build_session_report(result)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
