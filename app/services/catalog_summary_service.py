from __future__ import annotations

from typing import Any

from adapters.llm_client import LLMClient


def build_catalog_summary(
    focus: str,
    measures_by_bucket: dict[str, list[dict[str, Any]]],
    llm_client: LLMClient | None = None,
    use_llm_texts: bool = False,
) -> dict[str, Any]:
    deterministic_summary = _build_deterministic_summary(focus=focus, measures_by_bucket=measures_by_bucket)

    if not use_llm_texts or llm_client is None:
        return deterministic_summary

    llm_payload = _build_llm_payload(measures_by_bucket)
    llm_summary = llm_client.summarize_measure_catalog(
        focus=focus,
        measures_by_bucket=llm_payload,
    )

    return {
        **deterministic_summary,
        "headline": llm_summary.get("headline") or deterministic_summary["headline"],
        "executive_summary": llm_summary.get("executive_summary") or deterministic_summary["executive_summary"],
        "now": llm_summary.get("now") or deterministic_summary["now"],
        "next": llm_summary.get("next") or deterministic_summary["next"],
        "later": llm_summary.get("later") or deterministic_summary["later"],
        "risks_and_dependencies": llm_summary.get("risks_and_dependencies") or deterministic_summary["risks_and_dependencies"],
        "first_30_days": llm_summary.get("first_30_days") or deterministic_summary["first_30_days"],
        "measure_details": llm_summary.get("measure_details") or deterministic_summary["measure_details"],
        "generation_mode": "deterministic+llm_text",
        "info": "Ableitung regelbasiert; Zusammenfassung und Detailtexte durch LLM unterstützt.",
    }


def _build_deterministic_summary(focus: str, measures_by_bucket: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
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


def _build_llm_payload(measures_by_bucket: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    payload: dict[str, list[dict[str, Any]]] = {"now": [], "next": [], "later": []}
    for bucket in ("now", "next", "later"):
        for item in measures_by_bucket.get(bucket, []):
            kpi = item.get("kpi") if isinstance(item.get("kpi"), dict) else {}
            trigger_items = item.get("trigger_items") if isinstance(item.get("trigger_items"), list) else []
            payload[bucket].append(
                {
                    "initiative_id": item.get("initiative_id"),
                    "title": item.get("title"),
                    "dimension": item.get("dimension"),
                    "priority": item.get("priority"),
                    "dependencies": item.get("dependencies", []),
                    "deliverables": item.get("deliverables", [])[:3],
                    "kpi_summary": (
                        f"{kpi.get('name') or 'KPI nicht definiert'} | "
                        f"Ziel {kpi.get('target') or 'n/a'} | "
                        f"Messung {kpi.get('measurement') or 'n/a'}"
                    ),
                    "evidence_summary": item.get("rationale", ""),
                    "trigger_refs": [f"{trigger.get('item_id')}: {trigger.get('label', trigger.get('item_id'))}" for trigger in trigger_items[:3]],
                }
            )
    return payload
