# Thesis-KMU-InsightHub

Stabile Demo für BI/PA-Assessment inkl. Validierung, Scoring, Synthesis und Maßnahmenkatalog.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional für reproduzierbare LLM-Läufe ohne API-Key:

```bash
export LLM_DRY_RUN=true
export LLM_TRACE_FILE=logs/llm_traces.jsonl
```

> Ohne `OPENAI_API_KEY` läuft die Demo weiterhin stabil mit Dummy/Fallback-Ausgaben.

## Run

### API (FastAPI)

```bash
uvicorn app.api.main:app --reload
```

### UI (Streamlit)

```bash
streamlit run app/ui/streamlit_app.py
```

## Demo-Flow

1. **Use Case anlegen** (`POST /usecases`)
2. **Antworten speichern** (`POST /answersets`, Version z. B. `v1.0`)
3. **Validieren & sperren** (`POST /answersets/{answer_set_id}/validate`)
4. **Assessments rechnen** (`POST /assessments/{answer_set_id}`)
5. **Synthesis erzeugen** (`POST /synthesis/{answer_set_id}`)
6. **Katalog erstellen** (`POST /catalog/{answer_set_id}`)
7. **Maßnahmen finalisieren** (`POST /catalog/{catalog_id}/selection`)
8. **Ergebnisse abrufen** (`GET /results/{use_case_id}`)

## Reproduzierbarkeit

Folgende Versionsfelder werden persistiert:

- **Questionnaire-Version** (`questionnaire_version`)
- **Scoring-Version** (`scoring_version`)
- **Prompt-Version** (`prompt_version`)
- **Model-Version / Modellname** (`model_version`, `llm_model`)

Zusätzlich werden LLM-Trace-Events in `logs/llm_traces.jsonl` protokolliert (Task, Prompt-Version, Modell, Hash, Modus).

## Qualität / Tests

```bash
python -m unittest discover -s tests
```

Getestet werden u. a.:

- Validierungsregeln (Pflichtfelder, Typprüfung, Konsistenzhinweise)
- Scoring-Regeln (inkl. Rule-Typen und Fehlerfälle)
- Synthesis-Heuristikregeln (BI-first, PA-first, Balanced)
- Persistenz der Reproduzierbarkeitsfelder

## Repository-Aufräumarbeiten

Die folgenden nicht mehr benötigten Artefakte wurden entfernt:

- veraltete Thesis-Dokumente im Projekt-Root (`Thesis.pdf`, `chapter1.tex`, `chapter2.tex`, `chapter3.tex`)
- leere Platzhalterverzeichnisse unter `app/` (nur `.gitkeep` ohne produktiven Inhalt)
