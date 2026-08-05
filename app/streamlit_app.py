"""Interfaz Streamlit inicial de Mitotl IA para videos cargados."""

from __future__ import annotations

import base64
import html
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mitotl.agent import AgentConfigurationError, AgentRequestError, stream_agent  # noqa: E402
from mitotl.pipeline import PipelineError, analyze_session  # noqa: E402
from mitotl.prompts import BODY_PART_LABELS, LANDMARK_LABELS  # noqa: E402
from mitotl.report import build_session_report  # noqa: E402
from mitotl.visualizations import (  # noqa: E402
    VisualizationError,
    create_aligned_clip,
    create_aligned_video,
    select_high_severity_moments,
)


FULL_COMPOSITE_LIMIT_SEC = 5 * 60


def _traffic_signal(value: float, *, percent: bool = True) -> tuple[str, str]:
    ratio = float(value) / 100 if percent else float(value)
    if ratio <= 0.30:
        return "#FF0F00", "Necesita atención"
    if ratio <= 0.60:
        return "#FFD166", "En proceso"
    return "#39FF88", "Buen parecido"


st.set_page_config(page_title="Mitotl IA", page_icon="🎭", layout="wide")


def _inventory_path() -> Path:
    return PROJECT_ROOT / "data" / "metadata" / "reference_video_inventory.csv"


def _reference_dir() -> Path:
    return PROJECT_ROOT / "data" / "raw" / "reference"


def _brand_asset(name: str) -> Path:
    return PROJECT_ROOT / "assets" / "brand" / "export" / name


def _save_uploaded_file(uploaded_file: Any, prefix: str) -> Path:
    suffix = Path(uploaded_file.name).suffix.lower() or ".mp4"
    temporary_file = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False)
    temporary_file.write(uploaded_file.getbuffer())
    temporary_file.flush()
    temporary_file.close()
    return Path(temporary_file.name)


@st.cache_data(ttl=3600, show_spinner=False)
def _download_aist_video(url: str) -> bytes:
    """Descarga una referencia AIST y conserva sus bytes en la caché de Streamlit."""

    request = Request(url, headers={"User-Agent": "Mitotl-IA/0.1"})
    with urlopen(request, timeout=90) as response:
        return response.read()


def _materialize_aist_reference(selected_row: pd.Series) -> Path | None:
    """Convierte la URL del inventario en un archivo temporal para OpenCV."""

    file_name = str(selected_row.get("file_name", "reference.mp4"))
    cached_paths = st.session_state.setdefault("aist_reference_paths", {})
    cached_path = cached_paths.get(file_name)
    if cached_path and Path(cached_path).exists():
        return Path(cached_path)

    url = str(selected_row.get("url", "")).strip()
    if not url or url.lower() == "nan":
        st.error("La referencia no tiene una URL de descarga disponible.")
        return None

    try:
        with st.spinner(f"Descargando referencia {file_name}..."):
            video_bytes = _download_aist_video(url)
        suffix = Path(file_name).suffix.lower() or ".mp4"
        temporary_file = tempfile.NamedTemporaryFile(
            prefix="mitotl_aist_reference_",
            suffix=suffix,
            delete=False,
        )
        temporary_file.write(video_bytes)
        temporary_file.flush()
        temporary_file.close()
        path = Path(temporary_file.name)
        cached_paths[file_name] = str(path)
        return path
    except Exception as error:
        st.error(f"No se pudo descargar la referencia desde AIST: {error}")
        return None


def _render_video_box(video_path: Path, *, height: int = 420) -> None:
    """Muestra cualquier orientación de video dentro de una caja uniforme."""

    mime_by_suffix = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
    }
    mime_type = mime_by_suffix.get(video_path.suffix.lower(), "video/mp4")
    encoded_video = base64.b64encode(video_path.read_bytes()).decode("ascii")
    components.html(
        f"""
        <div style="width:100%; height:{height}px; background:#11131a; border-radius:0.5rem; overflow:hidden; display:flex; align-items:center; justify-content:center;">
            <video controls style="width:100%; height:100%; object-fit:contain; background:#11131a;">
                <source src="data:{mime_type};base64,{encoded_video}" type="{mime_type}">
                Tu navegador no puede reproducir este video.
            </video>
        </div>
        """,
        height=height,
        scrolling=False,
    )


def _render_table_box(
    dataframe: pd.DataFrame,
    *,
    header_color: str,
    box_color: str = "rgba(6,70,83,0.18)",
) -> None:
    """Renderiza una tabla dentro de un contenedor nativo de Streamlit."""

    styled_dataframe = dataframe.style.set_table_styles(
        [{
            "selector": "th",
            "props": [
                ("background-color", header_color),
                ("color", "white"),
                ("font-weight", "bold"),
            ],
        }]
    )
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 0.75rem;
            border: 1px solid rgba(255,255,255,0.14);
            background: linear-gradient(145deg, rgba(6,70,83,0.78), rgba(8,122,90,0.20));
            box-shadow: 0 8px 20px rgba(0,0,0,0.14);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(
            f"<div style='height:4px; background:{box_color}; border-radius:4px; margin-bottom:0.5rem;'></div>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            styled_dataframe,
            use_container_width=True,
            hide_index=True,
        )


def _load_inventory() -> pd.DataFrame:
    path = _inventory_path()
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _saved_session_path() -> Path:
    return PROJECT_ROOT / "data" / "derived" / "scores" / "session_score_summary.json"


def _load_saved_session() -> dict[str, Any] | None:
    """Carga una sesión existente únicamente para revisar visualmente la interfaz."""

    path = _saved_session_path()
    if not path.exists():
        return None
    summary = json.loads(path.read_text(encoding="utf-8"))

    reference_name = summary.get("reference_video")
    execution_name = summary.get("execution_video")

    def load_derived(directory: str, file_name: str | None) -> dict[str, Any]:
        if not file_name:
            return {}
        derived_path = PROJECT_ROOT / "data" / "derived" / directory / file_name
        if not derived_path.exists():
            return {}
        return json.loads(derived_path.read_text(encoding="utf-8"))

    reference_stem = Path(reference_name).stem if reference_name else ""
    execution_stem = Path(execution_name).stem if execution_name else ""
    reference_pose = load_derived("pose", f"{reference_stem}_pose.json")
    execution_pose = load_derived("pose", f"{execution_stem}_pose.json")
    reference_features = load_derived("features", f"{reference_stem}_features.json")
    execution_features = load_derived("features", f"{execution_stem}_features.json")
    alignment_path = PROJECT_ROOT / "data" / "derived" / "comparison" / "dtw_alignment_summary.json"
    alignment = json.loads(alignment_path.read_text(encoding="utf-8")) if alignment_path.exists() else {}
    return {
        "status": summary.get("status", "preliminary"),
        "pipeline_completed": True,
        "reference": {"file_name": reference_name},
        "execution": {"file_name": execution_name},
        "pose": {"reference": reference_pose, "execution": execution_pose},
        "features": {"reference": reference_features, "execution": execution_features},
        "alignment": alignment,
        "score": {
            "score_general": summary.get("score_general", 0),
            "body_scores_xy": summary.get("body_scores_xy", {}),
            "body_scores_xyz": summary.get("body_scores_xyz", {}),
            "segment_scores": summary.get("segment_scores", []),
            "frame_similarity_records": summary.get("frame_similarity_records", []),
        },
        "feedback": {
            "recommendations": summary.get("recommendations", []),
            "top_findings": summary.get("top_findings", []),
            "all_findings": summary.get("all_findings", []),
            "all_findings_count": len(summary.get("all_findings", [])),
        },
    }


def _reference_selector(inventory: pd.DataFrame) -> Path | None:
    st.markdown("### Video de referencia")
    reference_mode = st.radio(
        "Origen de la referencia",
        ["Catálogo AIST", "Cargar referencia propia"],
        horizontal=True,
    )
    if reference_mode == "Cargar referencia propia":
        uploaded_reference = st.file_uploader(
            "Selecciona un video de referencia",
            type=["mp4", "mov", "webm"],
            key="reference_upload",
        )
        if uploaded_reference is None:
            return None
        if st.session_state.get("reference_upload_name") != uploaded_reference.name:
            st.session_state["reference_upload_path"] = _save_uploaded_file(uploaded_reference, "mitotl_reference_")
            st.session_state["reference_upload_name"] = uploaded_reference.name
        return Path(st.session_state["reference_upload_path"])

    if inventory.empty:
        st.error("No se encontró el inventario de referencias.")
        return None
    selected_name = st.selectbox("Referencia del catálogo", inventory["file_name"].tolist())
    selected_path = _reference_dir() / selected_name
    selected_row = inventory[inventory["file_name"] == selected_name].iloc[0]
    if not selected_path.exists():
        selected_path = _materialize_aist_reference(selected_row)
        if selected_path is None:
            return None
    st.caption(
        f"Género: {selected_row.get('genre', '—')} · "
        f"Duración: {float(selected_row.get('duration_sec', 0)):.2f} s · "
        f"Cámara: {selected_row.get('camera', '—')}"
    )
    return selected_path


def _render_kpis(result: dict[str, Any]) -> None:
    score = result["score"]
    st.subheader("Resultado de la sesión")
    body_scores = score["body_scores_xy"]
    general_color, general_status = _traffic_signal(score["score_general"])
    ordered_body_scores = sorted(body_scores.items(), key=lambda item: item[1])
    body_labels = {"arms": "💪 Brazos", "legs": "🦵 Piernas", "torso": "🧍 Torso", "head": "🧠 Cabeza"}
    kpis = [
        ("Score general", score["score_general"], general_color, general_status),
    ]
    kpis.extend(
        (body_labels[part], value, *_traffic_signal(value))
        for part, value in ordered_body_scores
    )
    st.markdown(
        f"""
        <style>
        .mitotl-kpi-layout {{
            display: grid;
            grid-template-columns: minmax(210px, 0.9fr) minmax(0, 1.8fr);
            gap: 0.75rem;
            margin: 0.75rem 0 1.25rem 0;
        }}
        .mitotl-kpi-secondary-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
        }}
        .mitotl-kpi-card {{
            min-height: 112px;
            padding: 1rem;
            border: 1px solid rgba(255,255,255,0.12);
            border-top: 4px solid var(--kpi-color);
            border-radius: 0.75rem;
            background: linear-gradient(145deg, rgba(6,70,83,0.78), rgba(8,122,90,0.20));
            box-shadow: 0 8px 20px rgba(0,0,0,0.14);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }}
        .mitotl-kpi-featured {{ min-height: 320px !important; }}
        .mitotl-kpi-featured .mitotl-kpi-label {{ font-size: 2.04rem; }}
        .mitotl-kpi-featured .mitotl-kpi-value {{ font-size: 4.1rem; }}
        .mitotl-kpi-featured .mitotl-kpi-caption {{ font-size: 1.68rem; }}
        .mitotl-kpi-label {{
            color: rgba(255,255,255,0.75);
            font-size: 1.02rem;
            font-weight: 600;
        }}
        .mitotl-kpi-value {{
            color: #ffffff;
            font-size: 2.05rem;
            font-weight: 800;
            line-height: 1.2;
            margin-top: 0.45rem;
        }}
        .mitotl-kpi-caption {{
            color: rgba(255,255,255,0.52);
            font-size: 0.84rem;
            margin-top: 0.25rem;
        }}
        .mitotl-kpi-status {{
            font-size: 0.9rem;
            font-weight: 700;
            margin-top: 0.2rem;
        }}
        @media (max-width: 900px) {{
            .mitotl-kpi-layout {{ grid-template-columns: 1fr; }}
            .mitotl-kpi-secondary-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}
        @media (max-width: 560px) {{
            .mitotl-kpi-secondary-grid {{ grid-template-columns: 1fr; }}
        }}
        </style>
        <div class="mitotl-kpi-layout">
            <div class="mitotl-kpi-card mitotl-kpi-featured" style="--kpi-color:{general_color};">
                <div class="mitotl-kpi-label">Score general</div>
                <div class="mitotl-kpi-value">{score['score_general']:.2f}%</div>
                <div class="mitotl-kpi-status" style="color:{general_color};">{general_status}</div>
                <div class="mitotl-kpi-caption">Parecido general en pantalla</div>
            </div>
            <div class="mitotl-kpi-secondary-grid">
                {''.join(
                    f'''<div class="mitotl-kpi-card" style="--kpi-color:{color};">
                        <div class="mitotl-kpi-label">{label}</div>
                        <div class="mitotl-kpi-value">{value:.2f}%</div>
                        <div class="mitotl-kpi-status" style="color:{status};">{status}</div>
                        <div class="mitotl-kpi-caption">Parecido en pantalla</div>
                    </div>'''
                    for label, value, color, status in kpis[1:]
                )}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="mitotl-reading-box">
            <div class="mitotl-reading-title">Cómo leer estos números</div>
            <div>
                <strong>Parecido en pantalla</strong><br>
                Mira si cada parte del cuerpo aparece en un lugar parecido dentro de la pantalla:
                a la izquierda o derecha, y arriba o abajo.
            </div>
        </div>
        <style>
        .mitotl-reading-box {
            margin: 0.25rem 0 1.25rem 0;
            padding: 0.8rem 1rem;
            border: 1px solid rgba(255,255,255,0.12);
            border-left: 4px solid #00F0FF;
            border-radius: 0.75rem;
            background: rgba(6,70,83,0.30);
            color: rgba(255,255,255,0.75);
            font-size: 0.86rem;
            line-height: 1.45;
        }
        .mitotl-reading-title {
            color: #00F0FF;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }
        .mitotl-reading-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1rem;
        }
        .mitotl-reading-grid strong { color: #ffffff; }
        @media (max-width: 900px) {
            .mitotl-reading-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_temporal_sync(result: dict[str, Any]) -> None:
    score = result["score"]
    st.subheader("Sincronización temporal")
    segments = pd.DataFrame(score["segment_scores"])
    if not segments.empty:
        segments_display = segments[
            [
                "segment",
                "temporal_similarity",
                "reference_start_time_sec",
                "reference_end_time_sec",
                "execution_start_time_sec",
                "execution_end_time_sec",
            ]
        ].rename(
            columns={
                "segment": "Segmento",
                "temporal_similarity": "Similitud temporal",
                "reference_start_time_sec": "Inicio referencia (s)",
                "reference_end_time_sec": "Fin referencia (s)",
                "execution_start_time_sec": "Inicio ejecución (s)",
                "execution_end_time_sec": "Fin ejecución (s)",
            }
        )
        segments_display["Similitud temporal"] = segments_display["Similitud temporal"].map(lambda value: f"{value:.3f}")
        for column in [
            "Inicio referencia (s)",
            "Fin referencia (s)",
            "Inicio ejecución (s)",
            "Fin ejecución (s)",
        ]:
            segments_display[column] = segments_display[column].map(lambda value: f"{value:.2f}")
        _render_table_box(
            segments_display,
            header_color="#064653",
            box_color="#FF39B0",
        )


def _render_recommendations(result: dict[str, Any]) -> None:
    feedback = result["feedback"]
    st.subheader("Recomendaciones")
    recommendations = feedback["recommendations"]
    body_recommendations = sorted(
        (item for item in recommendations if item["type"] == "body_part"),
        key=lambda item: item.get("similarity_xy_percent", 100),
    )
    temporal_recommendations = sorted(
        (item for item in recommendations if item["type"] != "body_part"),
        key=lambda item: item.get("temporal_similarity", 1),
    )

    st.markdown(
        """
        <style>
        .mitotl-recommendation-card {
            min-height: 9rem;
            margin-bottom: 0.8rem;
            padding: 1rem 1.1rem;
            border: 1px solid rgba(255,255,255,0.14);
            border-left: 4px solid var(--recommendation-color);
            border-radius: 0.75rem;
            background: linear-gradient(135deg, rgba(6,70,83,0.45), rgba(9,25,31,0.72));
        }
        .mitotl-recommendation-title { color: #ffffff; font-size: 1.05rem; font-weight: 700; }
        .mitotl-recommendation-score { color: var(--recommendation-color); font-weight: 700; margin: 0.35rem 0; }
        .mitotl-recommendation-text { color: rgba(255,255,255,0.78); line-height: 1.45; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if body_recommendations:
        st.markdown("#### Qué practicar del cuerpo")
        body_columns = st.columns(2)
        for index, recommendation in enumerate(body_recommendations):
            body_part = recommendation.get("body_part", recommendation.get("parte_cuerpo", "—"))
            body_part_label = recommendation.get("parte_cuerpo_es") or BODY_PART_LABELS.get(body_part, body_part)
            color, status = _traffic_signal(recommendation.get("similarity_xy_percent", 0))
            with body_columns[index % 2]:
                st.markdown(
                    f"""
                    <div class="mitotl-recommendation-card" style="--recommendation-color:{color};">
                        <div class="mitotl-recommendation-title">{html.escape(body_part_label)}</div>
                        <div class="mitotl-recommendation-score">Parecido en pantalla: {recommendation.get('similarity_xy_percent', 0):.2f}% · {status}</div>
                        <div class="mitotl-recommendation-text">{html.escape(recommendation.get('recommendation', 'Sin recomendación disponible.'))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    if temporal_recommendations:
        st.markdown("#### Ritmo y sincronización")
        temporal_columns = st.columns(2)
        for index, recommendation in enumerate(temporal_recommendations):
            segment = recommendation.get("segment", "—")
            color, status = _traffic_signal(recommendation.get("temporal_similarity", 0), percent=False)
            with temporal_columns[index % 2]:
                st.markdown(
                    f"""
                    <div class="mitotl-recommendation-card" style="--recommendation-color:{color};">
                        <div class="mitotl-recommendation-title">Segmento temporal {html.escape(str(segment))}</div>
                        <div class="mitotl-recommendation-score">Parecido en el tiempo: {recommendation.get('temporal_similarity', 0):.3f} · {status}</div>
                        <div class="mitotl-recommendation-text">{html.escape(recommendation.get('recommendation', 'Sin recomendación disponible.'))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_findings(result: dict[str, Any]) -> None:
    feedback = result["feedback"]
    st.subheader("Hallazgos principales")
    findings = pd.DataFrame(feedback["top_findings"])
    if not findings.empty:
        findings_display = findings[
            [
                "reference_frame",
                "execution_frame",
                "reference_time_sec",
                "execution_time_sec",
                "landmark",
                "parte_cuerpo",
                "diferencia_xy",
                "severidad",
            ]
        ].rename(
            columns={
                "reference_frame": "Frame referencia",
                "execution_frame": "Frame ejecución",
                "reference_time_sec": "Tiempo referencia (s)",
                "execution_time_sec": "Tiempo ejecución (s)",
                "landmark": "Punto corporal",
                "parte_cuerpo": "Parte del cuerpo",
                "diferencia_xy": "Diferencia de posición",
                "severidad": "Severidad",
            }
        )
        findings_display["Punto corporal"] = findings_display["Punto corporal"].map(
            lambda value: LANDMARK_LABELS.get(value, value)
        )
        findings_display["Parte del cuerpo"] = findings_display["Parte del cuerpo"].map(
            lambda value: BODY_PART_LABELS.get(value, value)
        )
        findings_display["Tiempo referencia (s)"] = findings_display["Tiempo referencia (s)"].map(lambda value: f"{value:.2f}")
        findings_display["Tiempo ejecución (s)"] = findings_display["Tiempo ejecución (s)"].map(lambda value: f"{value:.2f}")
        findings_display["Diferencia de posición"] = findings_display["Diferencia de posición"].map(lambda value: f"{value:.4f}")
        _render_table_box(findings_display, header_color="#FF0F00")


def _render_pdf_download(result: dict[str, Any]) -> None:
    """Muestra la descarga del reporte resumido de la sesión."""

    if "session_report_pdf" not in st.session_state:
        try:
            st.session_state["session_report_pdf"] = build_session_report(result)
        except Exception as error:
            st.error(f"No fue posible preparar el reporte PDF: {error}")
            return
    st.markdown("### Reporte de la sesión")
    st.caption("Descarga un resumen con los scores, la sincronización, los hallazgos y las recomendaciones.")
    st.download_button(
        "Descargar resultados en PDF",
        data=st.session_state["session_report_pdf"],
        file_name="mitotl_reporte_sesion.pdf",
        mime="application/pdf",
        key="download_session_report_pdf",
        type="primary",
    )


def _render_agent(result: dict[str, Any] | None) -> None:
    """Renderiza el asistente con el patrón conversacional de Streamlit."""

    st.title("💬 Asistente Mitotl IA")
    st.caption("🎭 Una guía educativa para comprender tus resultados y practicar mejor.")

    messages = st.session_state.setdefault("agent_messages", [])
    if not messages:
        messages.append(
            {
                "role": "assistant",
                "content": (
                    "¡Hola! Soy el asistente de Mitotl IA. Puedo ayudarte a entender "
                    "tus resultados, identificar qué practicar primero y explicar por qué. "
                    "La retroalimentación es educativa y no sustituye una evaluación profesional."
                ),
            }
        )
        if result is None:
            messages.append(
                {
                    "role": "assistant",
                    "content": "Primero carga tus videos y ejecuta el análisis para que pueda ayudarte con una sesión concreta.",
                }
            )

    # El historial tiene su propio scroll para que la entrada permanezca debajo.
    chat_container = st.container(height=620, border=False)
    with chat_container:
        for message in messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    if result is None:
        return

    # El campo se declara después del historial para que visualmente quede al final.
    question = st.chat_input(
        "Escribe tu pregunta sobre esta sesión...",
        key="agent_chat_input",
    )
    if question and question.strip():
        question_text = question.strip()
        messages.append({"role": "user", "content": question_text})
        try:
            with chat_container:
                with st.chat_message("user"):
                    st.write(question_text)
                with st.chat_message("assistant"):
                    response = st.write_stream(stream_agent(question_text, result))
        except (AgentConfigurationError, AgentRequestError) as error:
            response = f"No pude generar la respuesta: {error}"
            with chat_container:
                st.error(response)
        messages.append({"role": "assistant", "content": response})
        # En la siguiente ejecución el historial completo se dibuja antes del input.
        st.rerun()


def _render_instructions() -> bool:
    stacked_logo_path = _brand_asset("stacked-logo-color.png")
    if stacked_logo_path.exists():
        logo_columns = st.sidebar.columns([1, 2, 1])
        with logo_columns[1]:
            st.image(str(stacked_logo_path), width=140)
    st.sidebar.caption("Análisis educativo de movimiento corporal")
    st.sidebar.markdown("### Cómo comenzar")
    st.sidebar.markdown(
        "1. Abre la pestaña **Videos**.\n"
        "2. Selecciona o carga un video de referencia.\n"
        "3. Carga tu video de ejecución.\n"
        "4. Ejecuta el análisis.\n"
        "5. Consulta tus resultados y pregunta al agente."
    )
    st.sidebar.info(
        "El análisis compara pose, trayectoria y sincronización. "
        "El score orienta la práctica; no representa calidad artística profesional."
    )
    return st.sidebar.checkbox(
        "Revisar interfaz con sesión guardada",
        value=False,
        help="Usa el JSON existente solo para probar el diseño sin volver a procesar los videos.",
    )


def _resolve_session_video_paths(result: dict[str, Any]) -> tuple[Path | None, Path | None]:
    """Resuelve los videos de la sesión actual o de la sesión guardada."""

    stored_paths = st.session_state.get("analysis_video_paths", {})
    reference_path = Path(stored_paths["reference"]) if stored_paths.get("reference") else None
    execution_path = Path(stored_paths["execution"]) if stored_paths.get("execution") else None

    if reference_path is None or not reference_path.exists():
        reference_name = result.get("reference", {}).get("file_name")
        candidate = _reference_dir() / reference_name if reference_name else None
        reference_path = candidate if candidate and candidate.exists() else None
    if execution_path is None or not execution_path.exists():
        execution_name = result.get("execution", {}).get("file_name")
        candidate = PROJECT_ROOT / "data" / "raw" / "execution" / execution_name if execution_name else None
        execution_path = candidate if candidate and candidate.exists() else None
    return reference_path, execution_path


def _render_visualizations(result: dict[str, Any] | None) -> None:
    st.subheader("Visualizaciones")
    if result is None:
        st.info("Las visualizaciones estarán disponibles después de ejecutar el análisis.")
        return

    for warning in result.get("warnings", []):
        st.warning(warning)

    reference_path, execution_path = _resolve_session_video_paths(result)
    if reference_path is None or execution_path is None:
        st.warning("No se encontraron los videos de esta sesión para preparar la comparación visual.")
        return

    st.markdown("### Video comparativo sincronizado")
    st.caption(
        "La referencia y tu ejecución aparecen en un solo video, lado a lado y sincronizadas "
        "con la alineación temporal del análisis."
    )

    pose_data = result.get("pose", {})
    reference_pose = pose_data.get("reference", {})
    execution_pose = pose_data.get("execution", {})
    alignment = result.get("alignment", {})
    score = result.get("score", {})
    reference_frames = reference_pose.get("frames", [])
    execution_frames = execution_pose.get("frames", [])
    records = score.get("frame_similarity_records", [])
    reference_fps = result.get("preparation", {}).get("reference", {}).get("target_fps")
    execution_fps = result.get("preparation", {}).get("execution", {}).get("target_fps")
    reference_fps = float(reference_fps or result.get("features", {}).get("reference", {}).get("fps", reference_pose.get("fps", 30.0)))
    execution_fps = float(execution_fps or result.get("features", {}).get("execution", {}).get("fps", execution_pose.get("fps", 30.0)))
    feedback = result.get("feedback", {})
    findings = feedback.get("all_findings") or feedback.get("top_findings", [])
    moments = select_high_severity_moments(findings, max_moments=3)
    highlighted_landmarks = {
        str(moment["landmark"])
        for moment in moments
        if moment.get("landmark") not in {None, "—"}
    }

    if not reference_frames or not execution_frames or not alignment or not records:
        st.warning("La sesión no contiene los datos necesarios para dibujar landmarks sincronizados.")
        return

    previous_clips = st.session_state.get("critical_clips", [])
    if previous_clips and any("video" not in clip for clip in previous_clips):
        st.session_state.pop("critical_clips", None)

    reference_duration = float(result.get("reference", {}).get("duration_sec", 0.0) or 0.0)
    execution_duration = float(result.get("execution", {}).get("duration_sec", 0.0) or 0.0)
    longest_duration = max(reference_duration, execution_duration)
    if longest_duration > FULL_COMPOSITE_LIMIT_SEC:
        st.warning(
            "La sesión supera 5 minutos. Se mostrarán clips críticos para evitar un "
            "renderizado completo demasiado pesado."
        )
    elif not st.session_state.get("aligned_video"):
        with st.spinner("Generando comparación sincronizada con landmarks..."):
            try:
                st.session_state["aligned_video"] = create_aligned_video(
                    reference_path,
                    execution_path,
                    reference_frames=reference_frames,
                    execution_frames=execution_frames,
                    alignment=alignment,
                    frame_similarity_records=records,
                    reference_analysis_fps=reference_fps,
                    execution_analysis_fps=execution_fps,
                    highlighted_landmarks=highlighted_landmarks,
                )
            except VisualizationError as error:
                st.error(str(error))

    aligned_video = st.session_state.get("aligned_video")
    if aligned_video:
        st.video(str(aligned_video))
        st.download_button(
            "Descargar video comparativo",
            data=Path(aligned_video).read_bytes(),
            file_name="mitotl_video_comparativo.mp4",
            mime="video/mp4",
            key="download_aligned_video",
        )

    st.markdown(
        """
        <div class="mitotl-reading-box">
            <div class="mitotl-reading-title">Cómo leer la comparación</div>
            <div class="mitotl-reading-grid">
                <div>
                    <strong>Verde: más parecido</strong><br>
                    La ejecución aparece más cerca de la referencia en la posición
                    visible del cuerpo.
                </div>
                <div>
                    <strong>Rojo: más diferente</strong><br>
                    La ejecución se separa más de la referencia en la posición visible.
                    La pista de profundidad ayuda a comparar qué tan cerca o lejos
                    parece estar una parte, pero no crea una imagen 3D real.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Momentos con mayor diferencia")
    if not moments:
        st.info("No hay hallazgos suficientes para preparar clips críticos.")
        return

    moments_display = pd.DataFrame(moments).rename(
        columns={
            "reference_time_sec": "Tiempo referencia (s)",
            "execution_time_sec": "Tiempo ejecución (s)",
            "landmark": "Punto corporal",
            "body_part": "Parte del cuerpo",
            "difference": "Diferencia de posición",
            "severity": "Severidad",
        }
    )
    moments_display["Punto corporal"] = moments_display["Punto corporal"].map(
        lambda value: LANDMARK_LABELS.get(value, value)
    )
    moments_display["Parte del cuerpo"] = moments_display["Parte del cuerpo"].map(
        lambda value: BODY_PART_LABELS.get(value, value)
    )
    for column in ["Tiempo referencia (s)", "Tiempo ejecución (s)"]:
        moments_display[column] = moments_display[column].map(lambda value: f"{value:.2f}")
    moments_display["Diferencia de posición"] = moments_display["Diferencia de posición"].map(lambda value: f"{value:.4f}")
    _render_table_box(moments_display[[
        "Tiempo referencia (s)",
        "Tiempo ejecución (s)",
        "Punto corporal",
        "Parte del cuerpo",
        "Diferencia de posición",
        "Severidad",
    ]], header_color="#FF0F00", box_color="#FF0F00")

    st.markdown(
        """
        <div class="mitotl-reading-box">
            <div class="mitotl-reading-title">Sobre los clips críticos</div>
            <div>
                Cada clip muestra un momento donde la diferencia fue mayor para que
                puedas practicarlo sin recorrer todo el video. Los tiempos corresponden
                al video de referencia y al video de ejecución.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not st.session_state.get("critical_clips"):
        clips: list[dict[str, Any]] = []
        with st.spinner("Extrayendo clips cortos..."):
            try:
                for index, moment in enumerate(moments, start=1):
                    clips.append({
                        "index": index,
                        "moment": moment,
                        "video": create_aligned_clip(
                            reference_path,
                            execution_path,
                            center_reference_time_sec=moment["reference_time_sec"],
                            reference_frames=reference_frames,
                            execution_frames=execution_frames,
                            alignment=alignment,
                            frame_similarity_records=records,
                            reference_analysis_fps=reference_fps,
                            execution_analysis_fps=execution_fps,
                            highlighted_landmarks={str(moment["landmark"])},
                        ),
                    })
            except VisualizationError as error:
                st.error(str(error))
                return
        st.session_state["critical_clips"] = clips

    for clip in st.session_state.get("critical_clips", []):
        moment = clip["moment"]
        landmark_label = LANDMARK_LABELS.get(moment.get("landmark"), moment.get("landmark", "punto corporal"))
        st.markdown(
            f"**Momento {clip['index']}** · referencia {moment['reference_time_sec']:.2f} s "
            f"· ejecución {moment['execution_time_sec']:.2f} s · {landmark_label}"
        )
        st.video(str(clip["video"]))
        st.download_button(
            f"Descargar Momento {clip['index']}",
            data=Path(clip["video"]).read_bytes(),
            file_name=f"mitotl_momento_{clip['index']}.mp4",
            mime="video/mp4",
            key=f"download_critical_clip_{clip['index']}",
        )


def main() -> None:
    visual_review_mode = _render_instructions()
    inventory = _load_inventory()
    result = _load_saved_session() if visual_review_mode else st.session_state.get("analysis_result")
    if visual_review_mode and result is None:
        st.sidebar.warning("No se encontró la sesión JSON guardada.")
    horizontal_logo_path = _brand_asset("horizontal-logo-color.png")
    if horizontal_logo_path.exists():
        st.image(str(horizontal_logo_path), width=260)
    else:
        st.title("Mitotl IA")
    st.write("Compara un video de referencia con tu ejecución y recibe una guía educativa de práctica.")
    st.caption(
        "Las referencias del catálogo provienen de AIST Dance Video Database "
        "(https://aistdancedb.ongaaccel.jp/). Uso sujeto a sus términos de uso."
    )

    st.markdown(
        """
        <style>
        [role="tablist"] {
            display: flex !important;
            width: 100% !important;
            gap: 0 !important;
        }
        [role="tablist"] > div {
            flex: 1 1 0 !important;
            width: 25% !important;
            max-width: none !important;
        }
        [role="tablist"] [role="tab"] {
            display: flex !important;
            flex: 1 1 0 !important;
            width: 100% !important;
            max-width: none !important;
            justify-content: center !important;
            text-align: center !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    videos_tab, kpis_tab, visualizations_tab, agent_tab = st.tabs(
        ["Videos", "Resultados", "Visualizaciones", "Asistente"]
    )

    with videos_tab:
        reference_column, execution_column = st.columns(2, gap="large")
        with reference_column:
            reference_path = _reference_selector(inventory)
            if reference_path is not None:
                _render_video_box(reference_path)
                st.caption(f"Referencia cargada: {reference_path.name}")

        with execution_column:
            st.markdown("### Video de ejecución")
            st.markdown(
                "<div style='height: 96px;'></div>",
                unsafe_allow_html=True,
            )
            uploaded_execution = st.file_uploader(
                "Selecciona tu ejecución",
                type=["mp4", "mov", "webm"],
                key="execution_upload",
            )
            execution_path = None
            if uploaded_execution is not None:
                if st.session_state.get("execution_upload_name") != uploaded_execution.name:
                    st.session_state["execution_upload_path"] = _save_uploaded_file(uploaded_execution, "mitotl_execution_")
                    st.session_state["execution_upload_name"] = uploaded_execution.name
                execution_path = Path(st.session_state["execution_upload_path"])
                _render_video_box(execution_path)
                st.caption(f"Ejecución cargada: {execution_path.name}")

        if st.button("Analizar sesión", type="primary", disabled=reference_path is None or execution_path is None):
            analysis_started_at = time.perf_counter()
            with st.status("Analizando sesión", expanded=True) as status:
                progress_bar = st.progress(0, text="Preparando análisis")
                elapsed_placeholder = st.empty()

                def update_progress(stage: str, progress: float) -> None:
                    elapsed = time.perf_counter() - analysis_started_at
                    progress_bar.progress(int(progress * 100), text=stage)
                    elapsed_placeholder.caption(f"Tiempo transcurrido: {elapsed:.1f} s")

                try:
                    result = analyze_session(
                        reference_path,
                        execution_path,
                        progress_callback=update_progress,
                    )
                except PipelineError as error:
                    status.update(label="No fue posible completar el análisis", state="error")
                    st.error(str(error))
                    return
                elapsed = time.perf_counter() - analysis_started_at
                progress_bar.progress(100, text="Análisis completado")
                elapsed_placeholder.success(f"Tiempo total: {elapsed:.1f} s")
                status.update(label="Análisis completado", state="complete")
            st.session_state["analysis_result"] = result
            st.session_state["analysis_video_paths"] = {
                "reference": str(reference_path),
                "execution": str(execution_path),
            }
            st.session_state.pop("critical_clips", None)
            st.session_state.pop("aligned_video", None)
            st.session_state.pop("agent_messages", None)
            st.session_state.pop("session_report_pdf", None)
            st.success("Sesión analizada correctamente. Consulta las pestañas Resultados y Visualizaciones.")

    with kpis_tab:
        if result is None:
            st.info("Ejecuta primero el análisis desde la pestaña Videos.")
        else:
            _render_kpis(result)
            _render_temporal_sync(result)
            _render_recommendations(result)
            _render_findings(result)
            _render_pdf_download(result)

    with visualizations_tab:
        _render_visualizations(result)

    with agent_tab:
        _render_agent(result)


if __name__ == "__main__":
    main()
