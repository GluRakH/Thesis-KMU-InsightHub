from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from domain.models import MeasureCategory


@dataclass(frozen=True)
class InitiativeDefaults:
    scale_min: float
    scale_max: float
    deliverables_exactly: int
    impact_range: tuple[int, int]
    effort_range: tuple[int, int]


@dataclass(frozen=True)
class InitiativeTemplate:
    template_id: str
    title: str
    category: MeasureCategory
    goal: str
    deliverables: tuple[str, str, str]
    kpi: dict[str, str]
    impact: int
    effort: int
    evidence_rules: dict[str, object]
    sequencing: dict[str, list[str]]


@dataclass(frozen=True)
class DimensionTemplateBundle:
    dimension_id: str
    dimension_name: str
    good_definition: str
    minimal_standards: tuple[str, ...]
    target_maturity: str
    target_description: str
    template: InitiativeTemplate


@dataclass(frozen=True)
class InitiativeSchema:
    schema_version: str
    defaults: InitiativeDefaults
    dimensions: dict[str, DimensionTemplateBundle]


def load_initiative_schema(config_path: Path | None = None) -> InitiativeSchema:
    path = config_path or Path("app/config/initiative_schema_v1.0.json")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    defaults = payload.get("defaults", {})
    export_defaults = defaults.get("export", {})
    priority_defaults = defaults.get("priority", {})
    schema_defaults = InitiativeDefaults(
        scale_min=float(defaults.get("scale", {}).get("min", 1)),
        scale_max=float(defaults.get("scale", {}).get("max", 5)),
        deliverables_exactly=int(export_defaults.get("deliverables_exactly", 3)),
        impact_range=tuple(priority_defaults.get("impact_range", [1, 5])),
        effort_range=tuple(priority_defaults.get("effort_range", [1, 5])),
    )

    dimensions: dict[str, DimensionTemplateBundle] = {}
    for dimension_id, config in payload.get("dimensions", {}).items():
        template_payload = config.get("primary_template", {})
        deliverables = tuple(template_payload.get("deliverables", [])[: schema_defaults.deliverables_exactly])
        if len(deliverables) != schema_defaults.deliverables_exactly:
            raise ValueError(f"Template {dimension_id} muss genau {schema_defaults.deliverables_exactly} Deliverables haben.")

        impact = int(template_payload.get("estimates", {}).get("impact", 1))
        effort = int(template_payload.get("estimates", {}).get("effort", 1))
        impact = max(schema_defaults.impact_range[0], min(schema_defaults.impact_range[1], impact))
        effort = max(schema_defaults.effort_range[0], min(schema_defaults.effort_range[1], effort))

        template = InitiativeTemplate(
            template_id=str(template_payload.get("template_id", f"TPL_{dimension_id}")),
            title=str(template_payload.get("title", f"Initiative {dimension_id}")),
            category=MeasureCategory(str(template_payload.get("category", "organizational"))),
            goal=str(template_payload.get("goal", "")),
            deliverables=deliverables,
            kpi={k: str(v) for k, v in (template_payload.get("kpi", {}) or {}).items()},
            impact=impact,
            effort=effort,
            evidence_rules=dict(template_payload.get("evidence_rules", {}) or {}),
            sequencing=dict(template_payload.get("sequencing", {}) or {}),
        )

        dimensions[dimension_id] = DimensionTemplateBundle(
            dimension_id=dimension_id,
            dimension_name=str(config.get("dimension_name", dimension_id)),
            good_definition=str(config.get("good_definition", "")),
            minimal_standards=tuple(str(item) for item in config.get("minimal_standards", [])),
            target_maturity=str(config.get("target_state", {}).get("maturity_target", "L3")),
            target_description=str(config.get("target_state", {}).get("description", "")),
            template=template,
        )

    return InitiativeSchema(
        schema_version=str(payload.get("schema_version", "1.0")),
        defaults=schema_defaults,
        dimensions=dimensions,
    )
