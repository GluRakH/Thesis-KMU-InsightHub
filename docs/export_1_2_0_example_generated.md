# InsightHub Export
- Export Version: 1.2.0
- Timestamp: 2026-03-04T20:00:03.029632+00:00

## Evidenzüberblick
### BI
- Kritischste Dimension: BI_D1 | Severity: 0.79
- Top-Trigger-Items: DA_01=1 (1.00), DA_02=2 (0.75)
### PA
- Kritischste Dimension: PA_D1 | Severity: 0.67
- Top-Trigger-Items: PA_01=2 (0.75), PA_02=2 (0.75)

## Maßnahmen
### NOW
- INIT-BI-GOVERNANCE-01 | BI-Governance-Basics etablieren | BI_D1 | governance | PriorityScore=3.25
  - Diagnose: In BI_D1 zeigen DA_01=1 (deficit 1.00) und DA_02=2 (deficit 0.75) fehlende Governance-Grundlagen.
  - Deliverable: RACI-Modell verabschieden
  - Deliverable: Governance-Board starten
  - Deliverable: BI-Richtlinie publizieren
  - Dependencies: keine
  - KPI: Owner-Abdeckung | Ziel: >= 90% | Messung: Monatliche Katalogprüfung
### NEXT
- INIT-BI-DATA-02 | Datenqualitätsregeln und Monitoring einführen | BI_D2 | data | PriorityScore=1.92
  - Diagnose: DA_05=2 (deficit 0.75) und DA_06=2 (deficit 0.75) zeigen Qualitätsdefizite.
  - Deliverable: DQ-Regelwerk definieren
  - Deliverable: DQ-Dashboard bereitstellen
  - Deliverable: Quality-Review etablieren
  - Dependencies: INIT-BI-GOVERNANCE-01
  - KPI: DQ-Compliance | Ziel: >= 95% | Messung: Wöchentlicher DQ-Run
### LATER