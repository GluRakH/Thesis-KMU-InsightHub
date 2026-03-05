from __future__ import annotations

from typing import Any
import logging
import re

from adapters.llm_client import LLMClient

logger = logging.getLogger(__name__)

INVALID_TEXT_PATTERN = re.compile(r"\b(invalid|n/?a|nicht\s+definiert)\b", re.IGNORECASE)


def _is_useful_text(s: str) -> bool:
    text = str(s or "").strip()
    if not text:
        return False
    return INVALID_TEXT_PATTERN.search(text) is None


def _format_trigger_ref(trigger: dict[str, Any]) -> str:
    item_id = trigger.get("item_id") or "?"
    label = trigger.get("label", item_id)
    answer = trigger.get("answer_value", trigger.get("answer", "?"))
    try:
        deficit = float(trigger.get("deficit_score", 0.0))
    except (TypeError, ValueError):
        deficit = 0.0
    return f"{item_id}: {label} | answer={answer} | deficit={deficit:.2f}"


def build_catalog_summary(
    focus: str,
    measures_by_bucket: dict[str, list[dict[str, Any]]],
    llm_client: LLMClient | None = None,
    use_llm_texts: bool = False,
    dev_mode: bool = False,
) -> dict[str, Any]:
    deterministic_summary = _build_deterministic_summary(focus=focus, measures_by_bucket=measures_by_bucket, dev_mode=dev_mode)

    if not use_llm_texts or llm_client is None:
        return deterministic_summary

    llm_payload = _build_llm_payload(measures_by_bucket, dev_mode=dev_mode)
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
        "measure_details": _merge_measure_details(
            deterministic_details=deterministic_summary["measure_details"],
            llm_details=llm_summary.get("measure_details"),
        ),
        "generation_mode": "deterministic+llm_text",
        "info": "Ableitung regelbasiert; Zusammenfassung und Detailtexte durch LLM unterstützt.",
    }


def _merge_measure_details(
    deterministic_details: dict[str, list[dict[str, Any]]],
    llm_details: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(llm_details, dict):
        return deterministic_details

    merged: dict[str, list[dict[str, Any]]] = {"now": [], "next": [], "later": []}
    for bucket in ("now", "next", "later"):
        fallback_items = deterministic_details.get(bucket, [])
        fallback_by_title = {
            str(item.get("title") or "").strip().lower(): item
            for item in fallback_items
            if str(item.get("title") or "").strip()
        }
        used_titles: set[str] = set()
        used_fallback_indices: set[int] = set()
        llm_bucket = llm_details.get(bucket, []) if isinstance(llm_details.get(bucket), list) else []

        for idx, llm_item in enumerate(llm_bucket):
            if not isinstance(llm_item, dict):
                continue

            title_key = str(llm_item.get("title") or "").strip().lower()
            fallback = fallback_by_title.get(title_key)
            fallback_index = -1
            if fallback is None and idx < len(fallback_items):
                fallback = fallback_items[idx]
                fallback_index = idx
            elif fallback is not None:
                fallback_index = fallback_items.index(fallback)

            if fallback is None:
                fallback = {"title": llm_item.get("title")}

            if title_key:
                used_titles.add(title_key)
            if fallback_index >= 0:
                used_fallback_indices.add(fallback_index)

            llm_kpi_summary = str(llm_item.get("kpi_summary") or "")
            llm_evidence_summary = str(llm_item.get("evidence_summary") or "")
            merged[bucket].append(
                {
                    "title": llm_item.get("title") or fallback.get("title") or "",
                    "deliverables": llm_item.get("deliverables") or fallback.get("deliverables") or [],
                    "kpi_summary": llm_kpi_summary if _is_useful_text(llm_kpi_summary) else fallback.get("kpi_summary") or "",
                    "evidence_summary": llm_evidence_summary if _is_useful_text(llm_evidence_summary) else fallback.get("evidence_summary") or "",
                    "trigger_refs": llm_item.get("trigger_refs") or fallback.get("trigger_refs") or [],
                }
            )

        for fallback_idx, fallback in enumerate(fallback_items):
            title_key = str(fallback.get("title") or "").strip().lower()
            if fallback_idx in used_fallback_indices:
                continue
            if title_key and title_key in used_titles:
                continue
            merged[bucket].append(fallback)

    return merged


def _validated_item(item: dict[str, Any], dev_mode: bool = False) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    kpi = item.get("kpi") if isinstance(item.get("kpi"), dict) else {}
    deliverables = item.get("deliverables") if isinstance(item.get("deliverables"), list) else []
    trigger_items = item.get("trigger_items") if isinstance(item.get("trigger_items"), list) else []
    if len(deliverables) != 3:
        errors.append("deliverables muss exakt 3 Einträge enthalten")
    for field in ("name", "target", "measurement", "frequency"):
        if not str(kpi.get(field) or "").strip():
            errors.append(f"kpi.{field} fehlt")
    if not trigger_items:
        errors.append("mindestens ein trigger_item erforderlich")

    if errors:
        logger.error("Invalid measure item %s: %s", item.get('initiative_id') or item.get('title'), '; '.join(errors))
    if errors and dev_mode:
        raise ValueError(f"INVALID measure item {item.get('initiative_id') or item.get('title')}: {'; '.join(errors)}")

    normalized = dict(item)
    normalized["_validation_errors"] = errors
    return normalized, errors


def _build_deterministic_summary(focus: str, measures_by_bucket: dict[str, list[dict[str, Any]]], dev_mode: bool = False) -> dict[str, Any]:
    def _bullet(item: dict[str, Any]) -> str:
        return f"{item.get('initiative_id')}: {item.get('title')} ({item.get('dimension')}, Rang {item.get('priority')})"

    details: dict[str, list[dict[str, Any]]] = {"now": [], "next": [], "later": []}
    for bucket in ("now", "next", "later"):
        for raw_item in measures_by_bucket.get(bucket, []):
            item, errors = _validated_item(raw_item, dev_mode=dev_mode)
            triggers = item.get("trigger_items", [])[:3]
            trigger_refs = [_format_trigger_ref(trigger) for trigger in triggers]
            trigger_ids = ", ".join(str(trigger.get("item_id") or "?") for trigger in triggers) or "keine"
            dimension = str(item.get("dimension") or "unbekannt")
            deterministic_evidence = f"Dimension {dimension}; Top-Trigger: {trigger_ids}."
            if errors:
                details[bucket].append(
                    {
                        "title": f"INVALID: {item.get('title')}",
                        "deliverables": item.get("deliverables", []),
                        "kpi_summary": f"INVALID ITEM – {'; '.join(errors)}",
                        "evidence_summary": deterministic_evidence,
                        "trigger_refs": trigger_refs,
                    }
                )
                continue

            kpi = item.get("kpi") or {}
            details[bucket].append(
                {
                    "title": item.get("title"),
                    "deliverables": item.get("deliverables", [])[:3],
                    "kpi_summary": f"{kpi.get('name')} | Ziel {kpi.get('target')} | Messung {kpi.get('measurement')}",
                    "evidence_summary": deterministic_evidence,
                    "trigger_refs": trigger_refs,
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


def _build_llm_payload(measures_by_bucket: dict[str, list[dict[str, Any]]], dev_mode: bool = False) -> dict[str, list[dict[str, Any]]]:
    payload: dict[str, list[dict[str, Any]]] = {"now": [], "next": [], "later": []}
    for bucket in ("now", "next", "later"):
        for raw_item in measures_by_bucket.get(bucket, []):
            item, errors = _validated_item(raw_item, dev_mode=dev_mode)
            kpi = item.get("kpi") if isinstance(item.get("kpi"), dict) else {}
            trigger_items = item.get("trigger_items") if isinstance(item.get("trigger_items"), list) else []
            kpi_summary = (
                f"INVALID ITEM – {'; '.join(errors)}"
                if errors
                else f"{kpi.get('name')} | Ziel {kpi.get('target')} | Messung {kpi.get('measurement')}"
            )
            trigger_refs = [_format_trigger_ref(trigger) for trigger in trigger_items[:3]]
            trigger_ids = ", ".join(str(trigger.get("item_id") or "?") for trigger in trigger_items[:3]) or "keine"
            payload[bucket].append(
                {
                    "initiative_id": item.get("initiative_id"),
                    "title": item.get("title"),
                    "dimension": item.get("dimension"),
                    "priority": item.get("priority"),
                    "dependencies": item.get("dependencies", []),
                    "deliverables": item.get("deliverables", [])[:3],
                    "kpi_summary": kpi_summary,
                    "evidence_summary": f"Dimension {item.get('dimension') or 'unbekannt'}; Top-Trigger: {trigger_ids}.",
                    "trigger_refs": trigger_refs,
                }
            )
    return payload
