# InsightHub Export
- Export Version: 1.1.0
- Timestamp: 2026-03-04T20:00:03.029101+00:00

## Evidenzüberblick
### BI
- Kritischste Dimension: BI_D1
### PA
- Kritischste Dimension: PA_D1

## Maßnahmen
### NOW
- INIT-BI-GOVERNANCE-01 | BI-Governance-Basics etablieren | Ziel: Erreiche in BI_D1 den nächsten stabilen Reifezustand durch 'BI-Governance-Basics etablieren'. | PriorityScore=3.25 (I=5.0, E=2.0, CW=1.3, GW=1.0)
  - Dependencies: Keine
  - KPI: Owner-Abdeckung | Target: >= 90% | Messung: Monatliche Katalogprüfung
### NEXT
- INIT-BI-DATA-02 | Datenqualitätsregeln und Monitoring einführen | Ziel: Erreiche in BI_D2 den nächsten stabilen Reifezustand durch 'Datenqualitätsregeln und Monitoring einführen'. | PriorityScore=1.92 (I=5.0, E=3.0, CW=1.15, GW=1.0)
  - Dependencies: INIT-BI-GOVERNANCE-01
  - KPI: DQ-Compliance | Target: >= 95% | Messung: Wöchentlicher DQ-Run
### LATER