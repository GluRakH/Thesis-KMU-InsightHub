from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

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
                    "deliverables": (measure.deliverables or [])[:3],
                    "dependencies": measure.dependencies,
                    "kpi": measure.kpi,
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
    }


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
    return "\n".join(lines)


def payload_to_json(payload: dict[str, Any]) -> str:
    def _json_default(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)
