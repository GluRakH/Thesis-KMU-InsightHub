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
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    prompt_version: str = "v1"
    api_url: str = "https://api.openai.com/v1/chat/completions"
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
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            prompt_version=os.getenv("LLM_PROMPT_VERSION", "v1"),
            api_url=os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions"),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
            trace_file=Path(os.getenv("LLM_TRACE_FILE", "logs/llm_traces.jsonl")),
        )
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")

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
        return self._run_text_task("summarize_use_case", prompt, payload)

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
        return self._run_text_task("generate_assessment_rationale", prompt, payload)

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
        content = self._run_text_task("draft_measures", prompt, payload)

        try:
            parsed = json.loads(content)
            measures = parsed.get("measures", [])
            if isinstance(measures, list):
                cleaned = [str(item).strip() for item in measures if str(item).strip()]
                if cleaned:
                    return cleaned[:max_measures]
        except json.JSONDecodeError:
            pass

        return [line.strip("- •\t ") for line in content.splitlines() if line.strip()][:max_measures]

    def _run_text_task(self, task_name: str, prompt: str, payload: dict[str, Any]) -> str:
        input_hash = self._hash_payload(payload)
        timestamp = datetime.now(timezone.utc).isoformat()

        if self.dry_run or not self.api_key:
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
            output = self._call_api(prompt, payload)
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

    def _call_api(self, prompt: str, payload: dict[str, Any]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": "Du bist ein Assistenzmodell für nachvollziehbare, datensparsame KMU-Analysen.",
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nINPUT (JSON):\n{json.dumps(payload, ensure_ascii=False)}",
                },
            ],
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
        return str(response_payload["choices"][0]["message"]["content"]).strip()

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
        return "[Dummy] Kein Ergebnis verfügbar."
