# Reproduzierbarkeit des InsightHub-Prototyps (thesis-ready)

## 1. Zielbild und Determinismus
Der Prototyp erzeugt BI/PA-Bewertungen, priorisierte Maßnahmen und auditierbare Exporte **deterministisch** aus Fragebogenantworten, Scoring-Regeln und Template-Konfiguration.

Kernelemente:
- Regelbasierte Ableitung (keine Pflicht-Abhängigkeit von LLM für Maßnahmeninhalt).
- Versionierte Template-Quelle (`app/config/templates.yaml`).
- Vollständige Evidenz pro Maßnahme (`dimension_id`, `severity`, `trigger_items`, `rationale`).
- Persistente Run-Artefakte mit `run_id` und `configuration_hash`.

## 2. Artefakte und Versionierung
- Templates: `app/config/templates.yaml` mit `template_version` und `template_id` je Maßnahme.
- Empfehlungsgenerierung: `app/services/recommendation_service.py`.
- Exportlogik + Run-Persistenz: `app/services/export_service.py`.
- Deterministische Zusammenfassung: `app/services/catalog_summary_service.py`.
- UI-Darstellung inkl. Legende: `app/ui/streamlit_app.py`.

## 3. Setup und Start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.
streamlit run app/ui/streamlit_app.py
```

## 4. Reproduzierbarer Run (Ablauf)
1. **Use Case anlegen** (Schritt 1).
2. **Fragebogen ausfüllen** und speichern (Schritt 2).
3. **Bewertung berechnen** (Schritt 3).
4. **Maßnahmenkatalog generieren** (Schritt 4).
5. **Export 2.0.0 herunterladen** (Schritt 5).

Beim Export wird automatisch ein `run_id` erzeugt und unter `runs/<run_id>.json` gespeichert. Das Run-Objekt enthält:
- `answer_set_id`
- Ergebnis-JSON
- Zeitstempel
- `configuration_hash` aus Template-Version + Gate-Schwellen

## 5. Nachvollziehbarkeit im Export
JSON-Export enthält:
- `export_version`
- `assessment` (Scores, Levels, Dimensionscores)
- `initiatives` (Buckets Jetzt/Nächstes/Später)
- vollständige Maßnahmendetails: Deliverables, KPI, Evidence, Dependencies, Template-Referenz
- `rules_applied` (aktivierte Gates, Schwellen, Kanten)
- `generation_metadata` (Template-Version, Prompt/LLM-Metadaten)

Markdown-Export enthält kompakte Audit-Sicht:
- Rang/PriorityScore
- Sequenzbegründung
- Evidenz-Trigger (Item-ID, Antwort, Defizit)
- aktive Gate-Regeln unter „Risiken & Abhängigkeiten“

## 6. Qualitätssicherung
Empfohlene Mindesttests:
```bash
PYTHONPATH=. pytest tests/test_recommendation_service.py tests/test_export_service.py -q
```
Abgedeckt sind u. a.:
- YAML-Loader + Schema-Regeln (3 Deliverables)
- PriorityScore > 0
- Bucketing mit mindestens einem NOW-Eintrag
- Evidence-Trigger-Länge (2–3) und Defizitbereich [0,1]

## 7. Hinweise für Thesis-Evaluation
- Die Reproduzierbarkeit basiert auf `run_id` + `configuration_hash`.
- Für Vergleichsläufe sollten identische Antwortsets mit stabiler Template-Version genutzt werden.
- Änderungen an `templates.yaml` verändern bewusst die Ableitungslogik und müssen in der Thesis als neue Konfigurationsversion dokumentiert werden.
