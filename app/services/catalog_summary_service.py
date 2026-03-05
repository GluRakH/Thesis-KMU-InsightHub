from __future__ import annotations

from typing import Any


def build_catalog_summary(focus: str, measures_by_bucket: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    def _bullet(item: dict[str, Any]) -> str:
        return f"{item.get('initiative_id')}: {item.get('title')} ({item.get('dimension')}, Rang {item.get('priority')})"

    details: dict[str, list[dict[str, Any]]] = {"now": [], "next": [], "later": []}
    for bucket in ("now", "next", "later"):
        for item in measures_by_bucket.get(bucket, []):
            triggers = item.get("trigger_items", [])[:3]
            details[bucket].append(
                {
                    "title": item.get("title"),
                    "deliverables": item.get("deliverables", [])[:3],
                    "kpi_summary": (
                        f"{(item.get('kpi') or {}).get('name') or 'KPI nicht definiert'} | "
                        f"Ziel {(item.get('kpi') or {}).get('target') or 'n/a'} | "
                        f"Messung {(item.get('kpi') or {}).get('measurement') or 'n/a'}"
                    ),
                    "evidence_summary": item.get("rationale", ""),
                    "trigger_refs": [f"{trigger.get('item_id')}: {trigger.get('label', trigger.get('item_id'))}" for trigger in triggers],
                }
            )

    activated = []
    for bucket_items in measures_by_bucket.values():
        for item in bucket_items:
            if item.get("dependencies"):
                activated.append(f"{item.get('initiative_id')} hängt ab von {', '.join(item.get('dependencies', []))}")

    return {
        "headline": "Ergebnis Maßnahmenkatalog (deterministisch)",
        "executive_summary": f"Fokus: {focus or 'aus Scores abgeleitet'}. Maßnahmen und Reihenfolge werden regelbasiert aus Scores, Severity und Triggern erzeugt.",
        "now": [_bullet(item) for item in measures_by_bucket.get("now", [])],
        "next": [_bullet(item) for item in measures_by_bucket.get("next", [])],
        "later": [_bullet(item) for item in measures_by_bucket.get("later", [])],
        "risks_and_dependencies": activated or ["Keine aktiven Gates für den aktuellen Lauf."],
        "first_30_days": ["Top-Now-Maßnahmen mit Ownern planen", "KPI-Messung initial einrichten"],
        "measure_details": details,
        "generation_mode": "deterministic",
        "info": "Ableitung regelbasiert; textuelle Formulierungen optional generierbar.",
    }
