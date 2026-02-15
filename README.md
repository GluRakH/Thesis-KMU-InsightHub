# Thesis-KMU-InsightHub

Stabile Demo für BI/PA-Assessment inkl. Validierung, Scoring, Synthesis und Maßnahmenkatalog.

## Setup

### 1) Notwendige Software installieren

#### Pflicht

- **Git** (zum Klonen des Repositories)
- **Python 3.11+** (empfohlen: 3.11 oder 3.12)
- **pip** (normalerweise in Python enthalten)

#### Optional (für lokale LLM-Texte)

- **Ollama** (lokaler Modellserver)
- mindestens ein Modell, z. B. `llama3.1:8b`

Beispiel-Kommandos:

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip

# macOS (mit Homebrew)
brew install git python

# Optional: Ollama installieren (siehe offizielle Doku)
# https://ollama.com/download
```

### 2) Repository klonen und in den Projektordner wechseln

```bash
git clone <DEIN_REPO_URL>
cd Thesis-KMU-InsightHub
```

### 3) Virtuelle Umgebung anlegen und aktivieren

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4) Optional: LLM-Modus konfigurieren

Optional für reproduzierbare LLM-Läufe ohne API-Key:

```bash
export LLM_DRY_RUN=true
export LLM_TRACE_FILE=logs/llm_traces.jsonl
```

Optional für Live-Zugriff auf eine lokale Ollama-Installation:

```bash
export LLM_MODEL=llama3.1:8b
export LLM_API_URL=http://localhost:11434/api/generate
# optional, falls deine Ollama-Instanz abgesichert ist
export OLLAMA_API_KEY=...
```

> Ohne laufendes Ollama läuft die Demo weiterhin stabil mit Dummy/Fallback-Ausgaben.

### 5) API lokal starten (Hosting lokal auf deinem Rechner)

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

- API erreichbar unter: `http://localhost:8000`
- Swagger UI unter: `http://localhost:8000/docs`

### 6) Streamlit-UI starten

Öffne ein **zweites Terminal**, aktiviere dort ebenfalls die virtuelle Umgebung und starte:

```bash
streamlit run app/ui/streamlit_app.py --server.port 8501
```

- UI erreichbar unter: `http://localhost:8501`

### 7) Funktionstest durchführen

Wenn API und UI laufen, kannst du prüfen:

- API Root: `GET http://localhost:8000/`
- Fragebogen laden: `GET http://localhost:8000/questionnaire?version=v1.0`
- End-to-End-Flow über Swagger (`/docs`) oder über die Streamlit-Oberfläche.

### 8) Tests lokal ausführen (empfohlen)

```bash
python -m unittest discover -s tests
```

### 9) Häufige Fehler & schnelle Lösungen

- **`ModuleNotFoundError`**: Prüfe, ob die virtuelle Umgebung aktiv ist.
- **Port bereits belegt (`8000` oder `8501`)**: Starte mit anderem Port, z. B. `--port 8001`.
- **LLM/Ollama nicht erreichbar**: Setze `LLM_DRY_RUN=true`, dann läuft die App mit Fallback-Ausgaben.

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


## LLM-Integration (lokales Ollama)

- Die LLM-Aufrufe nutzen die Ollama API (**`/api/generate`**).
- Für jeden Task werden strukturierte JSON-Ausgaben erwartet (z. B. `summary`, `rationale`, `measures[]`).
- Das LLM liefert JSON-Objekte, die anschließend in Textartefakte für Synthese und Maßnahmen überführt werden.
- Reifegrade und Scores bleiben vollständig regelbasiert und deterministisch im Scoring-Code.
- API und Streamlit erlauben optional einen **`ollama_api_key`** bzw. ein API-Key-Feld in der Sidebar für abgesicherte Ollama-Instanzen.

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
