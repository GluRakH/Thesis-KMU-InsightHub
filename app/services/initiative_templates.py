from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json

from jsonschema import Draft202012Validator

from domain.models import MeasureCategory


@dataclass(frozen=True)
class InitiativeTemplate:
    template_id: str
    template_version: str
    title: str
    category: MeasureCategory
    goal: str
    diagnosis_template: str
    deliverables: tuple[str, str, str]
    kpi_name: str
    kpi_target_template: str
    kpi_measurement: str
    kpi_frequency: str
    kpi_source_system: str
    kpi_owner_role: str
    impact: int
    effort: int


FALLBACK_TEMPLATE = InitiativeTemplate(
    template_id="TPL_FALLBACK_BASE",
    template_version="default",
    title="Umsetzungsfahrplan mit messbaren Zwischenzielen",
    category=MeasureCategory.ORGANIZATIONAL,
    goal="Die priorisierte Dimension wird innerhalb eines Quartals in einen stabilen Umsetzungsmodus überführt.",
    diagnosis_template="In {dimension} zeigen {trigger_summary} den größten Handlungsdruck und bremsen die Reifeentwicklung.",
    deliverables=(
        "Ist-Analyse mit Ursachenliste und Scope pro Teilprozess",
        "90-Tage-Plan mit Ownern, Milestones und Review-Rhythmus",
        "Pilotumsetzung inkl. Lessons-Learned und Rollout-Entscheid",
    ),
    kpi_name="Meilensteinerreichung priorisierte Dimension",
    kpi_target_template=">= 80% der 90-Tage-Meilensteine termingerecht erreicht",
    kpi_measurement="Monatliches PMO-Tracking auf Maßnahmenebene",
    kpi_frequency="monthly",
    kpi_source_system="PMO-Board",
    kpi_owner_role="Programmleitung",
    impact=3,
    effort=2,
)


DIMENSION_TEMPLATE_MAP: dict[str, list[str]] = {
    "BI_D1": ["BI_GOV_FOUNDATION"],
    "BI_D2": ["BI_DQ_RULES"],
    "BI_D3": ["BI_SEMANTIC_LAYER", "ENABLEMENT"],
    "PA_D1": ["PA_GOV_FOUNDATION"],
    "PA_D2": ["PA_PIPELINE_STANDARD"],
    "PA_D3": ["PA_OPERATIONS", "ENABLEMENT"],
}


class TemplateValidationError(ValueError):
    pass


def _templates_schema_validator() -> Draft202012Validator:
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "templates.schema.json"
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(payload)


def _canonicalize_templates(payload: dict[str, Any]) -> dict[str, Any]:
    if "templates" in payload:
        return payload

    reverse_map: dict[str, list[str]] = {}
    for dim, template_ids in DIMENSION_TEMPLATE_MAP.items():
        for template_id in template_ids:
            reverse_map.setdefault(template_id, []).append(dim)

    templates: list[dict[str, Any]] = []
    items = payload.get("items", {})
    for template_id, item in items.items():
        kpi = item.get("kpi", {})
        frequency_map = {"wöchentlich": "weekly", "monatlich": "monthly", "quartalsweise": "quarterly"}
        frequency_raw = str(kpi.get("frequency", "monthly")).strip().lower()
        templates.append(
            {
                "template_id": template_id,
                "title": item.get("title"),
                "category": item.get("category"),
                "applies_to": {"dimensions": reverse_map.get(template_id, ["BI_D1"])},
                "goal": item.get("goal"),
                "deliverables": item.get("deliverables"),
                "kpi": {
                    "name": kpi.get("name"),
                    "baseline_definition": kpi.get("baseline_definition") or f"Baseline für {kpi.get('name', template_id)}",
                    "target": kpi.get("target") or kpi.get("target_template"),
                    "measurement": kpi.get("measurement"),
                    "frequency": frequency_map.get(frequency_raw, frequency_raw),
                    "source_system": kpi.get("source_system"),
                    "owner_role": kpi.get("owner_role"),
                },
                "impact": item.get("impact"),
                "effort": item.get("effort"),
            }
        )

    return {
        "schema_version": str(payload.get("schema_version", "1.0.0")),
        "template_version": str(payload.get("template_version", "1.0.0")) + (".0" if str(payload.get("template_version", "1.0.0")).count(".")==1 else ""),
        "templates": templates,
    }


def _validate_template(template_id: str, payload: dict[str, Any], template_version: str) -> InitiativeTemplate:
    deliverables = payload.get("deliverables")
    if not isinstance(deliverables, list) or len(deliverables) != 3:
        raise TemplateValidationError(f"Template '{template_id}' muss exakt 3 Deliverables enthalten")

    kpi = payload.get("kpi")
    if not isinstance(kpi, dict):
        raise TemplateValidationError(f"Template '{template_id}' enthält kein KPI-Objekt")
    for field in ("name", "baseline_definition", "target", "measurement", "frequency"):
        if field not in kpi or (isinstance(kpi.get(field), str) and not kpi.get(field).strip()):
            raise TemplateValidationError(f"Template '{template_id}' KPI-Feld '{field}' fehlt")

    return InitiativeTemplate(
        template_id=template_id,
        template_version=template_version,
        title=str(payload["title"]),
        category=MeasureCategory(str(payload["category"])),
        goal=str(payload["goal"]),
        diagnosis_template=str(payload.get("diagnosis_template", "In {dimension} zeigen {trigger_summary} Handlungsbedarf.")),
        deliverables=tuple(str(item) for item in deliverables),
        kpi_name=str(kpi["name"]),
        kpi_target_template=str(kpi["target"]),
        kpi_measurement=str(kpi["measurement"]),
        kpi_frequency=str(kpi["frequency"]),
        kpi_source_system=str(kpi.get("source_system") or "N/A"),
        kpi_owner_role=str(kpi.get("owner_role") or "N/A"),
        impact=int(payload["impact"]),
        effort=int(payload["effort"]),
    )


def load_templates(config_path: Path | None = None, dev_mode: bool = False) -> tuple[dict[str, InitiativeTemplate], str]:
    path = config_path or Path("app/config/templates.yaml")
    if not path.exists():
        return {}, "default"

    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text) if raw_text.strip() else {}
    canonical = _canonicalize_templates(data)

    errors = sorted(_templates_schema_validator().iter_errors(canonical), key=lambda e: e.path)
    if errors:
        if dev_mode:
            raise TemplateValidationError(f"templates schema validation failed: {errors[0].message}")
        return {}, "default"

    version = str(canonical.get("template_version", "default"))
    registry: dict[str, InitiativeTemplate] = {}
    for payload in canonical.get("templates", []):
        template_id = str(payload.get("template_id"))
        registry[template_id] = _validate_template(template_id, payload, version)

    return registry, version


TEMPLATE_REGISTRY, TEMPLATE_VERSION = load_templates()


def template_for_dimension(dimension_id: str) -> InitiativeTemplate:
    template_ids = DIMENSION_TEMPLATE_MAP.get(dimension_id, [])
    if template_ids:
        template = TEMPLATE_REGISTRY.get(template_ids[0])
        if template:
            return template
    return FALLBACK_TEMPLATE
