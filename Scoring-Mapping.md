# Scoring-Mapping (v1.0) – minimal & lauffähig

## Grundprinzip
- Jede Frage wird genau **einer Dimension** zugeordnet.
- Jede Antwort wird auf **0–4 Punkte** gemappt (je höher, desto reifer/geeigneter).
- Dimension-Score = Mittelwert der Punkte aller Fragen in der Dimension.
- Gesamt-Score (BI bzw. PA) = Mittelwert der Dimensionscores (gleich gewichtet).
- Reifegradstufe (1–5) aus Gesamt-Score:
  - 0.0–0.9 → **1**
  - 1.0–1.9 → **2**
  - 2.0–2.9 → **3**
  - 3.0–3.5 → **4**
  - 3.6–4.0 → **5**

> Hinweis: Context- und Synthese-Fragen fließen **nicht** in BI/PA-Reifegrade ein, sondern in Synthese/Priorisierung (Heuristiken). Damit bleibt das Reifegrad-Scoring minimal und stabil.

---

## BI-Dimensionen (3)
- **BI_D1 Data Foundation** (Zugriff, Quellen, Qualität, Standardisierung)
- **BI_D2 Measurement & Governance** (KPI-Definition, Ownership, Monitoring)
- **BI_D3 Delivery & Usage** (Reporting-Nutzung, Aktualität, Self-Service)

### Zuordnung Fragen → Dimension
- **BI_D1:** BI_01, BI_02, BI_03, BI_07
- **BI_D2:** BI_04, BI_08, BI_10
- **BI_D3:** BI_05, BI_06, BI_09

---

## PA-Dimensionen (3)
- **PA_D1 Process Readiness** (Dokumentation, Standardisierung, Ausnahmen, Messbarkeit)
- **PA_D2 Automation Feasibility** (Regelbasiertheit, Medienbrüche, Systemanzahl)
- **PA_D3 Change & Control** (Compliance-Anforderungen, Änderungsbereitschaft, Erfahrung)

### Zuordnung Fragen → Dimension
- **PA_D1:** PA_01, PA_02, PA_03, PA_07
- **PA_D2:** PA_04, PA_05, PA_06
- **PA_D3:** PA_08, PA_09, PA_10

---

# Punkte-Mapping je Frage (0–4)

## Context (nur heuristisch, kein BI/PA-Score)
- CTX_01: kein Score (nur Metadaten)
- CTX_02: kein Score (Text)
- CTX_03: kein Score (optional Heuristik)
- CTX_04: kein Score (optional Heuristik)
- CTX_05: kein Score
- CTX_06: kein Score (kann später Effort/Prio beeinflussen)

## BI-Fragen

### BI_01 (MULTI_CHOICE) → BI_D1
Punkte = min(4, Anzahl gewählter Quellen - 1), mindestens 0  
- 0–1 Quelle → 0  
- 2 Quellen → 1  
- 3 Quellen → 2  
- 4 Quellen → 3  
- ≥5 Quellen → 4  

### BI_02 (SCALE 1–5) → BI_D1
Punkte = Antwort - 1

### BI_03 (SCALE 1–5) → BI_D1
Punkte = Antwort - 1

### BI_04 (SINGLE_CHOICE) → BI_D2
- Nein → 0  
- Teilweise → 2  
- Ja → 4  

### BI_05 (SINGLE_CHOICE) → BI_D3
- Nicht vorhanden → 0  
- Unregelmäßig/ad hoc → 1  
- Regelmäßig, aber wenig standardisiert → 3  
- Regelmäßig und standardisiert → 4  

### BI_06 (SINGLE_CHOICE) → BI_D3
Interpretation: höhere Aktualität erfordert höhere BI-Reife.
- Echtzeit/nahe Echtzeit → 4  
- Stündlich → 3  
- Täglich → 2  
- Wöchentlich → 1  
- Monatlich → 0  

### BI_07 (SCALE 1–5) → BI_D1
Punkte = Antwort - 1

### BI_08 (SINGLE_CHOICE) → BI_D2
- Nein → 0  
- Teilweise → 2  
- Ja → 4  

### BI_09 (SCALE 1–5) → BI_D3
Punkte = Antwort - 1

### BI_10 (SCALE 1–5) → BI_D2
Punkte = Antwort - 1

---

## PA-Fragen

### PA_01 (SCALE 1–5) → PA_D1
Punkte = Antwort - 1

### PA_02 (SCALE 1–5) → PA_D1
Punkte = Antwort - 1

### PA_03 (SINGLE_CHOICE) → PA_D1
- Sehr häufig → 0  
- Häufig → 1  
- Gelegentlich → 3  
- Selten → 4  

### PA_04 (SCALE 1–5) → PA_D2
Punkte = Antwort - 1

### PA_05 (SCALE 1–5) → PA_D2
Interpretation: mehr Medienbrüche = höheres Automatisierungspotenzial, aber oft geringe Reife.
Für minimalen Prototyp als „Feasibility“-Indikator: mehr Medienbrüche → mehr Punkte.
Punkte = Antwort - 1

### PA_06 (SINGLE_CHOICE) → PA_D2
Interpretation: weniger Systeme = einfacher zu automatisieren (im Prototyp).
- 1 → 4  
- 2–3 → 3  
- 4–5 → 1  
- >5 → 0  

### PA_07 (SCALE 1–5) → PA_D1
Punkte = Antwort - 1

### PA_08 (SCALE 1–5) → PA_D3
Interpretation: höhere Compliance-Anforderungen erhöhen Komplexität (Prototyp: niedriger Score).
Punkte = 5 - Antwort  
(Beispiel: 5 → 0 Punkte, 1 → 4 Punkte)

### PA_09 (SCALE 1–5) → PA_D3
Punkte = Antwort - 1

### PA_10 (SINGLE_CHOICE) → PA_D3
- Keine → 0  
- Erste Piloten → 2  
- Regelmäßig im Einsatz → 3  
- Breite Nutzung/Center of Excellence → 4  

---

# Synthese & Priorisierung (Heuristiken, kein Reifegrad-Score)

## SYN_01 (SCALE 1–5) – Abhängigkeit
- Kann genutzt werden, um Maßnahmen als „COMBINED“ zu markieren, wenn ≥4.

## SYN_02 (MULTI_CHOICE) – Nutzenprioritäten
- Kann genutzt werden, um Prioritäten zu verschieben:
  - Zeitersparnis → PA-Maßnahmen +1 Priorität
  - Transparenz/Steuerung → BI-Maßnahmen +1 Priorität
  - Risiko/Compliance → Governance/Kontroll-Maßnahmen +1 Priorität

## SYN_03 (SCALE 1–5) – Risikotoleranz
- Niedrig (≤2) → „Pilot klein anfangen“ Maßnahmen höher priorisieren.

## SYN_04 (SINGLE_CHOICE) – Zeithorizont
- <1 Monat / 1–3 Monate → Quick Wins höher priorisieren
- >6 Monate → Roadmap/Plattformmaßnahmen höher priorisieren
