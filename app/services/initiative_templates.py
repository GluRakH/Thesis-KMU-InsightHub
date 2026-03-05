from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json

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
    kpi_frequency="monatlich",
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


def _validate_template(template_id: str, payload: dict[str, Any], template_version: str) -> InitiativeTemplate:
    required = ["title", "category", "goal", "diagnosis_template", "deliverables", "kpi", "impact", "effort"]
    missing = [field for field in required if field not in payload]
    if missing:
        raise TemplateValidationError(f"Template '{template_id}' fehlt Pflichtfelder: {', '.join(missing)}")

    deliverables = payload.get("deliverables")
    if not isinstance(deliverables, list) or len(deliverables) != 3 or any(not str(item).strip() for item in deliverables):
        raise TemplateValidationError(f"Template '{template_id}' muss exakt 3 Deliverables enthalten")

    kpi = payload.get("kpi")
    if not isinstance(kpi, dict):
        raise TemplateValidationError(f"Template '{template_id}' enthält kein KPI-Objekt")
    for field in ("name", "target_template", "measurement"):
        if not str(kpi.get(field, "")).strip():
            raise TemplateValidationError(f"Template '{template_id}' KPI-Feld '{field}' fehlt")

    return InitiativeTemplate(
        template_id=template_id,
        template_version=template_version,
        title=str(payload["title"]),
        category=MeasureCategory(str(payload["category"])),
        goal=str(payload["goal"]),
        diagnosis_template=str(payload["diagnosis_template"]),
        deliverables=tuple(str(item) for item in deliverables),
        kpi_name=str(kpi["name"]),
        kpi_target_template=str(kpi["target_template"]),
        kpi_measurement=str(kpi["measurement"]),
        kpi_frequency=str(kpi.get("frequency", "monatlich")),
        kpi_source_system=str(kpi.get("source_system", "N/A")),
        kpi_owner_role=str(kpi.get("owner_role", "N/A")),
        impact=int(payload["impact"]),
        effort=int(payload["effort"]),
    )


def load_templates(config_path: Path | None = None, dev_mode: bool = False) -> tuple[dict[str, InitiativeTemplate], str]:
    path = config_path or Path("app/config/templates.yaml")
    if not path.exists():
        return {}, "default"

    data = json.loads(path.read_text(encoding="utf-8")) if path.read_text(encoding="utf-8").strip() else {}

    version = str(data.get("template_version", "default"))
    items = data.get("items", {})
    if not isinstance(items, dict):
        raise TemplateValidationError("templates.yaml: 'items' muss ein Objekt sein")

    registry: dict[str, InitiativeTemplate] = {}
    try:
        for template_id, payload in items.items():
            if not isinstance(payload, dict):
                raise TemplateValidationError(f"Template '{template_id}' muss ein Objekt sein")
            registry[str(template_id)] = _validate_template(str(template_id), payload, version)
    except TemplateValidationError:
        if dev_mode:
            raise
        return {}, "default"

    return registry, version


TEMPLATE_REGISTRY, TEMPLATE_VERSION = load_templates()


def template_for_dimension(dimension_id: str) -> InitiativeTemplate:
    template_ids = DIMENSION_TEMPLATE_MAP.get(dimension_id, [])
    if template_ids:
        template = TEMPLATE_REGISTRY.get(template_ids[0])
        if template:
            return template
    return FALLBACK_TEMPLATE
