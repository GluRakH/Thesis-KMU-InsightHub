from __future__ import annotations

from typing import TypedDict


class DimensionMeta(TypedDict):
    label: str
    description: str


DIMENSION_LABELS: dict[str, DimensionMeta] = {
    "BI_D1": {"label": "BI-Governance", "description": "Rollen, Verantwortlichkeiten, Richtlinien"},
    "BI_D2": {"label": "Datenqualität & Engineering", "description": "DQ-Regeln, Pipelines, Monitoring"},
    "BI_D3": {"label": "Nutzung & Entscheidungsintegration", "description": "Adoption, Reporting-Standards, Demand"},
    "PA_D1": {"label": "Prozessgrundlagen", "description": "Dokumentation, Standardisierung"},
    "PA_D2": {"label": "Automatisierungs-Readiness", "description": "Selektion, Machbarkeit, Risiko"},
    "PA_D3": {"label": "Betrieb & Skalierung", "description": "Runbooks, Monitoring, Governance, Skalierung"},
}


def dimension_label(dimension_id: str) -> str:
    meta = DIMENSION_LABELS.get(str(dimension_id or ""))
    return meta["label"] if meta else str(dimension_id or "Unbekannt")


def format_dimension(dimension_id: str, include_description: bool = False) -> str:
    raw_id = str(dimension_id or "Unbekannt")
    meta = DIMENSION_LABELS.get(raw_id)
    if not meta:
        return raw_id

    formatted = f"{meta['label']} ({raw_id})"
    if include_description:
        formatted = f"{formatted}: {meta['description']}"
    return formatted


def enrich_dimension_payload(dimension_id: str) -> dict[str, str]:
    raw_id = str(dimension_id or "")
    return {
        "id": raw_id,
        "label": dimension_label(raw_id),
        "display": format_dimension(raw_id),
        "description": DIMENSION_LABELS.get(raw_id, {}).get("description", ""),
    }
