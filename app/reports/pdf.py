from __future__ import annotations

import io
import os
import uuid
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.reports.visuals import farm_location_snapshot, weather_snapshot
from app.storage.database import save_report

BLACK = colors.black
DARK_GREY = colors.HexColor("#333333")
MID_GREY = colors.HexColor("#777777")
LIGHT_GREY = colors.HexColor("#E5E5E5")
VERY_LIGHT_GREY = colors.HexColor("#F5F5F5")


def _font_candidates() -> dict[str, list[Path]]:
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    return {
        "regular": [
            windir / "Fonts" / "times.ttf",
            Path("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf"),
            Path("/usr/share/fonts/truetype/tinos/Tinos-Regular.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
        ],
        "bold": [
            windir / "Fonts" / "timesbd.ttf",
            Path("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf"),
            Path("/usr/share/fonts/truetype/tinos/Tinos-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
        ],
        "italic": [
            windir / "Fonts" / "timesi.ttf",
            Path("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Italic.ttf"),
            Path("/usr/share/fonts/truetype/tinos/Tinos-Italic.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"),
        ],
        "bold_italic": [
            windir / "Fonts" / "timesbi.ttf",
            Path("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold_Italic.ttf"),
            Path("/usr/share/fonts/truetype/tinos/Tinos-BoldItalic.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf"),
        ],
    }


def _first_font_file(paths: Iterable[Path]) -> Path | None:
    """Return the first readable font file, never a directory placeholder."""
    for path in paths:
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


def _register_fonts() -> tuple[str, str, str, str]:
    names = {
        "regular": "COCO-Times",
        "bold": "COCO-Times-Bold",
        "italic": "COCO-Times-Italic",
        "bold_italic": "COCO-Times-BoldItalic",
    }
    candidates = _font_candidates()
    resolved = {style: _first_font_file(paths) for style, paths in candidates.items()}
    if not all(resolved.values()):
        return "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic"

    try:
        for style, path in resolved.items():
            if names[style] not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(names[style], str(path)))
        pdfmetrics.registerFontFamily(
            "COCO-Times",
            normal=names["regular"],
            bold=names["bold"],
            italic=names["italic"],
            boldItalic=names["bold_italic"],
        )
    except (OSError, TTFError, ValueError):
        # Font availability varies across local Windows, CI, and Render Linux.
        # A missing/corrupt optional system font must never prevent FastAPI startup.
        return "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic"

    return names["regular"], names["bold"], names["italic"], names["bold_italic"]


FONT_REGULAR, FONT_BOLD, FONT_ITALIC, FONT_BOLD_ITALIC = _register_fonts()


def _label(value: str) -> str:
    return str(value).replace("_", " ").strip().title()


def _number(value: Any, digits: int = 2) -> str:
    if value is None:
        return "Not available"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not (number == number and abs(number) != float("inf")):
        return "Not available"
    if abs(number - round(number)) < 1e-10:
        return f"{int(round(number)):,}"
    return f"{number:,.{digits}f}".rstrip("0").rstrip(".")


def _percent(value: Any, digits: int = 1, already_percent: bool = False) -> str:
    if value is None:
        return "Not available"
    number = float(value)
    if not already_percent:
        number *= 100.0
    return f"{number:.{digits}f}%"


def _text(value: Any, max_chars: int = 1200) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return _number(value, 4)
    if isinstance(value, (list, tuple)):
        value = "; ".join(_text(item, 180) for item in value[:30])
    elif isinstance(value, dict):
        value = "; ".join(f"{_label(k)}: {_text(v, 180)}" for k, v in list(value.items())[:30])
    result = str(value).replace("–", "-").replace("—", "-")
    return result if len(result) <= max_chars else result[: max_chars - 3] + "..."


def _p(value: Any, style) -> Paragraph:
    return Paragraph(escape(_text(value)), style)


def _styles():
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = FONT_REGULAR
        style.textColor = BLACK
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontName=FONT_BOLD,
        fontSize=18, leading=22, alignment=TA_CENTER, textColor=BLACK, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle", parent=styles["BodyText"], fontName=FONT_REGULAR,
        fontSize=10, leading=13, alignment=TA_CENTER, textColor=BLACK, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading2"], fontName=FONT_BOLD,
        fontSize=13, leading=16, textColor=BLACK, spaceBefore=10, spaceAfter=6,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="Subsection", parent=styles["Heading3"], fontName=FONT_BOLD,
        fontSize=11, leading=14, textColor=BLACK, spaceBefore=8, spaceAfter=4,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="BodyFormal", parent=styles["BodyText"], fontName=FONT_REGULAR,
        fontSize=9.4, leading=13, alignment=TA_JUSTIFY, textColor=BLACK, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader", parent=styles["BodyText"], fontName=FONT_BOLD,
        fontSize=8.2, leading=10, textColor=BLACK,
    ))
    styles.add(ParagraphStyle(
        name="TableBody", parent=styles["BodyText"], fontName=FONT_REGULAR,
        fontSize=8, leading=10, textColor=BLACK,
    ))
    styles.add(ParagraphStyle(
        name="Caption", parent=styles["BodyText"], fontName=FONT_ITALIC,
        fontSize=8, leading=10, alignment=TA_CENTER, textColor=BLACK, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Small", parent=styles["BodyText"], fontName=FONT_REGULAR,
        fontSize=7.5, leading=9.5, textColor=BLACK,
    ))
    return styles


def _table(rows: list[list[Any]], styles, widths: list[float] | None = None, align_numeric_from: int | None = None) -> Table:
    normalized: list[list[Any]] = []
    for row_index, row in enumerate(rows):
        normalized.append([
            value if isinstance(value, Paragraph) else Paragraph(escape(_text(value)), styles["TableHeader"] if row_index == 0 else styles["TableBody"])
            for value in row
        ])
    table = Table(normalized, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
        ("TEXTCOLOR", (0, 0), (-1, -1), BLACK),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
        ("GRID", (0, 0), (-1, -1), 0.35, MID_GREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if align_numeric_from is not None:
        commands.append(("ALIGN", (align_numeric_from, 1), (-1, -1), "RIGHT"))
    table.setStyle(TableStyle(commands))
    return table


def _kv_table(items: Iterable[tuple[str, Any]], styles, widths=(62 * mm, 98 * mm)) -> Table:
    rows = [["Field", "Value"]]
    for key, value in items:
        rows.append([_label(key), _text(value)])
    return _table(rows, styles, list(widths))


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(MID_GREY)
    canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
    canvas.setFont(FONT_REGULAR, 7.5)
    canvas.setFillColor(BLACK)
    canvas.drawString(18 * mm, 7.5 * mm, "COCO-AID Decision-Support Research Report")
    canvas.drawRightString(A4[0] - 18 * mm, 7.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _append_bullets(story: list, items: Iterable[Any], styles) -> None:
    for item in items:
        story.append(Paragraph(f"- {escape(_text(item))}", styles["BodyFormal"]))


def _annual_table(rows: list[dict[str, Any]], styles) -> Table | Paragraph:
    if not rows:
        return Paragraph("No annual production outlook was attached.", styles["BodyFormal"])
    indexes = sorted(set([0, len(rows) - 1] + list(range(4, len(rows), 5))))
    data = [["Year", "Coconut w/ husk (t)", "Mature (t)", "Young (t)", "Mature share", "Young share"]]
    for index in indexes:
        row = rows[index]
        data.append([
            row.get("year"), _number(row.get("coconut_w_husk_tons"), 3),
            _number(row.get("coconut_mature_tons"), 3), _number(row.get("coconut_young_tons"), 3),
            _percent(row.get("mature_share"), 1), _percent(row.get("young_share"), 1),
        ])
    return _table(data, styles, [18 * mm, 35 * mm, 28 * mm, 28 * mm, 25 * mm, 25 * mm], align_numeric_from=1)


def _event_table(events: list[dict[str, Any]], styles) -> Table | Paragraph:
    if not events:
        return Paragraph("No major event periods were flagged in the selected trajectory.", styles["BodyFormal"])
    rows = [["Event", "Start", "End", "Severity", "Estimated loss", "Trees affected"]]
    for event in events[:35]:
        rows.append([
            event.get("label"), event.get("start_date"), event.get("end_date"),
            f"{_number(event.get('severity_percent', float(event.get('peak_severity', 0)) * 100), 1)}/100",
            f"{_number(event.get('estimated_production_loss_tons'), 3)} t",
            _number(event.get("estimated_trees_affected"), 0),
        ])
    return _table(rows, styles, [33 * mm, 24 * mm, 24 * mm, 23 * mm, 30 * mm, 26 * mm], align_numeric_from=3)


def _pest_table(pests: list[dict[str, Any]], styles) -> Table | Paragraph:
    if not pests:
        return Paragraph("No pest-specific assessment was attached.", styles["BodyFormal"])
    rows = [["Pest", "Scientific name", "Outbreak score", "Risk class", "Primary affected part"]]
    for pest in pests:
        rows.append([
            pest.get("common_name"), pest.get("scientific_name"),
            f"{_number(pest.get('outbreak_score'), 1)}/100", pest.get("risk_class"), pest.get("affected_part"),
        ])
    return _table(rows, styles, [37 * mm, 38 * mm, 25 * mm, 23 * mm, 37 * mm])


def generate_pdf(analysis: dict[str, Any], analysis_id: str | None = None) -> tuple[str, Path]:
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a dictionary")
    if "result" in analysis and isinstance(analysis["result"], dict):
        analysis = analysis["result"]

    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    report_id = str(uuid.uuid4())
    path = settings.reports_dir / f"COCO-AID_Report_{report_id[:8]}.pdf"
    styles = _styles()
    doc = SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=18 * mm,
        title="COCO-AID Decision-Support Report", author="COCO-AID Research Prototype",
    )

    overview = analysis.get("overview") or {}
    farm = analysis.get("farm_assessment") or {}
    pest = analysis.get("pest_risk") or {}
    suitability = analysis.get("land_suitability") or {}
    official = analysis.get("official_production_reference") or {}
    climate = analysis.get("climate_projection") or {}
    simulation = analysis.get("recommended_simulation") or {}
    comparison = analysis.get("scenario_comparison") or {}
    forecast = analysis.get("farm_site_forecast") or {}
    pest_specific = analysis.get("pest_specific") or {}
    health_snapshot = analysis.get("farm_health_snapshot") or {}
    rehab = analysis.get("rehabilitation_map") or {}
    rehab_events = analysis.get("rehabilitation_event_plans") or {}
    metadata = analysis.get("metadata") or {}

    story: list[Any] = [
        Paragraph("COCO-AID DECISION-SUPPORT REPORT", styles["ReportTitle"]),
        Paragraph(
            "Bayesian Probabilistic Agroecosystem Simulation and Geospatial AI-Based "
            "Decision-Support Framework for Coconut Rehabilitation",
            styles["ReportSubtitle"],
        ),
        Paragraph(
            "This document is a formal research-prototype output. It combines available official provincial "
            "statistics with farm inputs, mathematical models, short-term weather forecasts when available, "
            "and scenario-based long-term projections. Results require field verification and professional review.",
            styles["BodyFormal"],
        ),
        Spacer(1, 6),
    ]

    story.append(Paragraph("1. Executive Summary", styles["Section"]))
    story.append(_kv_table([
        ("Farm", overview.get("farm_name", forecast.get("farm", {}).get("name"))),
        ("Current annual production", f"{_number(overview.get('current_production_tons'), 3)} metric tons"),
        ("Projected end-year median", f"{_number(overview.get('projected_end_median_tons'), 3)} metric tons"),
        ("Rehabilitation probability", _percent(overview.get("rehabilitation_probability"))),
        ("Severe-loss probability", _percent(overview.get("severe_loss_probability"))),
        ("Bayesian pest posterior", _percent(overview.get("pest_risk_probability", pest.get("posterior_probability")))),
        ("Land suitability", _percent(overview.get("land_suitability_percentage", suitability.get("percentage")), already_percent=True)),
        ("Recommended intervention", _label(overview.get("recommended_intervention", comparison.get("recommended_intervention", "Not available")))),
        ("Climate scenario", overview.get("climate_scenario", forecast.get("scenario"))),
    ], styles))

    story.append(Paragraph("2. Farm Location, Shape, and Data Quality", styles["Section"]))
    forecast_farm = forecast.get("farm") or {}
    location_image = farm_location_snapshot(forecast_farm)
    story.append(Image(location_image, width=160 * mm, height=75.9 * mm))
    story.append(Paragraph(
        "Figure 1. Farm centroid and entered boundary shape. The diagram is generated from the saved farm coordinates and is not a cadastral or legal land survey.",
        styles["Caption"],
    ))
    story.append(_kv_table([
        ("Entered area", f"{_number(farm.get('entered_area_hectares'), 3)} hectares"),
        ("Polygon area", f"{_number(farm.get('polygon_area_hectares'), 3)} hectares" if farm.get("polygon_area_hectares") is not None else "Not provided"),
        ("Tree density", f"{_number(farm.get('tree_density_per_hectare'), 2)} trees per hectare"),
        ("Productive and recovering fraction", _percent(farm.get("productive_recovering_fraction"))),
        ("At-risk tree fraction", _percent(farm.get("at_risk_fraction"))),
        ("Calculated yield", f"{_number(farm.get('calculated_yield_tons_per_hectare'), 3)} t/ha"),
        ("Data quality score", _percent(farm.get("data_quality_score"))),
        ("Data quality class", farm.get("data_quality_class")),
    ], styles))
    _append_bullets(story, farm.get("warnings") or [], styles)

    story.append(Paragraph("3. Official Provincial Production Reference", styles["Section"]))
    product_data = official.get("products") or {}
    story.append(_kv_table([
        ("Province", official.get("province")),
        ("Region", official.get("region")),
        ("Reference level", official.get("reference_level")),
        ("Latest official Coconut w/ husk", f"{_number(product_data.get('coconut_w_husk', {}).get('latest_official_2025_tons'), 2)} t"),
        ("Latest official Coconut Mature", f"{_number(product_data.get('coconut_mature', {}).get('latest_official_2025_tons'), 2)} t"),
        ("Latest official Coconut Young", f"{_number(product_data.get('coconut_young', {}).get('latest_official_2025_tons'), 2)} t"),
        ("Source", official.get("metadata", {}).get("source")),
        ("Table code", official.get("metadata", {}).get("table_code")),
    ], styles))

    story.append(Paragraph("4. Climate and Farm Production Outlook", styles["Section"]))
    annual_summary = climate.get("annual_summary") or {}
    story.append(_kv_table([
        ("Climate period", climate.get("display_label", climate.get("period"))),
        ("Scenario", climate.get("scenario", forecast.get("scenario"))),
        ("Mean temperature", f"{_number(annual_summary.get('mean_temperature_c'), 2)} C"),
        ("Annual rainfall", f"{_number(annual_summary.get('annual_precipitation_mm'), 1)} mm"),
        ("Forecast horizon", f"{forecast.get('effective_start_date', 'Not available')} to {forecast.get('effective_end_date', 'Not available')}"),
        ("Timeline resolution", forecast.get("timeline_resolution")),
        ("Monte Carlo runs", forecast.get("runs", metadata.get("simulation_count_per_intervention"))),
    ], styles))
    story.append(Paragraph(
        "Long-term weekly weather fields are climate-conditioned scenario paths. They are not exact forecasts of future clouds, rainfall, heat waves, or storm dates.",
        styles["BodyFormal"],
    ))

    story.append(Paragraph("5. Critical Weather Dates", styles["Section"]))
    critical = forecast.get("critical_weather_frames") or []
    if critical:
        farm_position = forecast.get("farm_map_position") or {}
        marker = {"map_x": farm_position.get("x", 0.5), "map_y": farm_position.get("y", 0.5)}
        for index, frame in enumerate(critical, start=2):
            image_data = weather_snapshot(frame, marker)
            report_image = Image(image_data, width=160 * mm, height=86.8 * mm)
            story.append(KeepTogether([
                Paragraph(f"Figure {index}. Critical weather frame: {escape(_text(frame.get('label') or frame.get('week_start')))}", styles["Subsection"]),
                report_image,
                Paragraph(
                    f"Rainfall {_number(frame.get('rainfall_mm'), 1)} mm; peak intensity {_number(frame.get('rain_intensity_mm_h'), 1)} mm/h; "
                    f"maximum temperature {_number(frame.get('temperature_max_c'), 1)} C; farm condition {_percent(frame.get('farm_condition_score'))}. "
                    "Colored surfaces represent the forecast or scenario rain field used by the farm model.",
                    styles["Caption"],
                ),
            ]))
    else:
        story.append(Paragraph("No critical-date weather snapshots were attached to this report.", styles["BodyFormal"]))

    story.append(PageBreak())
    story.append(Paragraph("6. Three-Product Production Projection", styles["Section"]))
    story.append(_annual_table(forecast.get("annual_by_product") or [], styles))
    product_model = forecast.get("product_model") or {}
    if product_model:
        story.append(Spacer(1, 5))
        story.append(_kv_table(product_model.items(), styles))

    story.append(Paragraph("7. Extreme-Weather Risk Timeline", styles["Section"]))
    story.append(_event_table(forecast.get("extreme_events") or [], styles))
    story.append(Paragraph(
        "Estimated loss is calculated from event type, peak and mean severity, event duration, and the baseline weekly production. "
        "This makes the reported loss increase consistently as severity or duration increases.",
        styles["BodyFormal"],
    ))

    story.append(Paragraph("8. Bayesian and Pest-Specific Risk Assessment", styles["Section"]))
    story.append(_kv_table([
        ("Bayesian prior", _percent(pest.get("prior_probability"))),
        ("Bayesian posterior", _percent(pest.get("posterior_probability"))),
        ("Bayesian risk class", pest.get("risk_class")),
        ("Highest pest-specific outbreak score", f"{_number(pest_specific.get('highest_outbreak_score'), 1)}/100"),
        ("Top pest-specific risk", pest_specific.get("top_risk_pest")),
        ("Overall pest pressure", f"{_number(pest_specific.get('overall_outbreak_pressure'), 1)}/100"),
    ], styles))
    story.append(_pest_table(pest_specific.get("pests") or [], styles))
    for pest_row in (pest_specific.get("pests") or [])[:5]:
        story.append(Paragraph(f"{escape(_text(pest_row.get('common_name')))} recommendations", styles["Subsection"]))
        _append_bullets(story, pest_row.get("ai_recommendations") or [], styles)

    story.append(Paragraph("9. Land Suitability and Farm Health", styles["Section"]))
    story.append(_kv_table([
        ("Suitability percentage", _percent(suitability.get("percentage"), already_percent=True)),
        ("Suitability class", suitability.get("class")),
        ("Limiting factors", suitability.get("limiting_factors")),
        ("Baseline current-condition grid", f"{rehab.get('rows', 'Not available')} x {rehab.get('cols', 'Not available')}"),
        ("Baseline high-priority cells", health_snapshot.get("rehabilitation_summary", {}).get("high_priority_cells")),
        ("Baseline visible cells", len(rehab.get("cells") or [])),
    ], styles))
    components = suitability.get("component_scores") or {}
    if components:
        rows = [["Suitability component", "Membership score"]] + [[_label(key), _percent(value)] for key, value in components.items()]
        story.append(_table(rows, styles, [95 * mm, 55 * mm], align_numeric_from=1))
    plans = rehab_events.get("plans") or []
    if plans:
        story.append(Paragraph("Event-Linked Rehabilitation Schedule", styles["Subsection"]))
        rows = [["Event", "Event period", "Inspect", "Rehabilitation", "Yellow / Red"]]
        for plan in plans[:12]:
            rows.append([
                plan.get("event_label"),
                f"{plan.get('event_start_date')} to {plan.get('event_end_date')}",
                plan.get("recommended_assessment_date"),
                plan.get("recommended_rehabilitation_date"),
                f"{(plan.get('counts') or {}).get('Needs inspection', 0)} / {(plan.get('counts') or {}).get('Needs Rehabilitation', 0)}",
            ])
        story.append(_table(rows, styles, [43 * mm, 44 * mm, 27 * mm, 30 * mm, 22 * mm], align_numeric_from=4))
        story.append(Paragraph(
            "Green zones indicate no immediate damage action, yellow zones require field inspection, and red zones indicate likely rehabilitation after field verification.",
            styles["BodyFormal"],
        ))

    story.append(Paragraph("10. Intervention Comparison", styles["Section"]))
    ranking = comparison.get("ranking") or []
    if ranking:
        rows = [["Rank", "Intervention", "Utility", "Final median", "Recovery", "Severe loss"]]
        for item in ranking:
            rows.append([
                item.get("rank"), _label(item.get("intervention")), _number(item.get("expected_utility"), 3),
                f"{_number(item.get('final_median_tons'), 3)} t", _percent(item.get("rehabilitation_probability")),
                _percent(item.get("severe_loss_probability")),
            ])
        story.append(_table(rows, styles, [15 * mm, 43 * mm, 27 * mm, 28 * mm, 25 * mm, 25 * mm], align_numeric_from=2))
    else:
        story.append(Paragraph("No intervention comparison was available.", styles["BodyFormal"]))

    story.append(Paragraph("Model Versions, Provenance, and Limitations", styles["Subsection"]))
    story.append(_kv_table([
        ("Calculation version", metadata.get("calculation_version")),
        ("Parameter version", metadata.get("parameter_version")),
        ("Model versions", metadata.get("model_versions")),
        ("Random seed", metadata.get("random_seed", forecast.get("seed"))),
        ("Generated at", datetime.now(UTC).isoformat()),
        ("Data source type", metadata.get("data_source_type", forecast.get("data_source_type"))),
    ], styles))
    limitations: list[str] = []
    for source in [metadata, simulation, comparison, forecast, pest_specific]:
        if isinstance(source, dict) and isinstance(source.get("limitations"), list):
            limitations.extend(str(item) for item in source["limitations"])
    limitations.extend([
        "The long-term weather path is a plausible climate-conditioned scenario, not an exact forecast to 2050.",
        "Pest-specific scores are inspection priorities and do not replace laboratory or expert identification.",
        "Farm-scale accuracy requires locally measured soil, pest, weather, tree-state, and production records.",
    ])
    _append_bullets(story, list(dict.fromkeys(limitations)), styles)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    save_report(report_id, path, analysis_id, report_type="pdf")
    return report_id, path
