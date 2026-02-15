# Fragebogen (v1.0) – 30 Fragen für BI-AutoPilot

**Konventionen**
- **ID**: eindeutige Kennung
- **Antworttyp**: `TEXT | SINGLE_CHOICE | MULTI_CHOICE | NUMBER | SCALE(1-5)`
- **Pflicht**: `Ja/Nein`
- **Hinweis**: Antwortoptionen sind bei Choice-Typen angegeben (minimal, prototypisch)

---

## Block A – Erhebung / Context (6 Fragen)

### A1 – Ziel und Scope
- **ID:** CTX_01  
- **Frage:** Welches Ziel soll mit dem beschriebenen Use Case primär erreicht werden?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `Kosten senken | Durchlaufzeit reduzieren | Qualität/Fehler reduzieren | Transparenz/Steuerung verbessern | Compliance/Risiko senken | Umsatz/Service verbessern | Sonstiges`

### A2 – Prozess-/Fachbereich
- **ID:** CTX_02  
- **Frage:** In welchem Fachbereich bzw. Prozesskontext tritt der Use Case auf?  
- **Antworttyp:** TEXT  
- **Pflicht:** Ja  

### A3 – Prozessfrequenz
- **ID:** CTX_03  
- **Frage:** Wie häufig tritt der Use Case bzw. der zugrunde liegende Prozess typischerweise auf?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `Mehrmals täglich | Täglich | Wöchentlich | Monatlich | Seltener`

### A4 – Kritikalität
- **ID:** CTX_04  
- **Frage:** Wie kritisch ist der Use Case für Betrieb oder Wertschöpfung?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  
- **Skala:** `1 = gering … 5 = sehr hoch`

### A5 – Relevante Stakeholder/Rollen
- **ID:** CTX_05  
- **Frage:** Welche Rollen sind im Prozess wesentlich beteiligt oder betroffen?  
- **Antworttyp:** MULTI_CHOICE  
- **Pflicht:** Nein  
- **Optionen:** `Fachbereich | IT | Management | Controlling | Operations | Compliance | Externe Partner | Sonstige`

### A6 – Restriktionen (Zeit/Budget/Ressourcen)
- **ID:** CTX_06  
- **Frage:** Wie stark sind Zeit, Budget und interne Ressourcen für die Umsetzung eingeschränkt?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  
- **Skala:** `1 = kaum eingeschränkt … 5 = sehr stark eingeschränkt`

---

## Block B – Business Intelligence (10 Fragen)

### B1 – Datenquellen verfügbar
- **ID:** BI_01  
- **Frage:** Welche Datenquellen sind für den Use Case grundsätzlich verfügbar?  
- **Antworttyp:** MULTI_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `ERP | CRM | MES/Produktion | Ticketing/Service | Excel/Files | Data Warehouse | Cloud Apps | Sonstige`

### B2 – Datenzugriff
- **ID:** BI_02  
- **Frage:** Wie gut ist der Zugriff auf die benötigten Daten organisatorisch und technisch geregelt?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  
- **Skala:** `1 = ad hoc/unklar … 5 = klar geregelt/standardisiert`

### B3 – Datenqualität
- **ID:** BI_03  
- **Frage:** Wie bewerten Sie die Datenqualität für den Use Case (Vollständigkeit, Aktualität, Konsistenz)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### B4 – KPI-Definition
- **ID:** BI_04  
- **Frage:** Sind die für den Use Case relevanten Kennzahlen eindeutig definiert und dokumentiert?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `Nein | Teilweise | Ja`

### B5 – Reporting-Nutzung
- **ID:** BI_05  
- **Frage:** Wie werden Reports/Dashboards aktuell im Unternehmen genutzt?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Nein  
- **Optionen:** `Nicht vorhanden | Unregelmäßig/ad hoc | Regelmäßig, aber wenig standardisiert | Regelmäßig und standardisiert`

### B6 – Aktualitätsanforderung
- **ID:** BI_06  
- **Frage:** Welche Aktualität benötigen die Informationen für den Use Case typischerweise?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `Echtzeit/nahe Echtzeit | Stündlich | Täglich | Wöchentlich | Monatlich`

### B7 – Datenmodellierung/Standardisierung
- **ID:** BI_07  
- **Frage:** Wie standardisiert sind Datenmodelle/Definitionen (z. B. einheitliche Begriffe, Dimensionen, Stammdaten)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### B8 – Governance/Ownership
- **ID:** BI_08  
- **Frage:** Ist klar geregelt, wer für Daten, KPIs und Reports fachlich verantwortlich ist (Ownership)?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `Nein | Teilweise | Ja`

### B9 – Self-Service-Analytics
- **ID:** BI_09  
- **Frage:** In welchem Umfang wird Self-Service-Analytics durch Fachbereiche genutzt oder angestrebt?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Nein  
- **Skala:** `1 = nicht relevant … 5 = zentraler Bestandteil`

### B10 – Monitoring/Erfolgsmessung
- **ID:** BI_10  
- **Frage:** Wie etabliert ist ein Monitoring über KPIs zur Steuerung und Erfolgsmessung (z. B. definierte Zielwerte, regelmäßige Reviews)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

---

## Block C – Prozessautomatisierung (10 Fragen)

### C1 – Prozessdokumentation
- **ID:** PA_01  
- **Frage:** Wie gut ist der Prozess dokumentiert (Ablauf, Verantwortlichkeiten, Varianten)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### C2 – Standardisierung
- **ID:** PA_02  
- **Frage:** Wie stark ist der Prozess standardisiert (wenige Varianten, klare Regeln)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### C3 – Ausnahmen/Varianz
- **ID:** PA_03  
- **Frage:** Wie häufig treten Ausnahmen oder Sonderfälle im Prozess auf?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `Selten | Gelegentlich | Häufig | Sehr häufig`

### C4 – Regelbasiertheit
- **ID:** PA_04  
- **Frage:** In welchem Ausmaß sind Entscheidungen im Prozess regelbasiert und automatisierbar?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### C5 – Medienbrüche
- **ID:** PA_05  
- **Frage:** Wie stark ist der Prozess durch Medienbrüche geprägt (Excel, E-Mail, Copy-Paste, Papier)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  
- **Skala:** `1 = kaum … 5 = sehr stark`

### C6 – Systemlandschaft (intern)
- **ID:** PA_06  
- **Frage:** Über wie viele Systeme/Tools verteilt sich der Prozess typischerweise?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `1 | 2–3 | 4–5 | >5`

### C7 – Messbarkeit/Prozesskennzahlen
- **ID:** PA_07  
- **Frage:** Wie gut lässt sich der Prozess aktuell über Kennzahlen messen (Durchlaufzeit, Fehlerquote, SLA etc.)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### C8 – Kontroll-/Compliance-Anforderungen
- **ID:** PA_08  
- **Frage:** Wie hoch sind Kontroll- oder Compliance-Anforderungen im Prozess (Freigaben, Dokumentation, Audit)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Nein  

### C9 – Änderungsbereitschaft
- **ID:** PA_09  
- **Frage:** Wie hoch ist die Bereitschaft im Fachbereich, Prozessschritte zu standardisieren und zu verändern?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### C10 – Automatisierungserfahrung
- **ID:** PA_10  
- **Frage:** Welche Erfahrung besteht bereits mit Prozessautomatisierung (RPA/Workflow/Low-Code)?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Nein  
- **Optionen:** `Keine | Erste Piloten | Regelmäßig im Einsatz | Breite Nutzung/Center of Excellence`

---

## Block D – Synthese & Priorisierung (4 Fragen)

### D1 – Abhängigkeit BI ↔ Automatisierung
- **ID:** SYN_01  
- **Frage:** Wie stark hängen BI und Automatisierung im Use Case voneinander ab (z. B. Datenbasis als Voraussetzung für Automatisierung oder umgekehrt)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### D2 – Nutzenprioritäten
- **ID:** SYN_02  
- **Frage:** Welche Nutzenkriterien sind für die Priorisierung am wichtigsten?  
- **Antworttyp:** MULTI_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `Zeitersparnis | Kostensenkung | Qualitätssteigerung | Risiko/Compliance | Transparenz/Steuerung | Kundennutzen`

### D3 – Risikotoleranz
- **ID:** SYN_03  
- **Frage:** Wie hoch ist die Risikotoleranz für Pilotierung und Veränderung (Fehlertoleranz, Experimentierfreude)?  
- **Antworttyp:** SCALE(1-5)  
- **Pflicht:** Ja  

### D4 – Umsetzungszeitraum
- **ID:** SYN_04  
- **Frage:** In welchem Zeithorizont sollen erste messbare Ergebnisse vorliegen?  
- **Antworttyp:** SINGLE_CHOICE  
- **Pflicht:** Ja  
- **Optionen:** `< 1 Monat | 1–3 Monate | 3–6 Monate | 6–12 Monate | > 12 Monate`
