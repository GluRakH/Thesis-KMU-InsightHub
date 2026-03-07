from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.services.dimension_labels import enrich_dimension_payload, format_dimension
from domain.models import MeasureCatalog


def _initiative_payload(measure: Any) -> dict[str, Any]:
    kpi = dict(measure.kpi or {})
    evidence = dict(measure.evidence or {})
    triggers = list(evidence.get("trigger_items", []))[:3]
    return {
        "id": measure.initiative_id or measure.measure_id,
        "title": measure.title,
        "dimension": measure.dimension,
        "dimension_meta": enrich_dimension_payload(measure.dimension),
        "category": measure.category.value,
        "bucket": str((measure.priority or {}).get("bucket", "later")),
        "priority_score": float(measure.priority_score),
        "rank": int(measure.suggested_priority),
        "sequence_reason": str((measure.priority or {}).get("sequence_reason", "")),
        "diagnosis": measure.description,
        "goal": measure.goal,
        "deliverables": list(measure.deliverables)[:3],
        "dependencies": list(measure.dependencies),
        "template_id": measure.measure_class,
        "template_version": measure.prompt_version,
        "kpi": {
            "name": str(kpi.get("name", "")),
            "target": str(kpi.get("target", "")),
            "measurement": str(kpi.get("measurement", "")),
            "frequency": str(kpi.get("frequency", "")),
            "source_system": str(kpi.get("source_system", "")),
            "owner_role": str(kpi.get("owner_role", "")),
        },
        "evidence": {
            "dimension_id": evidence.get("dimension_id", measure.dimension),
            "dimension_label": format_dimension(str(evidence.get("dimension_id", measure.dimension) or "")),
            "severity": float(evidence.get("severity", 0.0)),
            "trigger_items": triggers,
            "rationale": str(evidence.get("rationale", "")),
        },
    }


def build_export_payload(
    pipeline: dict[str, Any],
    answers: dict[str, Any],
    catalog: MeasureCatalog | None,
    export_version: str = "2.0.0",
    catalog_summary: dict[str, Any] | None = None,
    rules_applied: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    initiatives = [_initiative_payload(measure) for measure in (catalog.measures if catalog else [])]
    grouped = {"now": [], "next": [], "later": []}
    for initiative in initiatives:
        grouped[initiative["bucket"] if initiative["bucket"] in grouped else "later"].append(initiative)

    thresholds = (rules_applied or {}).get("thresholds", {"governance": 0.6, "data_quality": 0.55})
    template_version = catalog.prompt_version if catalog else "templates-default"

    payload = {
        "export_version": export_version,
        "timestamp": timestamp,
        "assessment": {
            "bi": pipeline.get("bi", {}),
            "pa": pipeline.get("pa", {}),
            "synthesis": pipeline.get("synthesis", {}),
            "dimension_labels": {
                "bi": {format_dimension(key): value for key, value in dict(pipeline.get("bi", {}).get("dimension_scores", {})).items()},
                "pa": {format_dimension(key): value for key, value in dict(pipeline.get("pa", {}).get("dimension_scores", {})).items()},
            },
            "scores": {
                "bi_score": float(pipeline.get("bi", {}).get("score", 0.0)),
                "pa_score": float(pipeline.get("pa", {}).get("score", 0.0)),
            },
        },
        "initiatives": grouped,
        "rules_applied": {
            "gates": (rules_applied or {}).get("gates", []),
            "thresholds": thresholds,
            "dependencies": (rules_applied or {}).get("dependencies", []),
        },
        "generation_metadata": {
            "template_version": template_version,
            "llm_model": "none",
            "prompt_version": catalog.prompt_version if catalog else "n/a",
            "temperature": 0.0,
            "mode": "deterministic",
        },
        "catalog_summary": catalog_summary or {},
        "answers": answers,
    }
    payload["run_id"] = persist_run(payload, answerset_id=str(pipeline.get("synthesis", {}).get("answer_set_id", "unknown")))
    return payload


def persist_run(payload: dict[str, Any], answerset_id: str) -> str:
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    run_dir = Path("runs")
    run_dir.mkdir(parents=True, exist_ok=True)
    config_hash = hashlib.sha256(
        json.dumps(
            {
                "template_version": payload.get("generation_metadata", {}).get("template_version"),
                "thresholds": payload.get("rules_applied", {}).get("thresholds", {}),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    record = {
        "run_id": run_id,
        "answer_set_id": answerset_id,
        "timestamp": payload.get("timestamp"),
        "configuration_hash": config_hash,
        "result": payload,
    }
    (run_dir / f"{run_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_id


def payload_to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# InsightHub Export",
        f"- Export Version: {payload['export_version']}",
        f"- Run-ID: {payload.get('run_id', 'n/a')}",
        f"- Timestamp: {payload['timestamp']}",
        "",
        "## Assessment",
        f"- BI-Score: {payload['assessment']['scores']['bi_score']:.2f} ({payload['assessment']['bi'].get('level_label', 'N/A')})",
        f"- PA-Score: {payload['assessment']['scores']['pa_score']:.2f} ({payload['assessment']['pa'].get('level_label', 'N/A')})",
        "",
        "## Maßnahmenkatalog (deterministisch)",
    ]
    for bucket, label in (("now", "Jetzt"), ("next", "Als Nächstes"), ("later", "Später")):
        lines.append(f"### {label}")
        measures = payload.get("initiatives", {}).get(bucket, [])
        if not measures:
            lines.append("- Keine Maßnahmen in diesem Bucket.")
            continue
        for measure in measures:
            lines.append(f"- {measure['id']} | {measure['title']} | PriorityScore={measure['priority_score']:.2f} | Rang={measure['rank']}")
            lines.append(f"  - Sequenz: {measure.get('sequence_reason', '')}")
            lines.append(f"  - Lieferobjekte: {', '.join(measure.get('deliverables', []))}")
            lines.append(f"  - KPI: {measure['kpi'].get('name')} | Ziel: {measure['kpi'].get('target')} | Messung: {measure['kpi'].get('measurement')}")
            evidence = measure.get("evidence", {})
            lines.append(f"  - Evidenz: Dimension {evidence.get('dimension_label') or format_dimension(str(evidence.get('dimension_id') or ''))} | Severity {float(evidence.get('severity', 0.0)):.2f}")
            for trigger in evidence.get("trigger_items", []):
                lines.append(f"    - Evidenz-Trigger: {trigger.get('item_id')} ({trigger.get('answer')}) deficit={trigger.get('deficit_score')}")

    lines.append("\n## Risiken & Abhängigkeiten")
    gates = payload.get("rules_applied", {}).get("gates", [])
    if gates:
        for gate in gates:
            lines.append(
                f"- {gate.get('rule')} aktiv: Blocker {gate.get('blocking_measure')} -> {', '.join(gate.get('affected_measures', [])) or 'keine'}"
            )
    else:
        lines.append("- Keine aktivierten Gates.")
    return "\n".join(lines)


def payload_to_json(payload: dict[str, Any]) -> str:
    def _json_default(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)
