# Export 1.2.0 – Entwicklernotiz

## Betroffene Module
- **Assessment / Scoring:** `app/services/assessment_service.py` (kritische Dimension inkl. Severity und Trigger-Items im Assessment-Ergebnis).
- **Domänenmodelle:** `domain/models.py` (neue Assessment-Felder `critical_dimension_*`).
- **Persistenz:** `persistence/repositories.py`, `app/ui/streamlit_app.py` (Speichern/Laden der neuen Assessment-Evidenz).
- **Maßnahmenlogik:** `app/services/recommendation_service.py` (deterministische Evidenz-Extraktion, Template-Mapping, PriorityScore, Gates, NOW/NEXT/LATER).
- **Template-Registry:** `app/services/initiative_templates.py` (konkrete Maßnahmen-Templates, Deliverables, KPI, Impact/Effort).
- **Export-Renderer:** `app/services/export_service.py` (Versionierung 1.0.0/1.1.0/1.2.0; kompakter Markdown/JSON-Output für 1.2.0).

## Datenstrukturen (neu/erweitert)
- Assessment enthält jetzt je Domäne:
  - `critical_dimension_id`
  - `critical_dimension_severity`
  - `critical_dimension_top_items` (`[{item_id, answer, deficit_score}]`)
- Maßnahmen enthalten konkrete Diagnosen, Deliverables (3), KPI und deterministische Priorisierung.

## Auswahl der Export-Version
- UI-Parameter in `app/ui/streamlit_app.py` (`selectbox`): `1.0.0`, `1.1.0`, `1.2.0`.
- `1.1.0` bleibt unverändert wählbar.
- `1.2.0` aktiviert den neuen kompakten Renderer.

## Prioritätsmodell 1.2.0
`priority = (impact / max(1, effort)) * criticality_weight * gap_weight`
- `criticality_weight`: Rang 1 → 1.30, Rang 2 → 1.15, sonst 1.00
- `gap_weight`: Zielreife Default BI=L3/PA=L3, clamp auf `[1.0, 1.6]`

## Gates
- **Governance-First:** Wenn `D1` Severity > 0.6, erhalten Non-Governance-Maßnahmen derselben Domäne eine Governance-Dependency.
- **Data-Quality-First:** Wenn BI_D2 Severity > 0.55, hängen fortgeschrittene BI/PA-Maßnahmen von der DQ/Semantik-nahen Maßnahme ab.
