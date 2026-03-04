from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import urllib.error
import urllib.request


@dataclass
class LLMClientConfig:
    model: str = "llama3.1:8b"
    temperature: float = 0.2
    prompt_version: str = "v1"
    api_url: str = "http://localhost:11434/api/generate"
    timeout_seconds: float = 20.0
    trace_file: Path = Path("logs/llm_traces.jsonl")


class LLMClient:
    def __init__(
        self,
        config: LLMClientConfig | None = None,
        api_key: str | None = None,
        dry_run: bool | None = None,
    ) -> None:
        self.config = config or LLMClientConfig(
            model=os.getenv("LLM_MODEL", "llama3.1:8b"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            prompt_version=os.getenv("LLM_PROMPT_VERSION", "v1"),
            api_url=os.getenv("LLM_API_URL", "http://localhost:11434/api/generate"),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
            trace_file=Path(os.getenv("LLM_TRACE_FILE", "logs/llm_traces.jsonl")),
        )
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY") or os.getenv("LLM_API_KEY")

        if dry_run is None:
            self.dry_run = os.getenv("LLM_DRY_RUN", "false").lower() == "true"
        else:
            self.dry_run = dry_run

    def summarize_use_case(
        self,
        company_context: str,
        bi_findings: dict[str, Any],
        pa_findings: dict[str, Any],
    ) -> str:
        payload = {
            "company_context": company_context,
            "bi_findings": bi_findings,
            "pa_findings": pa_findings,
        }
        prompt = (
            "Fasse den Use Case auf Deutsch in 5-7 Sätzen zusammen. "
            "Nenne Ausgangslage, wichtigste BI/PA-Befunde und den erwarteten Nutzen."
        )
        return self._run_text_task("summarize_use_case", prompt, payload, output_key="summary")

    def generate_assessment_rationale(
        self,
        assessment_type: str,
        score: float,
        maturity_level: int,
        dimension_scores: dict[str, float],
        findings: dict[str, str],
    ) -> str:
        payload = {
            "assessment_type": assessment_type,
            "score": score,
            "maturity_level": maturity_level,
            "dimension_scores": dimension_scores,
            "findings": findings,
        }
        prompt = (
            "Erkläre die Bewertung nachvollziehbar auf Deutsch. "
            "Begründe Reifegrad und Score auf Basis der Dimensionen und Findings."
        )
        return self._run_text_task("generate_assessment_rationale", prompt, payload, output_key="rationale")

    def draft_measures(
        self,
        focus_areas: list[str],
        constraints: list[str] | None = None,
        max_measures: int = 5,
    ) -> list[str]:
        payload = {
            "focus_areas": focus_areas,
            "constraints": constraints or [],
            "max_measures": max_measures,
        }
        prompt = (
            "Erstelle priorisierte, umsetzbare Maßnahmen auf Deutsch. "
            "Gib nur JSON zurück: {\"measures\": [\"...\"]}."
        )
        content = self._run_text_task("draft_measures", prompt, payload, output_key="measures")

        try:
            measures_payload = json.loads(content) if isinstance(content, str) else content
            if isinstance(measures_payload, dict):
                measures_payload = measures_payload.get("measures", [])
            if isinstance(measures_payload, list):
                cleaned = [str(item).strip() for item in measures_payload if str(item).strip()]
                if cleaned:
                    return cleaned[:max_measures]
        except json.JSONDecodeError:
            pass

        return [line.strip("- •\t ") for line in content.splitlines() if line.strip()][:max_measures]

    def summarize_measure_catalog(
        self,
        focus: str,
        measures_by_bucket: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        payload = {
            "focus": focus,
            "measures_by_bucket": measures_by_bucket,
        }
        prompt = (
            "Fasse den Maßnahmenkatalog auf Deutsch, übersichtlich und verständlich zusammen. "
            "Die Punkte in now/next/later sollen kurz, aber mit konkretem Nutzen formuliert sein. "
            "Ergänze zusätzlich pro Bucket eine knappe Anreicherung zu Deliverables und KPI. "
            "Gib nur JSON zurück mit den Feldern "
            "'headline', 'executive_summary', 'now', 'next', 'later', 'risks_and_dependencies', 'first_30_days', "
            "'measure_details'. "
            "'measure_details' muss ein Objekt mit den Buckets now/next/later sein; "
            "jede Liste enthält Objekte mit 'title', 'deliverables_summary', 'kpi_summary'."
        )
        content = self._run_text_task("summarize_measure_catalog", prompt, payload, output_key="catalog_summary")

        try:
            parsed = json.loads(content) if isinstance(content, str) else content
        except json.JSONDecodeError:
            parsed = {}

        if not isinstance(parsed, dict):
            parsed = {}

        return {
            "headline": str(parsed.get("headline") or "Ergebnis Maßnahmenkatalog"),
            "executive_summary": str(parsed.get("executive_summary") or "Keine Zusammenfassung verfügbar."),
            "now": [str(item) for item in parsed.get("now", [])][:3],
            "next": [str(item) for item in parsed.get("next", [])][:3],
            "later": [str(item) for item in parsed.get("later", [])][:3],
            "risks_and_dependencies": [str(item) for item in parsed.get("risks_and_dependencies", [])][:4],
            "first_30_days": [str(item) for item in parsed.get("first_30_days", [])][:4],
            "measure_details": self._normalize_measure_details(parsed.get("measure_details")),
        }

    @staticmethod
    def _normalize_measure_details(raw: Any) -> dict[str, list[dict[str, str]]]:
        default = {"now": [], "next": [], "later": []}
        if not isinstance(raw, dict):
            return default

        normalized: dict[str, list[dict[str, str]]] = {}
        for bucket in ("now", "next", "later"):
            entries = raw.get(bucket, [])
            if not isinstance(entries, list):
                normalized[bucket] = []
                continue

            bucket_items: list[dict[str, str]] = []
            for item in entries[:3]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                deliverables_summary = str(item.get("deliverables_summary") or "").strip()
                kpi_summary = str(item.get("kpi_summary") or "").strip()
                if title or deliverables_summary or kpi_summary:
                    bucket_items.append(
                        {
                            "title": title,
                            "deliverables_summary": deliverables_summary,
                            "kpi_summary": kpi_summary,
                        }
                    )
            normalized[bucket] = bucket_items

        return normalized

    def check_connection(self) -> dict[str, Any]:
        if self.dry_run:
            return {
                "ok": True,
                "mode": "dry_run",
                "api_url": self.config.api_url,
                "model": self.config.model,
                "message": "LLMClient läuft im Dry-Run-Modus; keine echte Ollama-Verbindung getestet.",
            }

        try:
            _ = self._call_api(
                prompt="Antworte mit einem kurzen Verbindungsstatus.",
                payload={"ping": "ping"},
                output_key="status",
            )
            return {
                "ok": True,
                "mode": "api",
                "api_url": self.config.api_url,
                "model": self.config.model,
                "message": "Ollama-Verbindung erfolgreich.",
            }
        except Exception as exc:
            return {
                "ok": False,
                "mode": "api",
                "api_url": self.config.api_url,
                "model": self.config.model,
                "message": f"Ollama-Verbindung fehlgeschlagen: {type(exc).__name__}: {exc}",
            }

    def _run_text_task(self, task_name: str, prompt: str, payload: dict[str, Any], output_key: str) -> str:
        input_hash = self._hash_payload(payload)
        timestamp = datetime.now(timezone.utc).isoformat()

        if self.dry_run:
            output = self._dummy_response(task_name, payload)
            self._write_trace(
                task_name=task_name,
                timestamp=timestamp,
                input_hash=input_hash,
                mode="dry_run",
                output_preview=output,
            )
            return output

        try:
            output = self._call_api(prompt, payload, output_key)
            self._write_trace(
                task_name=task_name,
                timestamp=timestamp,
                input_hash=input_hash,
                mode="api",
                output_preview=output,
            )
            return output
        except Exception as exc:
            output = self._dummy_response(task_name, payload)
            self._write_trace(
                task_name=task_name,
                timestamp=timestamp,
                input_hash=input_hash,
                mode="fallback",
                output_preview=output,
                error=f"{type(exc).__name__}: {exc}",
            )
            return output

    def _call_api(self, prompt: str, payload: dict[str, Any], output_key: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "model": self.config.model,
            "prompt": (
                "Du bist ein Assistenzmodell für nachvollziehbare, datensparsame KMU-Analysen. "
                f"{prompt}\n\n"
                f"Gib nur gültiges JSON zurück, das mindestens den Schlüssel '{output_key}' enthält.\n\n"
                f"INPUT (JSON):\n{json.dumps(payload, ensure_ascii=False)}"
            ),
            "stream": False,
            "format": "json",
            "options": {"temperature": self.config.temperature},
        }

        request = urllib.request.Request(
            self.config.api_url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM API HTTP {exc.code}: {detail}") from exc

        response_text = response_payload.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            raise RuntimeError("Ollama API lieferte kein Textfeld 'response'.")

        parsed_payload = json.loads(response_text)
        if output_key not in parsed_payload:
            raise RuntimeError(f"Ollama API lieferte kein Feld '{output_key}'.")

        field = parsed_payload[output_key]
        if isinstance(field, str):
            return field.strip()
        return json.dumps(field, ensure_ascii=False)

    def _write_trace(
        self,
        task_name: str,
        timestamp: str,
        input_hash: str,
        mode: str,
        output_preview: str | None = None,
        error: str | None = None,
    ) -> None:
        trace_record = {
            "timestamp": timestamp,
            "task": task_name,
            "prompt_version": self.config.prompt_version,
            "model": self.config.model,
            "temperature": self.config.temperature,
            "input_hash": input_hash,
            "mode": mode,
        }
        if output_preview:
            trace_record["output_preview"] = output_preview[:250]
        if error:
            trace_record["error"] = error[:250]

        self.config.trace_file.parent.mkdir(parents=True, exist_ok=True)
        with self.config.trace_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(trace_record, ensure_ascii=False) + "\n")

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        canonical_payload = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _dummy_response(task_name: str, payload: dict[str, Any]) -> str:
        if task_name == "summarize_use_case":
            return (
                "[Dummy] Das Unternehmen möchte BI und Predictive Analytics strukturiert ausbauen. "
                "Die bisherigen Befunde zeigen Handlungsbedarf bei Datenqualität, Prozessen und Kompetenzen. "
                "Durch gezielte Maßnahmen wird eine stabilere Entscheidungsgrundlage und höherer Geschäftsnutzen erwartet."
            )
        if task_name == "generate_assessment_rationale":
            return (
                f"[Dummy] Die Bewertung ergibt sich aus dem Zusammenspiel der Dimensionswerte. "
                f"Der ermittelte Reifegrad ist konsistent mit den dokumentierten Findings ({payload.get('assessment_type', 'Assessment')})."
            )
        if task_name == "draft_measures":
            focus_areas = payload.get("focus_areas", [])
            first_area = focus_areas[0] if focus_areas else "Datenmanagement"
            measures = [
                f"Priorität 1: Für {first_area} einen 90-Tage-Umsetzungsplan mit Verantwortlichen definieren.",
                "Priorität 2: KPI-Set für Wirkungsmessung der Maßnahmen einführen.",
                "Priorität 3: Monatliches Review mit Fachbereich und IT etablieren.",
            ]
            return json.dumps({"measures": measures}, ensure_ascii=False)
        if task_name == "summarize_measure_catalog":
            return json.dumps(
                {
                    "headline": "Ergebnis Maßnahmenkatalog",
                    "executive_summary": "[Dummy] Der Katalog priorisiert zuerst Basismaßnahmen mit hohem Hebel und reduziert so kurzfristig die größten Reifegradlücken.",
                    "now": [
                        "Governance-Grundlagen und Rollen verbindlich festlegen.",
                        "Datenqualitätsprobleme in den kritischsten Feldern systematisch beheben.",
                    ],
                    "next": ["Skalierbare Analytics-/Automations-Standards in den Fachbereichen ausrollen."],
                    "later": ["Erweiterte Use Cases nach stabiler Daten- und Prozessbasis schrittweise industrialisieren."],
                    "risks_and_dependencies": ["Abhängigkeit von Datenqualität und klarer Ownership vor technischen Ausbaustufen."],
                    "first_30_days": [
                        "Sponsor und Kernteam benennen.",
                        "Top-3-Maßnahmen in konkrete Arbeitspakete mit Verantwortlichen überführen.",
                    ],
                    "measure_details": {
                        "now": [
                            {
                                "title": "Governance-Grundlagen und Rollen verbindlich festlegen.",
                                "deliverables_summary": "Lieferobjekte: Rollenmodell, RACI und Governance-Board-Rhythmus.",
                                "kpi_summary": "KPI: Owner-Abdeckung >= 90% und Review-Teilnahmequote.",
                            }
                        ],
                        "next": [
                            {
                                "title": "Skalierbare Analytics-/Automations-Standards ausrollen.",
                                "deliverables_summary": "Lieferobjekte: Standard-Templates und verbindliche Qualitäts-Checks.",
                                "kpi_summary": "KPI: Anteil standardisierter Use Cases und reduzierte Durchlaufzeit.",
                            }
                        ],
                        "later": [],
                    },
                },
                ensure_ascii=False,
            )
        return "[Dummy] Kein Ergebnis verfügbar."
