# InsightHub Export
- Export Version: 1.1.0
- Timestamp: 2026-03-04T18:26:59.081254+00:00

## Evidenzüberblick
### BI
- Kritischste Dimension: BI_D1
  - DA_01: answer=1 deficit=1.0
  - DA_03: answer=1 deficit=1.0
  - DA_02: answer=2 deficit=0.75
### PA
- Kritischste Dimension: PA_D1
  - PA_02: answer=1 deficit=1.0
  - PA_01: answer=2 deficit=0.75
  - PA_07: answer=3 deficit=0.5

## Maßnahmen
### NOW
- INIT-BI-GOVERNANCE-01 | Standardisieren und stabilisieren: BI_D1 | Ziel: Erreiche in BI_D1 den nächsten stabilen Reifezustand durch 'Standardisieren und stabilisieren: BI_D1'. | PriorityScore=3.25 (I=5.0, E=2.0, CW=1.3, GW=1.0)
  - Dependencies: Abstimmung mit angrenzenden BI/PA-Dimensionen
  - KPI: Fortschritt BI_D1 | Target: Mindestwert >= aktueller Baseline | Messung: Monatlicher Mittelwert der Dimensions-Items (0-100)
  - Trigger: DA_01 (1) deficit=1.0
  - Trigger: DA_03 (1) deficit=1.0
  - Trigger: DA_02 (2) deficit=0.75
- INIT-PA-GOVERNANCE-01 | Standardisieren und stabilisieren: PA_D1 | Ziel: Erreiche in PA_D1 den nächsten stabilen Reifezustand durch 'Standardisieren und stabilisieren: PA_D1'. | PriorityScore=2.875 (I=5.0, E=2.0, CW=1.15, GW=1.0)
  - Dependencies: Abstimmung mit angrenzenden BI/PA-Dimensionen
  - KPI: Fortschritt PA_D1 | Target: Mindestwert >= aktueller Baseline | Messung: Monatlicher Mittelwert der Dimensions-Items (0-100)
  - Trigger: PA_02 (1) deficit=1.0
  - Trigger: PA_01 (2) deficit=0.75
  - Trigger: PA_07 (3) deficit=0.5
- INIT-BI-TECHNICAL-02 | Standardisieren und stabilisieren: BI_D2 | Ziel: Erreiche in BI_D2 den nächsten stabilen Reifezustand durch 'Standardisieren und stabilisieren: BI_D2'. | PriorityScore=2.875 (I=5.0, E=2.0, CW=1.15, GW=1.0)
  - Dependencies: Abstimmung mit angrenzenden BI/PA-Dimensionen, INIT-BI-GOVERNANCE-01
  - KPI: Fortschritt BI_D2 | Target: Mindestwert >= aktueller Baseline | Messung: Monatlicher Mittelwert der Dimensions-Items (0-100)
  - Trigger: DA_05 (2) deficit=0.75
  - Trigger: DA_06 (2) deficit=0.75
  - Trigger: DA_08 (2) deficit=0.75
- INIT-PA-TECHNICAL-02 | Standardisieren und stabilisieren: PA_D2 | Ziel: Erreiche in PA_D2 den nächsten stabilen Reifezustand durch 'Standardisieren und stabilisieren: PA_D2'. | PriorityScore=2.5 (I=5.0, E=2.0, CW=1.0, GW=1.0)
  - Dependencies: Abstimmung mit angrenzenden BI/PA-Dimensionen, INIT-PA-GOVERNANCE-01
  - KPI: Fortschritt PA_D2 | Target: Mindestwert >= aktueller Baseline | Messung: Monatlicher Mittelwert der Dimensions-Items (0-100)
  - Trigger: PA_03 (2) deficit=0.75
  - Trigger: PA_05 (2) deficit=0.75
  - Trigger: PA_06 (2) deficit=0.75
### NEXT
- INIT-BI-ORGANIZATIONAL-03 | Integrieren und skalieren: BI_D3 | Ziel: Erreiche in BI_D3 den nächsten stabilen Reifezustand durch 'Integrieren und skalieren: BI_D3'. | PriorityScore=1.0 (I=3.0, E=3.0, CW=1.0, GW=1.0)
  - Dependencies: Abstimmung mit angrenzenden BI/PA-Dimensionen, INIT-BI-GOVERNANCE-01
  - KPI: Fortschritt BI_D3 | Target: Mindestwert >= aktueller Baseline | Messung: Monatlicher Mittelwert der Dimensions-Items (0-100)
  - Trigger: COUP_01 (1) deficit=1.0
  - Trigger: DA_09 (2) deficit=0.75
  - Trigger: DA_12 (2) deficit=0.75
- INIT-PA-ORGANIZATIONAL-03 | Integrieren und skalieren: PA_D3 | Ziel: Erreiche in PA_D3 den nächsten stabilen Reifezustand durch 'Integrieren und skalieren: PA_D3'. | PriorityScore=1.0 (I=3.0, E=3.0, CW=1.0, GW=1.0)
  - Dependencies: Abstimmung mit angrenzenden BI/PA-Dimensionen, INIT-PA-GOVERNANCE-01
  - KPI: Fortschritt PA_D3 | Target: Mindestwert >= aktueller Baseline | Messung: Monatlicher Mittelwert der Dimensions-Items (0-100)
  - Trigger: PA_08 (2) deficit=0.75
  - Trigger: COUP_02 (2) deficit=0.75
### LATER