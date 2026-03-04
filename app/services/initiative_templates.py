from __future__ import annotations

from dataclasses import dataclass, field

from domain.models import MeasureCategory


@dataclass(frozen=True)
class InitiativeTemplate:
    template_id: str
    title: str
    category: MeasureCategory
    goal: str
    diagnosis_template: str
    deliverables: tuple[str, str, str]
    kpi_name: str
    kpi_target_template: str
    kpi_measurement: str
    impact: int
    effort: int
    default_dependencies_by_gate: dict[str, tuple[str, ...]] = field(default_factory=dict)


FALLBACK_TEMPLATE = InitiativeTemplate(
    template_id="TPL_FALLBACK_BASE",
    title="Umsetzungsfahrplan mit messbaren Zwischenzielen",
    category=MeasureCategory.ORGANIZATIONAL,
    goal="Die priorisierte Dimension wird innerhalb eines Quartals in einen stabilen Umsetzungsmodus überführt.",
    diagnosis_template="In {dimension} zeigen {trigger_summary} den größten Handlungsdruck und bremsen die Reifeentwicklung.",
    deliverables=(
        "Ist-Analyse mit Ursachenliste und Scope pro Teilprozess",
        "90-Tage-Plan mit Ownern, Milestones und Review-Rhythmus",
        "Pilotumsetzung inkl. Lessons-Learned und Rollout-Entscheid",
    ),
    kpi_name="Meilensteinerreichung priorisierte Dimension",
    kpi_target_template=">= 80% der 90-Tage-Meilensteine termingerecht erreicht",
    kpi_measurement="Monatliches PMO-Tracking auf Maßnahmenebene",
    impact=3,
    effort=2,
)


TEMPLATE_REGISTRY: dict[str, InitiativeTemplate] = {
    "BI_GOV_FOUNDATION": InitiativeTemplate(
        template_id="BI_GOV_FOUNDATION",
        title="BI-Governance-Basics etablieren",
        category=MeasureCategory.GOVERNANCE,
        goal="Verbindliche Datenverantwortung und Entscheidungswege für BI werden organisationsweit wirksam.",
        diagnosis_template="In {dimension} zeigen {trigger_summary} fehlende Governance-Grundlagen und unklare Zuständigkeiten.",
        deliverables=(
            "Data-Owner- und Data-Steward-Rollenmodell mit Verantwortungsmatrix (RACI)",
            "Governance-Board mit Entscheidungslogik, Eskalationspfad und Terminserie",
            "Verabschiedete BI-Richtlinie inkl. Freigabeprozess für KPI-Änderungen",
        ),
        kpi_name="Abgedeckte kritische Datenobjekte mit benanntem Owner",
        kpi_target_template=">= 90% der kritischen Datenobjekte mit aktivem Owner bis Quartalsende",
        kpi_measurement="Monatliche Stichprobe aus Datenkatalog und Governance-Protokollen",
        impact=5,
        effort=2,
    ),
    "PA_GOV_FOUNDATION": InitiativeTemplate(
        template_id="PA_GOV_FOUNDATION",
        title="PA-Governance und Use-Case-Steuerung standardisieren",
        category=MeasureCategory.GOVERNANCE,
        goal="Automatisierungsvorhaben werden nach einheitlichen Kriterien priorisiert und risikobewusst gesteuert.",
        diagnosis_template="In {dimension} signalisieren {trigger_summary} unklare Entscheidungs- und Freigabeprozesse für Automatisierung.",
        deliverables=(
            "Use-Case Intake-Template mit Business Value, Risiko und Umsetzbarkeit",
            "Stage-Gate-Prozess von Idee bis Betrieb inkl. Go/No-Go-Kriterien",
            "Backlog-Board mit Priorisierungsschema und monatlicher Portfolioreview",
        ),
        kpi_name="Anteil priorisierter PA-Use-Cases mit dokumentiertem Gate-Status",
        kpi_target_template=">= 85% der aktiven Use-Cases mit vollständigem Stage-Gate-Status",
        kpi_measurement="Monatlicher Portfolio-Export aus dem Automatisierungs-Backlog",
        impact=5,
        effort=2,
    ),
    "BI_DQ_RULES": InitiativeTemplate(
        template_id="BI_DQ_RULES",
        title="Datenqualitätsregeln und Monitoring einführen",
        category=MeasureCategory.DATA,
        goal="Kritische BI-Daten sind mit klaren Qualitätsregeln hinterlegt und kontinuierlich überwacht.",
        diagnosis_template="{trigger_summary} zeigen in {dimension} konsistente Qualitätsdefizite in den zentralen Datenobjekten.",
        deliverables=(
            "Regelwerk für Vollständigkeit, Aktualität und Korrektheit je kritischem Datenobjekt",
            "DQ-Dashboard mit Ampellogik und Incident-Workflow",
            "Wöchentlicher Quality-Review mit Root-Cause- und Maßnahmenjournal",
        ),
        kpi_name="DQ-Regel-Compliance kritischer Datenobjekte",
        kpi_target_template=">= 95% der DQ-Checks bestehen im Monatsmittel",
        kpi_measurement="Automatisierte Auswertung der DQ-Checks pro Woche",
        impact=5,
        effort=3,
    ),
    "BI_SEMANTIC_LAYER": InitiativeTemplate(
        template_id="BI_SEMANTIC_LAYER",
        title="Semantik- und KPI-Definitionen harmonisieren",
        category=MeasureCategory.DATA,
        goal="Fachbereiche arbeiten mit einheitlichen KPI-Definitionen und nachvollziehbarer Datenherkunft.",
        diagnosis_template="In {dimension} deuten {trigger_summary} auf uneinheitliche Begriffe und fehlende semantische Standards hin.",
        deliverables=(
            "Business Glossar mit verbindlichen KPI-Definitionen und Ownern",
            "Semantische Schicht für Kernkennzahlen inkl. Berechnungslogik",
            "Freigabeprozess für neue/angepasste Kennzahlen mit Versionierung",
        ),
        kpi_name="KPI-Definitionstreue in Standardreports",
        kpi_target_template=">= 90% der Standardreports nutzen freigegebene KPI-Definitionen",
        kpi_measurement="Monatlicher Report-Audit gegen Glossar und Semantic Layer",
        impact=4,
        effort=2,
    ),
    "PA_PIPELINE_STANDARD": InitiativeTemplate(
        template_id="PA_PIPELINE_STANDARD",
        title="Automatisierungs-Pipeline industrialisieren",
        category=MeasureCategory.TECHNICAL,
        goal="Automatisierungs-Lösungen werden mit wiederverwendbaren Build-, Test- und Release-Standards bereitgestellt.",
        diagnosis_template="{trigger_summary} zeigen in {dimension} Lücken in Testbarkeit und operationaler Stabilität der Automatisierungen.",
        deliverables=(
            "Standardisierte CI/CD-Pipeline für Automatisierungsartefakte",
            "Automatisierte Regressionstests für kritische Prozesspfade",
            "Betriebshandbuch mit Monitoring, Alerting und Fallback-Prozeduren",
        ),
        kpi_name="Fehlerfreie Deployments von Automatisierungen",
        kpi_target_template=">= 90% der Releases ohne kritischen Incident in 30 Tagen",
        kpi_measurement="Release- und Incident-Auswertung je Monat",
        impact=4,
        effort=3,
    ),
    "PA_OPERATIONS": InitiativeTemplate(
        template_id="PA_OPERATIONS",
        title="PA-Betriebsmodell und Skalierungsroutine aufbauen",
        category=MeasureCategory.TECHNICAL,
        goal="Automatisierungen werden über End-to-End-Prozesse stabil skaliert und wirtschaftlich betrieben.",
        diagnosis_template="In {dimension} weisen {trigger_summary} auf fehlende End-to-End-Verantwortung und Betriebsroutinen hin.",
        deliverables=(
            "Runbook-Set für Betrieb, Incident-Management und Kapazitätsplanung",
            "SLA-Definitionen je Automatisierungsprozess inkl. Eskalation",
            "Skalierungsboard mit quartalsweiser Roadmap für E2E-Integration",
        ),
        kpi_name="SLA-Erfüllung automatisierter Kernprozesse",
        kpi_target_template=">= 95% SLA-Erfüllung über die letzten 8 Wochen",
        kpi_measurement="Wöchentliche Betriebskennzahlen aus Monitoring und Ticketing",
        impact=4,
        effort=3,
    ),
    "ENABLEMENT": InitiativeTemplate(
        template_id="ENABLEMENT",
        title="Kompetenzaufbau für BI/PA-Enablement umsetzen",
        category=MeasureCategory.ORGANIZATIONAL,
        goal="Fachliche und technische Schlüsselkompetenzen für BI/PA sind durch Rollenpfade und Trainings abgesichert.",
        diagnosis_template="{trigger_summary} machen in {dimension} Kompetenz- und Enablement-Lücken sichtbar.",
        deliverables=(
            "Skill-Matrix für BI/PA-Rollen mit Soll-/Ist-Abgleich",
            "Trainingscurriculum mit Pflichtmodulen und Praxisformaten",
            "Mentoring- und Community-of-Practice-Format mit monatlichem Review",
        ),
        kpi_name="Abdeckung kritischer Rollen mit Sollkompetenz",
        kpi_target_template=">= 80% der kritischen Rollen erfüllen definierte Sollkompetenz",
        kpi_measurement="Quartalsweises Skill-Assessment mit HR/Teamlead-Abgleich",
        impact=3,
        effort=2,
    ),
}


DIMENSION_TEMPLATE_MAP: dict[str, list[str]] = {
    "BI_D1": ["BI_GOV_FOUNDATION"],
    "BI_D2": ["BI_DQ_RULES"],
    "BI_D3": ["BI_SEMANTIC_LAYER", "ENABLEMENT"],
    "PA_D1": ["PA_GOV_FOUNDATION"],
    "PA_D2": ["PA_PIPELINE_STANDARD"],
    "PA_D3": ["PA_OPERATIONS", "ENABLEMENT"],
}


def template_for_dimension(dimension_id: str) -> InitiativeTemplate:
    template_ids = DIMENSION_TEMPLATE_MAP.get(dimension_id, [])
    if template_ids:
        return TEMPLATE_REGISTRY[template_ids[0]]
    return FALLBACK_TEMPLATE
