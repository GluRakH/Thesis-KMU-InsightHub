from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from app.services.initiative_templates import template_for_dimension
from domain.models import MeasureCatalog


def _build_v11_payload(pipeline: dict[str, Any], answers: dict[str, Any], catalog: MeasureCatalog | None, timestamp: str) -> dict[str, Any]:
    assessments = {
        "BI": pipeline.get("bi", {}),
        "PA": pipeline.get("pa", {}),
    }

    evidence_overview: dict[str, dict[str, Any]] = {}
    for domain, assessment in assessments.items():
        dimension_scores = assessment.get("dimension_scores", {})
        critical_dimension = min(dimension_scores.items(), key=lambda item: item[1])[0] if dimension_scores else "N/A"
        top_items: list[dict[str, Any]] = []
        if catalog:
            for measure in catalog.measures:
                if measure.dimension == critical_dimension:
                    top_items = list(measure.evidence.get("trigger_items", []))[:3]
                    break

        evidence_overview[domain] = {
            "critical_dimension": critical_dimension,
            "top_items": top_items,
        }

    recommendations = {"now": [], "next": [], "later": []}
    if catalog:
        sorted_measures = sorted(catalog.measures, key=lambda item: item.suggested_priority)
        for index, measure in enumerate(sorted_measures, start=1):
            priority = dict(measure.priority or {})
            priority.setdefault("impact", float(measure.impact))
            priority.setdefault("effort", float(measure.effort))
            priority.setdefault("criticality_weight", 1.0)
            priority.setdefault("gap_weight", 1.0)
            score = measure.priority_score or (
                (priority["impact"] / max(1.0, priority["effort"]))
                * priority["criticality_weight"]
                * priority["gap_weight"]
            )
            priority["score"] = round(float(score), 4)
            if not priority.get("bucket"):
                priority["bucket"] = "now" if index <= 2 else "next" if index <= 4 else "later"

            kpi = dict(measure.kpi or {})
            kpi.setdefault("name", f"Fortschritt {measure.dimension or 'N/A'}")
            kpi.setdefault("target", "Mindestwert >= aktueller Baseline")
            kpi.setdefault("measurement", "Monatlicher Mittelwert der Dimensions-Items (0-100)")
            goal = measure.goal or f"Erreiche in {measure.dimension or 'N/A'} den nächsten stabilen Reifezustand durch '{measure.title or 'Maßnahme'}'."

            payload = {
                "id": measure.initiative_id or measure.measure_id or "N/A",
                "title": measure.title or "Ohne Titel",
                "goal": goal,
                "priority": priority,
                "dependencies": measure.dependencies,
                "kpi": kpi,
                "trigger_items": measure.evidence.get("trigger_items", []),
            }
            bucket = str(priority.get("bucket", "later")).lower()
            recommendations[bucket if bucket in recommendations else "later"].append(payload)

    return {
        "export_version": "1.1.0",
        "timestamp": timestamp,
        "summary": {
            "bi": pipeline.get("bi", {}),
            "pa": pipeline.get("pa", {}),
            "synthesis": pipeline.get("synthesis", {}),
        },
        "evidence_overview": evidence_overview,
        "recommendations": recommendations,
        "answers": answers,
    }


def build_export_payload(
    pipeline: dict[str, Any],
    answers: dict[str, Any],
    catalog: MeasureCatalog | None,
    export_version: str = "1.0.0",
    catalog_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    if export_version == "1.0.0":
        return {
            "export_version": "1.0.0",
            "timestamp": timestamp,
            "pipeline": pipeline,
            "answers": answers,
            "catalog": catalog.model_dump() if catalog else None,
        }
    if export_version == "1.1.0":
        return _build_v11_payload(pipeline, answers, catalog, timestamp)

    evidence_overview: dict[str, dict[str, Any]] = {}
    for domain, key in (("BI", "bi"), ("PA", "pa")):
        assessment = pipeline.get(key, {})
        top_items = list(assessment.get("critical_dimension_top_items", []))[:3]
        evidence_overview[domain] = {
            "critical_dimension": assessment.get("critical_dimension_id", "N/A"),
            "critical_dimension_severity": round(float(assessment.get("critical_dimension_severity", 0.0)), 4),
            "top_items": top_items,
        }

    recommendations = {"now": [], "next": [], "later": []}
    if catalog:
        for measure in sorted(catalog.measures, key=lambda m: (-float(m.priority_score), m.initiative_id)):
            priority = dict(measure.priority or {})
            score = float(measure.priority_score or priority.get("score", 0.0))
            if score <= 0:
                impact = float(priority.get("impact", measure.impact or 1))
                effort = max(1.0, float(priority.get("effort", measure.effort or 1)))
                criticality_weight = float(priority.get("criticality_weight", 1.0))
                gap_weight = float(priority.get("gap_weight", 1.0))
                score = (impact / effort) * criticality_weight * gap_weight

            template = template_for_dimension(measure.dimension) if measure.dimension else None
            deliverables = list(measure.deliverables or [])[:3]
            if not deliverables and template:
                deliverables = list(template.deliverables)

            kpi = dict(measure.kpi or {})
            if template:
                kpi.setdefault("name", template.kpi_name)
                kpi.setdefault("target", template.kpi_target_template)
                kpi.setdefault("measurement", template.kpi_measurement)

            bucket = str(priority.get("bucket", "later")).lower()
            if bucket not in recommendations:
                bucket = "later"
            recommendations[bucket].append(
                {
                    "id": measure.initiative_id or measure.measure_id,
                    "title": measure.title,
                    "dimension": measure.dimension,
                    "category": measure.category.value,
                    "priority_score": round(score, 2),
                    "diagnosis": measure.description,
                    "goal": measure.goal,
                    "deliverables": deliverables,
                    "dependencies": measure.dependencies,
                    "kpi": kpi,
                }
            )

    return {
        "export_version": "1.2.0",
        "timestamp": timestamp,
        "summary": {
            "bi": pipeline.get("bi", {}),
            "pa": pipeline.get("pa", {}),
            "synthesis": pipeline.get("synthesis", {}),
        },
        "evidence_overview": evidence_overview,
        "recommendations": recommendations,
        "answers": answers,
        "catalog_summary": catalog_summary if export_version == "1.2.0" else None,
    }


def _append_catalog_summary_markdown(lines: list[str], payload: dict[str, Any]) -> None:
    summary = payload.get("catalog_summary") or {}
    if not summary:
        return

    lines.append("\n## Ergebnis Maßnahmenkatalog (LLM)")
    lines.append(f"- Headline: {summary.get('headline', 'Ergebnis Maßnahmenkatalog')}")
    lines.append(summary.get("executive_summary", ""))

    for section_key, section_title in (("now", "Jetzt"), ("next", "Als Nächstes"), ("later", "Später")):
        lines.append(f"### {section_title}")
        for item in summary.get(section_key, []):
            lines.append(f"- {item}")

    lines.append("### Risiken & Abhängigkeiten")
    for item in summary.get("risks_and_dependencies", []):
        lines.append(f"- {item}")

    lines.append("### Erste 30 Tage")
    for item in summary.get("first_30_days", []):
        lines.append(f"- {item}")

    details = summary.get("measure_details", {})
    if isinstance(details, dict) and any(details.get(bucket) for bucket in ("now", "next", "later")):
        lines.append("### Maßnahmen-Details (Deliverables & KPI)")
        for bucket, title in (("now", "Jetzt"), ("next", "Als Nächstes"), ("later", "Später")):
            entries = details.get(bucket, [])
            if not entries:
                continue
            lines.append(f"- {title}:")
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                measure_title = str(entry.get("title") or "Maßnahme")
                deliverables = str(entry.get("deliverables_summary") or "")
                kpi_summary = str(entry.get("kpi_summary") or "")
                lines.append(f"  - {measure_title}: {(deliverables + ' ' + kpi_summary).strip()}")


def payload_to_markdown(payload: dict[str, Any]) -> str:
    if payload.get("export_version") == "1.0.0":
        pipeline = payload["pipeline"]
        answers = payload["answers"]
        catalog = payload.get("catalog")
        lines = [
            "# InsightHub Export",
            f"- Export Version: {payload['export_version']}",
            f"- Timestamp: {payload['timestamp']}",
            "",
            "## Assessments",
            f"- BI: {pipeline['bi']['summary']}",
            f"- PA: {pipeline['pa']['summary']}",
            "",
            "## Synthese",
            pipeline["synthesis"]["combined_summary"],
            "",
            "## Empfehlung",
            pipeline["synthesis"]["recommendation"],
            "",
            "## Antworten",
        ]
        for question_id, value in answers.items():
            lines.append(f"- {question_id}: {value}")

        if catalog is not None:
            lines.extend(["", "## Maßnahmenkatalog"])
            for measure in catalog["measures"]:
                lines.append(
                    f"- ({measure['suggested_priority']}) {measure['title']} | Kategorie: {measure['category']} | "
                    f"Impact {measure['impact']}/5 | Effort {measure['effort']}/5"
                )
        return "\n".join(lines)

    if payload.get("export_version") == "1.1.0":
        lines = [
            "# InsightHub Export",
            f"- Export Version: {payload['export_version']}",
            f"- Timestamp: {payload['timestamp']}",
            "",
            "## Evidenzüberblick",
        ]
        for domain, evidence in payload.get("evidence_overview", {}).items():
            lines.append(f"### {domain}")
            lines.append(f"- Kritischste Dimension: {evidence.get('critical_dimension', 'N/A')}")
            for item in evidence.get("top_items", []):
                lines.append(f"  - {item.get('item_id')}: answer={item.get('answer')} deficit={item.get('deficit_score')}")

        lines.append("\n## Maßnahmen")
        for bucket in ("now", "next", "later"):
            lines.append(f"### {bucket.upper()}")
            for measure in payload.get("recommendations", {}).get(bucket, []):
                priority = measure.get("priority", {})
                lines.append(
                    f"- {measure['id']} | {measure['title']} | Ziel: {measure.get('goal')} | "
                    f"PriorityScore={priority.get('score')} (I={priority.get('impact')}, E={priority.get('effort')}, "
                    f"CW={priority.get('criticality_weight')}, GW={priority.get('gap_weight')})"
                )
                lines.append(f"  - Dependencies: {', '.join(measure.get('dependencies', [])) or 'Keine'}")
                kpi = measure.get("kpi", {})
                lines.append(f"  - KPI: {kpi.get('name')} | Target: {kpi.get('target')} | Messung: {kpi.get('measurement')}")
                for trigger in measure.get("trigger_items", [])[:3]:
                    lines.append(f"  - Trigger: {trigger.get('item_id')} ({trigger.get('answer')}) deficit={trigger.get('deficit_score')}")
        return "\n".join(lines)

    lines = [
        "# InsightHub Export",
        f"- Export Version: {payload['export_version']}",
        f"- Timestamp: {payload['timestamp']}",
        "",
        "## Evidenzüberblick",
    ]
    for domain, evidence in payload.get("evidence_overview", {}).items():
        lines.append(f"### {domain}")
        lines.append(
            f"- Kritischste Dimension: {evidence.get('critical_dimension', 'N/A')} | Severity: {evidence.get('critical_dimension_severity', 0.0):.2f}"
        )
        triggers = [
            f"{item.get('item_id')}={item.get('answer')} ({float(item.get('deficit_score', 0.0)):.2f})"
            for item in evidence.get("top_items", [])[:3]
        ]
        lines.append(f"- Top-Trigger-Items: {', '.join(triggers) if triggers else 'keine'}")

    lines.append("\n## Maßnahmen")
    for bucket in ("now", "next", "later"):
        lines.append(f"### {bucket.upper()}")
        for measure in payload.get("recommendations", {}).get(bucket, []):
            lines.append(
                f"- {measure['id']} | {measure['title']} | {measure.get('dimension')} | {measure.get('category')} | PriorityScore={measure.get('priority_score'):.2f}"
            )
            lines.append(f"  - Diagnose: {measure.get('diagnosis')}")
            for deliverable in measure.get("deliverables", [])[:3]:
                lines.append(f"  - Deliverable: {deliverable}")
            lines.append(f"  - Dependencies: {', '.join(measure.get('dependencies', [])) or 'keine'}")
            kpi = measure.get("kpi", {})
            lines.append(f"  - KPI: {kpi.get('name')} | Ziel: {kpi.get('target')} | Messung: {kpi.get('measurement')}")

    _append_catalog_summary_markdown(lines, payload)
    return "\n".join(lines)


def payload_to_json(payload: dict[str, Any]) -> str:
    def _json_default(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)
