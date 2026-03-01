# Schritt 0 – Zielbild und Minimalumfang (Umsetzungsannahmen)

## Zielbild des Prototyps
Der Prototyp „BI-AutoPilot“ unterstützt KMU dabei, für einen beschriebenen Use Case ein systematisches Vorgehen zur kombinierten Einführung von Business Intelligence und Prozessautomatisierung abzuleiten. Der Nutzer erfasst einen Use Case, beantwortet einen strukturierten Fragenkatalog und erhält als Ergebnis zwei getrennte Reifegradeinschätzungen (BI und Prozessautomatisierung), eine integrierte Synthese sowie einen priorisierbaren Maßnahmenkatalog. Das System ist als geschlossenes System ohne direkte Integrationen in operative Unternehmenssysteme konzipiert. Die Interaktion erfolgt über eine primäre Nutzerrolle (KMU-Entscheider bzw. Architekt).

## Use-Case-Typen
Es werden drei Use-Case-Typen unterstützt:

- **BI** (Schwerpunkt auf Reporting, Analytics, KPI, Datenmanagement)
- **AUTOMATION** (Schwerpunkt auf Prozessautomatisierung, Standardisierung, Workflow)
- **COMBINED** (kombinierte Betrachtung von BI und Automatisierung)

Der Use-Case-Typ dient zur Auswahl bzw. Gewichtung relevanter Fragen und zur Plausibilisierung der resultierenden Empfehlungen.

## Fragebogenumfang und Blockstruktur
Der Fragenkatalog umfasst **30 Fragen** und ist in vier Blöcke gegliedert:

1. **Erhebung/Context (6 Fragen):** Ziel, Prozesskontext, Häufigkeit, Kritikalität, Datenlage grob, Rollenverantwortung.  
2. **BI (10 Fragen):** Datenquellen, Datenqualität, KPI-Definition, Reporting-Nutzung, Self-Service, Governance/Ownership, Änderungsprozesse.  
3. **Prozessautomatisierung (10 Fragen):** Prozessdokumentation, Standardisierung, Varianz/Ausnahmen, Regelbasiertheit, Messbarkeit, Risiken/Kontrollen, Medienbrüche.  
4. **Synthese & Priorisierung (4 Fragen):** Abhängigkeiten BI↔PA, Nutzenprioritäten, Restriktionen (Zeit/Budget/Ressourcen), Risikotoleranz.

Pflichtfragen werden pro Block definiert (z. B. mindestens 4/6 in Context, 7/10 in BI und PA, 3/4 in Synthese), um eine robuste Bewertung zu ermöglichen.

## Bewertungslogik (Reproduzierbarkeit)
Die Reifegradbewertung erfolgt **regelbasiert** über ein **Scoring-Modell**:

- Jede Frage ist einer Dimension zugeordnet (BI-Dimensionen, PA-Dimensionen).  
- Antworten werden auf Punkte (z. B. 0–4) gemappt.  
- Dimension-Score = Aggregation der zugeordneten Fragen.  
- Gesamt-Reifegrad = Aggregation der Dimensionscores (z. B. gewichtetes Mittel).  
- Reifegradstufen: **1–5** (oder äquivalent Low/Med/High als abgeleitete Darstellung).

Das **LLM wird ausschließlich assistierend** genutzt:

- Zusammenfassung des Use Cases (Text)  
- Formulierung/Begründung der Bewertungen (Text)  
- Formulierung von Maßnahmenbeschreibungen (Text)

Das LLM liefert **keine** verbindlichen Scores oder Stufenentscheidungen, um Nachvollziehbarkeit und Reproduzierbarkeit zu erhöhen.

## Ergebnisartefakte (Minimalumfang)
Der Prototyp erzeugt und verwaltet folgende Artefakte:

- **UseCase:** Titel, Beschreibung, Typ (BI/AUTOMATION/COMBINED), Metadaten.  
- **AnswerSet:** Antworten auf den Fragebogen, Validierungsstatus (Draft/Validated).  
- **BIAssessment:** BI-Reifegrad (gesamt + optional Dimensionen), Kurzbegründung.  
- **PAAssessment:** Automatisierungs-Reifegrad (gesamt + optional Dimensionen), Kurzbegründung.  
- **Synthesis:** integrierte Sicht mit zentralen Engpässen und Abhängigkeiten.  
- **MeasureCatalog:** Maßnahmenliste mit Prioritätsvorschlag und Kategorisierung (BI/PA/Combined).  
- **UserSelection:** optionale Nutzerfinalisierung (Auswahl + finale Priorität).

## Minimaler Validierungsumfang
- Pflichtfragen beantwortet.  
- Datentypen plausibel (Skala/Zahl).  
- Konsistenzcheck leichtgewichtig (z. B. „keine Datenquellen“ vs. „tägliches Reporting“ wird markiert).
