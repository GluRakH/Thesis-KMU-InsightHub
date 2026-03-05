from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.initiative_templates import FALLBACK_TEMPLATE, template_for_dimension
from domain.models import Measure, MeasureCatalog


class TriggerItem(BaseModel):
    item_id: str
    label: str
    answer_value: Any
    deficit_score: float
    dimension_id: str


class MeasureItem(BaseModel):
    initiative_id: str
    measure_id: str
    title: str
    dimension: str
    priority: int
    category: str
    deliverables: list[str] = Field(min_length=3, max_length=3)
    kpi: dict[str, Any]
    rationale: str
    trigger_items: list[TriggerItem]
    dependencies: list[str]


def _is_generic_title(title: str) -> bool:
    normalized = title.strip().lower()
    return not normalized or normalized in {"maßnahme", "initiative", "improvement measure"} or normalized.startswith("maßnahme ")


def _trigger_items_from_measure(measure: Measure) -> list[dict[str, Any]]:
    trigger_items = (measure.evidence or {}).get("trigger_items", []) if isinstance(measure.evidence, dict) else []
    normalized: list[dict[str, Any]] = []
    for item in trigger_items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("question_text") or item.get("label") or item.get("item_id") or "").strip()
        answer_value = item.get("answer_value", item.get("answer"))
        if answer_value is None:
            continue
        normalized.append(
            {
                "item_id": str(item.get("item_id") or item.get("question_id") or "unknown"),
                "label": label,
                "answer_value": answer_value,
                "deficit_score": float(item.get("deficit_score", 0.0)),
                "dimension_id": str(item.get("dimension_id") or measure.dimension),
            }
        )
    normalized.sort(key=lambda entry: entry["deficit_score"], reverse=True)
    return normalized[:3]


def _diagnosis(template_text: str, dimension: str, trigger_items: list[dict[str, Any]], fallback: str) -> str:
    trigger_summary = ", ".join(
        f"{item['item_id']}={item['answer_value']} (deficit {item['deficit_score']:.2f})" for item in trigger_items
    )
    trigger_summary = trigger_summary or "keine verwertbaren Trigger-Items"
    return template_text.format(dimension=dimension, trigger_summary=trigger_summary) if template_text else fallback


def _bucketed(catalog: MeasureCatalog, selected_ids: list[str] | None = None, final_priority: dict[str, int] | None = None) -> dict[str, list[Measure]]:
    selected = [m for m in catalog.measures if not selected_ids or m.measure_id in selected_ids]
    selected.sort(key=lambda m: final_priority.get(m.measure_id, m.suggested_priority) if final_priority else m.suggested_priority)
    for idx, measure in enumerate(sorted(selected, key=lambda m: (-m.priority_score, m.initiative_id)), start=1):
        measure.suggested_priority = idx
    ordered = sorted(selected, key=lambda m: m.suggested_priority)
    return {"now": ordered[:3], "next": ordered[3:6], "later": ordered[6:]}


def build_measures_by_bucket(
    catalog: MeasureCatalog,
    selected_ids: list[str] | None = None,
    final_priority: dict[str, int] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {"now": [], "next": [], "later": []}
    for bucket, measures in _bucketed(catalog, selected_ids, final_priority).items():
        for measure in measures:
            template = template_for_dimension(measure.dimension) if measure.dimension != "GLOBAL" else FALLBACK_TEMPLATE
            trigger_items = _trigger_items_from_measure(measure)
            kpi = dict(measure.kpi or {})
            if not kpi:
                kpi = {
                    "name": template.kpi_name,
                    "target": template.kpi_target_template,
                    "measurement": template.kpi_measurement,
                    "frequency": template.kpi_frequency,
                    "source_system": template.kpi_source_system,
                    "owner_role": template.kpi_owner_role,
                }
            for key in ("name", "target", "measurement", "frequency", "source_system", "owner_role"):
                if not str(kpi.get(key, "")).strip():
                    kpi[key] = getattr(template, f"kpi_{key}", "")

            deliverables = list(measure.deliverables or list(template.deliverables))[:3]
            if len(deliverables) < 3:
                deliverables = list(template.deliverables)

            title = template.title if _is_generic_title(measure.title) else measure.title
            rationale = _diagnosis(template.diagnosis_template, measure.dimension, trigger_items, measure.description)

            measure_item = MeasureItem(
                initiative_id=measure.initiative_id or measure.measure_id,
                measure_id=measure.measure_id,
                title=title,
                dimension=measure.dimension,
                priority=final_priority.get(measure.measure_id, measure.suggested_priority) if final_priority else measure.suggested_priority,
                category=measure.category.value if hasattr(measure.category, "value") else str(measure.category),
                deliverables=deliverables,
                kpi=kpi,
                rationale=rationale,
                trigger_items=trigger_items,
                dependencies=list(measure.dependencies or []),
            )
            result[bucket].append(measure_item.model_dump())
    return result
