"""Generación de reportes PDF para sesiones de Mitotl IA."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Mapping

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    Image as ReportImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.utils import ImageReader

from .prompts import BODY_PART_LABELS, LANDMARK_LABELS


MITOTL_CYAN = colors.HexColor("#00F0FF")
MITOTL_BLUE = colors.HexColor("#00C8FF")
MITOTL_TEAL = colors.HexColor("#064653")
MITOTL_GREEN = colors.HexColor("#39FF88")
MITOTL_MAGENTA = colors.HexColor("#FF39B0")
MITOTL_RED = colors.HexColor("#FF0F00")
PAPER_DARK = colors.HexColor("#10171C")
TEXT_DARK = colors.HexColor("#17313A")
TEXT_MUTED = colors.HexColor("#50636A")
PALE_BLUE = colors.HexColor("#E8F9FC")
PALE_MAGENTA = colors.HexColor("#FFF0FA")
PALE_RED = colors.HexColor("#FFF1F0")


def _escape(value: Any) -> str:
    text = str(value if value is not None else "-")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _traffic_signal(value: float, *, percent: bool = True) -> tuple[colors.Color, str]:
    ratio = float(value) / 100 if percent else float(value)
    if ratio <= 0.30:
        return MITOTL_RED, "Necesita atencion"
    if ratio <= 0.60:
        return colors.HexColor("#D49A00"), "En proceso"
    return colors.HexColor("#087A5A"), "Buen parecido"


class _HeaderRule(Flowable):
    """Linea de identidad visual para encabezados del reporte."""

    def __init__(self, width: float = 7.0 * inch, height: float = 5):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self) -> None:
        self.canv.setStrokeColor(MITOTL_CYAN)
        self.canv.setLineWidth(3)
        self.canv.line(0, 1, self.width, 1)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "MitotlTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=24, leading=28, textColor=MITOTL_TEAL, alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "MitotlSubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, leading=14, textColor=TEXT_MUTED, spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "MitotlSection", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=15, leading=18, textColor=MITOTL_TEAL, spaceBefore=12,
            spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "MitotlBody", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.2, leading=13, textColor=TEXT_DARK,
        ),
        "small": ParagraphStyle(
            "MitotlSmall", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8, leading=10, textColor=TEXT_MUTED,
        ),
        "card_label": ParagraphStyle(
            "MitotlCardLabel", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=9, leading=11, textColor=TEXT_MUTED,
        ),
        "table_header": ParagraphStyle(
            "MitotlTableHeader", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=8.5, leading=10, textColor=colors.white, alignment=TA_CENTER,
        ),
        "card_value": ParagraphStyle(
            "MitotlCardValue", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=20, leading=23, textColor=TEXT_DARK,
        ),
        "center": ParagraphStyle(
            "MitotlCenter", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=9, leading=11, alignment=TA_CENTER, textColor=TEXT_DARK,
        ),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_escape(text), style)


def _metadata_table(result: Mapping[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    reference = result.get("reference", {})
    execution = result.get("execution", {})
    rows = [
        [_p("Dato", styles["table_header"]), _p("Video de referencia", styles["table_header"]), _p("Video de ejecucion", styles["table_header"])],
        [_p("Archivo", styles["body"]), _p(reference.get("file_name"), styles["body"]), _p(execution.get("file_name"), styles["body"])],
        [_p("Duracion", styles["body"]), _p(f"{float(reference.get('duration_sec', 0) or 0):.2f} s", styles["body"]), _p(f"{float(execution.get('duration_sec', 0) or 0):.2f} s", styles["body"])],
        [_p("Frames", styles["body"]), _p(reference.get("frame_count"), styles["body"]), _p(execution.get("frame_count"), styles["body"])],
    ]
    table = Table(rows, colWidths=[1.15 * inch, 2.55 * inch, 2.55 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MITOTL_TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B6D5DA")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _score_cards(result: Mapping[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    score = result.get("score", {})
    body_scores = score.get("body_scores_xy", {})
    cards = [("Score general", score.get("score_general", 0), True)]
    labels = {"arms": "Brazos", "legs": "Piernas", "torso": "Torso", "head": "Cabeza"}
    cards.extend((labels[key], value, False) for key, value in sorted(body_scores.items(), key=lambda item: item[1]))
    cells = []
    for label, value, featured in cards:
        signal_color, status = _traffic_signal(value)
        cell = [
            _p(label, styles["card_label"]),
            _p(f"{float(value):.2f}%", styles["card_value"]),
            Paragraph(f'<font color="{signal_color.hexval()}"><b>{status}</b></font>', styles["small"]),
        ]
        cells.append(cell)
    def card_table(cell: list[Flowable], width: float, background: colors.Color, border: colors.Color) -> Table:
        card = Table([[item] for item in cell], colWidths=[width])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), background),
            ("BOX", (0, 0), (-1, -1), 0.9, border),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return card

    featured = card_table(cells[0], 6.25 * inch, PALE_BLUE, MITOTL_CYAN)
    body_cells = [
        [card_table(cells[1], 3.05 * inch, colors.HexColor("#F1FAF8"), MITOTL_TEAL), card_table(cells[2], 3.05 * inch, colors.HexColor("#F1FAF8"), MITOTL_TEAL)],
        [card_table(cells[3], 3.05 * inch, colors.HexColor("#F1FAF8"), MITOTL_TEAL), card_table(cells[4], 3.05 * inch, colors.HexColor("#F1FAF8"), MITOTL_TEAL)],
    ]
    body_table = Table(body_cells, colWidths=[3.05 * inch, 3.05 * inch])
    body_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1FAF8")),
        ("BOX", (0, 0), (-1, -1), 0.8, MITOTL_TEAL),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B6D5DA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return Table([[featured], [Spacer(1, 7)], [body_table]], colWidths=[6.25 * inch])


def _temporal_table(result: Mapping[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    segment_scores = result.get("score", {}).get("segment_scores", [])
    headers = ["Segmento", "Parecido en el tiempo", "Ref. (s)", "Ejec. (s)"]
    rows = [[_p(header, styles["table_header"]) for header in headers]]
    for segment in segment_scores:
        similarity = float(segment.get("temporal_similarity", 0) or 0)
        _, status = _traffic_signal(similarity, percent=False)
        rows.append([
            _p(segment.get("segment"), styles["center"]),
            Paragraph(f"{similarity:.3f}<br/><font size=7>{status}</font>", styles["center"]),
            _p(f"{float(segment.get('reference_start_time_sec', 0)):.2f} - {float(segment.get('reference_end_time_sec', 0)):.2f} s", styles["center"]),
            _p(f"{float(segment.get('execution_start_time_sec', 0)):.2f} - {float(segment.get('execution_end_time_sec', 0)):.2f} s", styles["center"]),
        ])
    table = Table(rows, colWidths=[0.95 * inch, 1.6 * inch, 1.85 * inch, 1.85 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MITOTL_MAGENTA),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8B9D0")),
        ("BACKGROUND", (0, 1), (-1, -1), PALE_MAGENTA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _recommendation_table(result: Mapping[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    recommendations = result.get("feedback", {}).get("recommendations", [])
    rows = [[_p("Prioridad", styles["table_header"]), _p("Enfoque", styles["table_header"]), _p("Que practicar", styles["table_header"])]]
    for index, recommendation in enumerate(recommendations, start=1):
        if recommendation.get("type") == "body_part":
            key = recommendation.get("body_part", recommendation.get("parte_cuerpo", "-"))
            focus = BODY_PART_LABELS.get(key, key)
            value = float(recommendation.get("similarity_xy_percent", 0) or 0)
            measure = f"Parecido en pantalla: {value:.2f}%"
        else:
            focus = f"Segmento temporal {recommendation.get('segment', '-') }"
            value = float(recommendation.get("temporal_similarity", 0) or 0)
            measure = f"Parecido en el tiempo: {value:.3f}"
        rows.append([
            _p(f"{index}", styles["center"]),
            Paragraph(f"<b>{_escape(focus)}</b><br/><font size=8>{_escape(measure)}</font>", styles["body"]),
            _p(recommendation.get("recommendation", "-"), styles["body"]),
        ])
    table = Table(rows, colWidths=[0.8 * inch, 2.0 * inch, 3.45 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MITOTL_TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B6D5DA")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _findings_table(result: Mapping[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    findings = result.get("feedback", {}).get("top_findings", [])[:10]
    headers = ["Ref. (s)", "Ejec. (s)", "Punto corporal", "Parte", "Diferencia", "Severidad"]
    rows = [[_p(header, styles["table_header"]) for header in headers]]
    for finding in findings:
        landmark = LANDMARK_LABELS.get(finding.get("landmark"), finding.get("landmark", "-"))
        body_part = BODY_PART_LABELS.get(finding.get("parte_cuerpo"), finding.get("parte_cuerpo", "-"))
        rows.append([
            _p(f"{float(finding.get('reference_time_sec', 0)):.2f} s", styles["center"]),
            _p(f"{float(finding.get('execution_time_sec', 0)):.2f} s", styles["center"]),
            _p(landmark, styles["body"]),
            _p(body_part, styles["body"]),
            _p(f"{float(finding.get('diferencia_xy', 0)):.4f}", styles["center"]),
            _p(finding.get("severidad", "-"), styles["center"]),
        ])
    table = Table(rows, colWidths=[0.8 * inch, 0.8 * inch, 1.45 * inch, 1.15 * inch, 0.85 * inch, 0.85 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MITOTL_RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E6B8B5")),
        ("BACKGROUND", (0, 1), (-1, -1), PALE_RED),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _default_logo_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "brand" / "export" / "horizontal-logo-color.png"


def _logo_flowable(logo_path: str | Path | None) -> Flowable | Paragraph:
    path = Path(logo_path) if logo_path else _default_logo_path()
    if not path.exists():
        return _p("Mitotl IA", _styles()["title"])
    width, height = ImageReader(str(path)).getSize()
    target_width = 2.45 * inch
    target_height = target_width * height / width
    return ReportImage(str(path), width=target_width, height=target_height)


def build_session_report(
    result: Mapping[str, Any],
    *,
    logo_path: str | Path | None = None,
) -> bytes:
    """Construye un PDF descargable con el resumen de una sesion."""

    styles = _styles()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="Reporte de sesion - Mitotl IA",
        author="Mitotl IA",
    )
    score = result.get("score", {})
    story: list[Any] = [
        _logo_flowable(logo_path),
        Spacer(1, 3),
        _p("Reporte de comparacion y guia educativa de practica", styles["subtitle"]),
        _HeaderRule(),
        Spacer(1, 10),
        _p("Resumen de la sesion", styles["section"]),
        _metadata_table(result, styles),
        Spacer(1, 8),
        _score_cards(result, styles),
        _p("Sincronizacion temporal", styles["section"]),
        _temporal_table(result, styles),
        KeepTogether([
            _p("Recomendaciones", styles["section"]),
            _recommendation_table(result, styles),
        ]),
        KeepTogether([
            _p("Hallazgos principales", styles["section"]),
            _findings_table(result, styles),
        ]),
        _p("Limitaciones", styles["section"]),
        _p(
            "El resultado es una guia educativa basada en esta comparacion. "
            "Los scores no representan porcentajes de error ni una evaluacion profesional "
            "de danza. Las diferencias deben confirmarse visualmente considerando la calidad "
            "del video, la perspectiva de la camara y la deteccion de pose.",
            styles["body"],
        ),
    ]

    def footer(canvas: Any, document_obj: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D4E6E8"))
        canvas.line(document_obj.leftMargin, 0.42 * inch, letter[0] - document_obj.rightMargin, 0.42 * inch)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(document_obj.leftMargin, 0.25 * inch, "Mitotl IA - Analisis educativo de movimiento corporal")
        canvas.drawRightString(letter[0] - document_obj.rightMargin, 0.25 * inch, f"Pagina {document_obj.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def write_session_report(
    result: Mapping[str, Any],
    output_path: str | Path,
    *,
    logo_path: str | Path | None = None,
) -> Path:
    """Escribe un reporte PDF en una ruta indicada y la devuelve."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_session_report(result, logo_path=logo_path))
    return path
