"""Contexto y cliente del agente de retroalimentación de Mitotl IA."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

from dotenv import load_dotenv
from openai import OpenAI

from .prompts import BODY_PART_LABELS, LANDMARK_LABELS, STRONGER_PROMPT


class AgentConfigurationError(RuntimeError):
    """Error de configuración segura del agente."""


class AgentRequestError(RuntimeError):
    """Error al solicitar una respuesta al proveedor."""


def _localize_finding(finding: Mapping[str, Any]) -> dict[str, Any]:
    localized = dict(finding)
    landmark = localized.get("landmark")
    body_part = localized.get("parte_cuerpo", localized.get("body_part"))
    localized["landmark_es"] = LANDMARK_LABELS.get(landmark, landmark)
    localized["parte_cuerpo_es"] = BODY_PART_LABELS.get(body_part, body_part)
    return localized


def _localize_recommendation(recommendation: Mapping[str, Any]) -> dict[str, Any]:
    localized = dict(recommendation)
    body_part = localized.get("body_part")
    localized["parte_cuerpo_es"] = BODY_PART_LABELS.get(body_part, body_part) if body_part else None
    top_landmarks = []
    for landmark in recommendation.get("top_landmarks", []):
        localized_landmark = dict(landmark)
        name = localized_landmark.get("landmark")
        localized_landmark["landmark_es"] = LANDMARK_LABELS.get(name, name)
        top_landmarks.append(localized_landmark)
    if top_landmarks:
        localized["top_landmarks"] = top_landmarks
    return localized


def build_agent_context(session_result: Mapping[str, Any]) -> dict[str, Any]:
    """Construye un contexto compacto y localizado para el agente."""

    score = session_result.get("score", session_result)
    feedback = session_result.get("feedback", session_result)
    reference = session_result.get("reference", {})
    execution = session_result.get("execution", {})
    context = {
        "video_referencia": reference.get("file_name", score.get("reference_video")),
        "video_ejecucion": execution.get("file_name", score.get("execution_video")),
        "score_general_porcentaje": score.get("score_general"),
        "ponderaciones": score.get("weights", {}),
        "similitud_corporal_en_plano_visible_porcentaje": {
            BODY_PART_LABELS.get(key, key): value
            for key, value in score.get("body_scores_xy", {}).items()
        },
        "similitud_corporal_espacial_diagnostica_porcentaje": {
            BODY_PART_LABELS.get(key, key): value
            for key, value in score.get("body_scores_xyz", {}).items()
        },
        "similitud_temporal": score.get("temporal_similarity"),
        "segmentos_temporales": score.get("segment_scores", []),
        "hallazgos_principales": [
            _localize_finding(finding) for finding in feedback.get("top_findings", score.get("top_findings", []))
        ],
        "recomendaciones": [
            _localize_recommendation(recommendation)
            for recommendation in feedback.get("recommendations", score.get("recommendations", []))
        ],
        "cantidad_hallazgos_completos": feedback.get(
            "all_findings_count", len(score.get("all_findings", []))
        ),
        "estado": score.get("status", session_result.get("status", "preliminary")),
    }
    return context


def build_agent_context_text(session_result: Mapping[str, Any]) -> str:
    """Serializa el contexto localizado sin incluir todos los hallazgos."""

    return json.dumps(build_agent_context(session_result), ensure_ascii=False, indent=2)


def create_agent_client(*, env_path: str | None = None) -> tuple[OpenAI, str]:
    """Carga la configuración local y crea el cliente sin imprimir secretos."""

    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise AgentConfigurationError("No se encontró OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL") or "gpt-5.6-luna"
    return OpenAI(), model


def build_agent_input(question: str, context_text: str) -> str:
    """Construye la entrada del usuario separando pregunta y datos."""

    question = question.strip()
    if not question:
        raise AgentRequestError("La pregunta no puede estar vacía")
    return (
        "CONTEXTO ESTRUCTURADO DE LA SESIÓN:\n"
        f"{context_text}\n\n"
        "PREGUNTA DE LA PERSONA:\n"
        f"{question}"
    )


def ask_agent(
    question: str,
    session_result: Mapping[str, Any],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    instructions: str = STRONGER_PROMPT,
) -> str:
    """Solicita retroalimentación en español mediante Responses API."""

    if client is None:
        client, configured_model = create_agent_client()
        model = model or configured_model
    if not model:
        raise AgentConfigurationError("No se configuró OPENAI_MODEL")
    context_text = build_agent_context_text(session_result)
    try:
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=build_agent_input(question, context_text),
        )
    except Exception as error:
        raise AgentRequestError(f"No fue posible obtener respuesta del agente: {error}") from error
    output_text = getattr(response, "output_text", None)
    if not output_text:
        raise AgentRequestError("La respuesta del agente no contiene texto")
    return output_text.strip()


def stream_agent(
    question: str,
    session_result: Mapping[str, Any],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    instructions: str = STRONGER_PROMPT,
):
    """Genera la respuesta del agente progresivamente para la interfaz de chat."""

    if client is None:
        client, configured_model = create_agent_client()
        model = model or configured_model
    if not model:
        raise AgentConfigurationError("No se configuró OPENAI_MODEL")
    context_text = build_agent_context_text(session_result)
    try:
        stream = client.responses.create(
            model=model,
            instructions=instructions,
            input=build_agent_input(question, context_text),
            stream=True,
        )
        for event in stream:
            if getattr(event, "type", None) == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                if delta:
                    yield delta
    except Exception as error:
        raise AgentRequestError(f"No fue posible obtener respuesta del agente: {error}") from error
