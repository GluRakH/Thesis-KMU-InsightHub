# InsightHub Export
- Export Version: 2.0.0
- Run-ID: run-20260305193659
- Timestamp: 2026-03-05T19:36:59.362692+00:00

## Assessment
- BI-Score: 34.00 (L1)
- PA-Score: 41.00 (L2)

## Maßnahmenkatalog (deterministisch)
### Jetzt
- INIT-BI-GOVERNANCE-01 | BI-Governance-Basics etablieren | PriorityScore=4.23 | Rang=1
  - Sequenz: Keine aktive Gate-Blockade
  - Lieferobjekte: Data-Owner- und Data-Steward-Rollenmodell mit Verantwortungsmatrix (RACI), Governance-Board mit Entscheidungslogik, Eskalationspfad und Terminserie, Verabschiedete BI-Richtlinie inkl. Freigabeprozess für KPI-Änderungen
  - KPI: Abgedeckte kritische Datenobjekte mit benanntem Owner | Ziel: >= 90% der kritischen Datenobjekte mit aktivem Owner bis Quartalsende | Messung: Monatliche Stichprobe aus Datenkatalog und Governance-Protokollen
  - Evidenz: Dimension BI_D1 | Severity 0.83
    - Evidenz-Trigger: DA_01 (1) deficit=1.0
    - Evidenz-Trigger: DA_02 (2) deficit=0.75
    - Evidenz-Trigger: DA_03 (2) deficit=0.75
- INIT-PA-GOVERNANCE-01 | PA-Governance und Use-Case-Steuerung standardisieren | PriorityScore=3.31 | Rang=2
  - Sequenz: Keine aktive Gate-Blockade
  - Lieferobjekte: Use-Case Intake-Template mit Business Value, Risiko und Umsetzbarkeit, Stage-Gate-Prozess von Idee bis Betrieb inkl. Go/No-Go-Kriterien, Backlog-Board mit Priorisierungsschema und monatlicher Portfolioreview
  - KPI: Anteil priorisierter PA-Use-Cases mit dokumentiertem Gate-Status | Ziel: >= 85% der aktiven Use-Cases mit vollständigem Stage-Gate-Status | Messung: Monatlicher Portfolio-Export aus dem Automatisierungs-Backlog
  - Evidenz: Dimension PA_D1 | Severity 0.75
    - Evidenz-Trigger: PA_01 (2) deficit=0.75
    - Evidenz-Trigger: PA_02 (2) deficit=0.75
### Als Nächstes
- INIT-BI-DATA-03 | Semantik- und KPI-Definitionen harmonisieren | PriorityScore=2.60 | Rang=3
  - Sequenz: Governance vor Skalierung
  - Lieferobjekte: Business Glossar mit verbindlichen KPI-Definitionen und Ownern, Semantische Schicht für Kernkennzahlen inkl. Berechnungslogik, Freigabeprozess für neue/angepasste Kennzahlen mit Versionierung
  - KPI: KPI-Definitionstreue in Standardreports | Ziel: >= 90% der Standardreports nutzen freigegebene KPI-Definitionen | Messung: Monatlicher Report-Audit gegen Glossar und Semantic Layer
  - Evidenz: Dimension BI_D3 | Severity 0.00
    - Evidenz-Trigger: DA_09 (None) deficit=0.0
    - Evidenz-Trigger: DA_10 (None) deficit=0.0
- INIT-BI-DATA-02 | Datenqualitätsregeln und Monitoring einführen | PriorityScore=2.17 | Rang=4
  - Sequenz: Governance vor Skalierung
  - Lieferobjekte: Regelwerk für Vollständigkeit, Aktualität und Korrektheit je kritischem Datenobjekt, DQ-Dashboard mit Ampellogik und Incident-Workflow, Wöchentlicher Quality-Review mit Root-Cause- und Maßnahmenjournal
  - KPI: DQ-Regel-Compliance kritischer Datenobjekte | Ziel: >= 95% der DQ-Checks bestehen im Monatsmittel | Messung: Automatisierte Auswertung der DQ-Checks pro Woche
  - Evidenz: Dimension BI_D2 | Severity 0.00
    - Evidenz-Trigger: DA_05 (None) deficit=0.0
    - Evidenz-Trigger: DA_06 (None) deficit=0.0
- INIT-PA-TECHNICAL-02 | Automatisierungs-Pipeline industrialisieren | PriorityScore=1.53 | Rang=5
  - Sequenz: Governance vor Skalierung
  - Lieferobjekte: Standardisierte CI/CD-Pipeline für Automatisierungsartefakte, Automatisierte Regressionstests für kritische Prozesspfade, Betriebshandbuch mit Monitoring, Alerting und Fallback-Prozeduren
  - KPI: Fehlerfreie Deployments von Automatisierungen | Ziel: >= 90% der Releases ohne kritischen Incident in 30 Tagen | Messung: Release- und Incident-Auswertung je Monat
  - Evidenz: Dimension PA_D2 | Severity 0.62
    - Evidenz-Trigger: PA_04 (2) deficit=0.75
    - Evidenz-Trigger: PA_03 (3) deficit=0.5
- INIT-PA-TECHNICAL-03 | PA-Betriebsmodell und Skalierungsroutine aufbauen | PriorityScore=1.53 | Rang=6
  - Sequenz: Governance vor Skalierung
  - Lieferobjekte: Runbook-Set für Betrieb, Incident-Management und Kapazitätsplanung, SLA-Definitionen je Automatisierungsprozess inkl. Eskalation, Skalierungsboard mit quartalsweiser Roadmap für E2E-Integration
  - KPI: SLA-Erfüllung automatisierter Kernprozesse | Ziel: >= 95% SLA-Erfüllung über die letzten 8 Wochen | Messung: Wöchentliche Betriebskennzahlen aus Monitoring und Ticketing
  - Evidenz: Dimension PA_D3 | Severity 0.00
    - Evidenz-Trigger: PA_08 (None) deficit=0.0
    - Evidenz-Trigger: COUP_02 (None) deficit=0.0
### Später
- Keine Maßnahmen in diesem Bucket.

## Risiken & Abhängigkeiten
- governance_first aktiv: Blocker INIT-BI-GOVERNANCE-01 -> INIT-BI-DATA-02, INIT-BI-DATA-03
- governance_first aktiv: Blocker INIT-PA-GOVERNANCE-01 -> INIT-PA-TECHNICAL-02, INIT-PA-TECHNICAL-03