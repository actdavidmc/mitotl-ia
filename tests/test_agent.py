"""Pruebas locales del contexto y contrato del agente, sin llamadas de red."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mitotl.agent import (  # noqa: E402
    AgentRequestError,
    ask_agent,
    build_agent_context,
    build_agent_input,
)
from mitotl.prompts import STRONGER_PROMPT  # noqa: E402


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_text="Respuesta de prueba en español.")


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


class AgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = {
            "status": "preliminary",
            "reference": {"file_name": "ref.mp4"},
            "execution": {"file_name": "exec.mov"},
            "score": {
                "score_general": 66.03,
                "weights": {"body": 0.8, "temporal": 0.2},
                "body_scores_xy": {"arms": 47.49},
                "body_scores_xyz": {"arms": 39.45},
                "temporal_similarity": 0.6439,
                "segment_scores": [],
                "status": "preliminary",
            },
            "feedback": {
                "all_findings_count": 36234,
                "top_findings": [{
                    "landmark": "right_pinky",
                    "parte_cuerpo": "right_arm",
                    "diferencia_xy": 3.5,
                    "diferencia_xyz": 3.9,
                    "severidad": "Alta",
                }],
                "recommendations": [{
                    "type": "body_part",
                    "body_part": "right_arm",
                    "recommendation": "Revisar la trayectoria del brazo derecho.",
                }],
            },
        }

    def test_context_localizes_labels_and_omits_full_findings(self) -> None:
        context = build_agent_context(self.session)
        self.assertEqual(context["video_referencia"], "ref.mp4")
        self.assertEqual(context["similitud_corporal_en_plano_visible_porcentaje"]["Brazos"], 47.49)
        self.assertEqual(context["hallazgos_principales"][0]["landmark_es"], "Meñique derecho")
        self.assertEqual(context["recomendaciones"][0]["parte_cuerpo_es"], "Brazo derecho")
        self.assertEqual(context["cantidad_hallazgos_completos"], 36234)
        self.assertNotIn("all_findings", context)

    def test_empty_question_is_rejected(self) -> None:
        with self.assertRaises(AgentRequestError):
            build_agent_input("  ", "{}")

    def test_responses_api_contract_is_used_without_network(self) -> None:
        client = FakeClient()
        response = ask_agent("¿Qué practico primero?", self.session, client=client, model="test-model")
        self.assertEqual(response, "Respuesta de prueba en español.")
        call = client.responses.calls[0]
        self.assertEqual(call["model"], "test-model")
        self.assertEqual(call["instructions"], STRONGER_PROMPT)
        self.assertIn("¿Qué practico primero?", str(call["input"]))

    def test_prompt_contains_scope_and_metrics_rules(self) -> None:
        self.assertIn("similitud corporal en el plano visible (XY)", STRONGER_PROMPT)
        self.assertIn("similitud corporal espacial diagnóstica (XYZ)", STRONGER_PROMPT)
        self.assertIn("Esa solicitud está fuera de mi alcance", STRONGER_PROMPT)
        self.assertIn("exclusivamente en español", STRONGER_PROMPT)


if __name__ == "__main__":
    unittest.main()
