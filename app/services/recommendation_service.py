from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from adapters.llm_client import LLMClient
from app.services.initiative_templates import TEMPLATE_VERSION, template_for_dimension
from domain.models import CatalogStatus, Measure, MeasureCatalog, MeasureCategory, Synthesis


class RecommendationService:
    def __init__(
        self,
        config_path: Path | None = None,
        llm_client: LLMClient | None = None,
        scoring_dir: Path | None = None,
    ) -> None:
        self._llm_client = llm_client or LLMClient(dry_run=True)
        self._config_path = config_path or Path("app/config/recommendation_catalog_v1.0.json")
        self._scoring_dir = scoring_dir or Path("app/config")
        self._question_meta = self._load_question_meta()
        self._dimension_questions = self._load_dimension_questions()
        self.last_rules_applied: dict[str, Any] = {"gates": [], "thresholds": {}}

    def generate_catalog(
        self,
        synthesis: Synthesis,
        bi_maturity_label: str,
        pa_maturity_label: str,
        bi_dimension_scores: dict[str, float],
        pa_dimension_scores: dict[str, float],
        bi_dimension_levels: dict[str, str] | None = None,
        pa_dimension_levels: dict[str, str] | None = None,
        use_llm_texts: bool = False,
        answers: dict[str, Any] | None = None,
        target_level_by_domain: dict[str, int] | None = None,
    ) -> MeasureCatalog:
        del use_llm_texts
        answers_payload = answers or {}
        scores = {**bi_dimension_scores, **pa_dimension_scores}
        levels = {**(bi_dimension_levels or {}), **(pa_dimension_levels or {})}
        if not levels:
            levels = {dimension: (bi_maturity_label if dimension.startswith("BI_") else pa_maturity_label) for dimension in scores}

        evidence_by_dimension, severity_by_dimension = self._extract_evidence_by_dimension(answers_payload)
        critical_weights = self._criticality_weights(scores)

        ranked_dimensions = sorted(scores.items(), key=lambda item: item[1])
        measures: list[Measure] = []
        sequence_by_domain: dict[str, int] = {"BI": 0, "PA": 0, "GLOBAL": 0}

        for dimension, _ in ranked_dimensions:
            template = template_for_dimension(dimension)
            level = levels.get(dimension, "L1")
            domain = self._domain_from_dimension(dimension)
            sequence_by_domain[domain] = sequence_by_domain.get(domain, 0) + 1
            initiative_id = self._build_initiative_id(domain, template.category, sequence_by_domain[domain])

            impact = max(1, int(template.impact))
            effort = max(1, int(template.effort))
            criticality_weight = critical_weights.get(dimension, 1.0)
            gap_weight = self._gap_weight(level, domain, target_level_by_domain or {})
            priority_score = self.calculate_priority_score(impact, effort, criticality_weight, gap_weight)

            triggers = self._normalize_trigger_items(dimension, evidence_by_dimension.get(dimension, []), answers_payload)
            diagnosis = self._build_diagnosis(template.diagnosis_template, dimension, triggers)
            kpi_target = template.kpi_target_template.format(target_level=self._target_score(level, domain, target_level_by_domain or {}))

            evidence = {
                "dimension_id": dimension,
                "severity": severity_by_dimension.get(dimension, 0.0),
                "trigger_items": triggers,
                "rationale": self._build_rationale(dimension, triggers),
                "deficit_statement": self._build_deficit_statement(dimension, scores.get(dimension, 0.0)),
            }
            kpi = {
                "name": template.kpi_name,
                "target": kpi_target,
                "measurement": template.kpi_measurement,
                "frequency": template.kpi_frequency,
                "source_system": template.kpi_source_system,
                "owner_role": template.kpi_owner_role,
            }

            measures.append(
                Measure(
                    measure_id=f"mea-{uuid4().hex[:12]}",
                    initiative_id=initiative_id,
                    title=template.title,
                    description=diagnosis,
                    category=template.category,
                    dimension=dimension,
                    maturity_label=level,
                    measure_class=template.template_id,
                    impact=impact,
                    effort=effort,
                    priority_score=priority_score,
                    prerequisites=[],
                    dependencies=[],
                    suggested_priority=1,
                    goal=template.goal,
                    evidence=evidence,
                    priority={
                        "impact": float(impact),
                        "effort": float(effort),
                        "criticality_weight": criticality_weight,
                        "gap_weight": gap_weight,
                        "score": priority_score,
                    },
                    kpi=kpi,
                    deliverables=list(template.deliverables),
                    prompt_version=template.template_version,
                )
            )

        rules_applied = {"gates": [], "thresholds": {"governance": 0.6, "data_quality": 0.55}, "dependencies": []}
        self._apply_governance_gate(measures, severity_by_dimension, rules_applied)
        self._apply_data_quality_gate(measures, severity_by_dimension, rules_applied)

        buckets = self._build_now_next_later(measures)
        ordered_ids = buckets["now"] + buckets["next"] + buckets["later"]
        order_map = {initiative_id: idx + 1 for idx, initiative_id in enumerate(ordered_ids)}
        bucket_map = {initiative_id: bucket for bucket, ids in buckets.items() for initiative_id in ids}
        for measure in measures:
            measure.suggested_priority = order_map.get(measure.initiative_id, 999)
            bucket = bucket_map.get(measure.initiative_id, "later")
            measure.priority["bucket"] = bucket
            measure.priority["rank"] = float(measure.suggested_priority)
            measure.priority["sequence_reason"] = self._sequence_reason(measure, rules_applied)
            measure.evidence["template_id"] = measure.measure_class
            measure.evidence["template_version"] = measure.prompt_version

        self.last_rules_applied = rules_applied

        return MeasureCatalog(
            catalog_id=f"cat-{uuid4().hex[:12]}",
            title=f"Maßnahmenkatalog für {synthesis.answer_set_id}",
            status=CatalogStatus.DRAFT,
            synthesis_id=synthesis.synthesis_id,
            measures=sorted(measures, key=lambda item: item.suggested_priority),
            model_version="recommendation-v1.3.0",
            prompt_version=f"templates-{TEMPLATE_VERSION}",
        )

    @staticmethod
    def calculate_deficit_score(answer: Any, min_value: float, max_value: float) -> float | None:
        if answer is None:
            return None
        if max_value <= min_value:
            return None
        try:
            value = float(answer)
        except (TypeError, ValueError):
            return None
        normalized = 1 - ((value - min_value) / (max_value - min_value))
        return round(max(0.0, min(1.0, normalized)), 4)

    @staticmethod
    def calculate_priority_score(impact: int, effort: int, criticality_weight: float, gap_weight: float) -> float:
        return (impact / max(1, effort)) * criticality_weight * gap_weight

    def _extract_evidence_by_dimension(self, answers: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, float]]:
        evidence: dict[str, list[dict[str, Any]]] = {}
        severity_by_dimension: dict[str, float] = {}
        for dimension_id, questions in self._dimension_questions.items():
            items: list[dict[str, Any]] = []
            for question_id in questions:
                if question_id not in answers:
                    continue
                min_v, max_v = self._question_meta.get(question_id, (1.0, 5.0))
                deficit = self.calculate_deficit_score(answers.get(question_id), min_v, max_v)
                if deficit is None:
                    continue
                items.append(
                    {
                        "item_id": question_id,
                        "answer": answers.get(question_id),
                        "deficit_score": deficit,
                        "label": question_id,
                    }
                )
            items.sort(key=lambda x: x["deficit_score"], reverse=True)
            top_items = items[:3]
            evidence[dimension_id] = top_items
            severity_by_dimension[dimension_id] = round(sum(x["deficit_score"] for x in top_items) / len(top_items), 4) if top_items else 0.0
        return evidence, severity_by_dimension

    def _normalize_trigger_items(self, dimension: str, items: list[dict[str, Any]], answers: dict[str, Any]) -> list[dict[str, Any]]:
        selected = list(items[:3])
        for question_id in self._dimension_questions.get(dimension, []):
            if len(selected) >= 2:
                break
            if any(item["item_id"] == question_id for item in selected):
                continue
            deficit = self.calculate_deficit_score(answers.get(question_id), *self._question_meta.get(question_id, (1.0, 5.0))) or 0.0
            selected.append({"item_id": question_id, "answer": answers.get(question_id), "deficit_score": deficit, "label": question_id})
        return selected[:3]

    @staticmethod
    def _build_rationale(dimension: str, triggers: list[dict[str, Any]]) -> str:
        refs = ", ".join(f"{item['item_id']} ({item['deficit_score']:.2f})" for item in triggers[:3]) or "keine Trigger"
        return f"Für {dimension} priorisiert, weil die höchsten Defizite in {refs} liegen."

    @staticmethod
    def _criticality_weights(dimension_scores: dict[str, float]) -> dict[str, float]:
        ordered = sorted(dimension_scores.items(), key=lambda item: item[1])
        return {dimension: (1.30 if rank == 1 else 1.15 if rank == 2 else 1.0) for rank, (dimension, _) in enumerate(ordered, start=1)}

    @staticmethod
    def _gap_weight(level_label: str, domain: str, target_level_by_domain: dict[str, int]) -> float:
        target = target_level_by_domain.get(domain, {"BI": 3, "PA": 3}.get(domain))
        if target is None:
            return 1.0
        try:
            current = int(level_label.replace("L", ""))
        except ValueError:
            return 1.0
        return round(max(1.0, min(1.6, 1.0 + max(0, target - current) * 0.15)), 2)

    @staticmethod
    def _target_score(level_label: str, domain: str, target_level_by_domain: dict[str, int]) -> str:
        target = target_level_by_domain.get(domain, {"BI": 3, "PA": 3}.get(domain))
        return f"L{target} (ausgehend von {level_label})" if target else ">= aktueller Baseline"

    @staticmethod
    def _build_initiative_id(domain: str, category: MeasureCategory, sequence: int) -> str:
        return f"INIT-{domain}-{category.value.upper()}-{sequence:02d}"

    @staticmethod
    def _domain_from_dimension(dimension: str) -> str:
        return "BI" if dimension.startswith("BI_") else "PA" if dimension.startswith("PA_") else "GLOBAL"

    @staticmethod
    def _build_diagnosis(template: str, dimension: str, triggers: list[dict[str, Any]]) -> str:
        trigger_summary = ", ".join(f"{item['item_id']}={item['answer']} (deficit {item['deficit_score']:.2f})" for item in triggers[:3]) or "keine verwertbaren Trigger-Items"
        return template.format(dimension=dimension, trigger_summary=trigger_summary)

    @staticmethod
    def _build_deficit_statement(dimension: str, dimension_score: float) -> str:
        severity = "hoher" if dimension_score < 35 else "mittlerer" if dimension_score < 60 else "geringer"
        return f"{severity.capitalize()} Handlungsbedarf in {dimension} (Score: {dimension_score:.1f})."

    def _apply_governance_gate(self, measures: list[Measure], severity_by_dimension: dict[str, float], rules_applied: dict[str, Any]) -> None:
        for domain in ("BI", "PA"):
            if severity_by_dimension.get(f"{domain}_D1", 0.0) <= 0.6:
                continue
            gov = next((m for m in measures if m.dimension.startswith(domain) and m.category == MeasureCategory.GOVERNANCE), None)
            if not gov:
                continue
            impacted = []
            for measure in measures:
                if measure.category == MeasureCategory.GOVERNANCE or not measure.dimension.startswith(domain):
                    continue
                if gov.initiative_id not in measure.dependencies:
                    measure.dependencies.append(gov.initiative_id)
                    impacted.append(measure.initiative_id)
            rules_applied["gates"].append({"rule": "governance_first", "domain": domain, "blocking_measure": gov.initiative_id, "affected_measures": impacted})
            rules_applied["dependencies"].extend({"from": gov.initiative_id, "to": item} for item in impacted)

    @staticmethod
    def _apply_data_quality_gate(measures: list[Measure], severity_by_dimension: dict[str, float], rules_applied: dict[str, Any]) -> None:
        dq = next((m for m in measures if m.dimension == "BI_D2"), None)
        if not dq or severity_by_dimension.get("BI_D2", 0.0) <= 0.55:
            return
        impacted = []
        for measure in measures:
            if measure.initiative_id == dq.initiative_id:
                continue
            advanced = measure.dimension in {"BI_D3", "PA_D3"} or (measure.category == MeasureCategory.TECHNICAL and measure.dimension in {"BI_D2", "PA_D2"})
            if advanced and dq.initiative_id not in measure.dependencies:
                measure.dependencies.append(dq.initiative_id)
                impacted.append(measure.initiative_id)
        rules_applied["gates"].append({"rule": "data_quality_first", "domain": "BI", "blocking_measure": dq.initiative_id, "affected_measures": impacted})
        rules_applied["dependencies"].extend({"from": dq.initiative_id, "to": item} for item in impacted)

    @staticmethod
    def _build_now_next_later(measures: list[Measure]) -> dict[str, list[str]]:
        ordered = sorted(measures, key=lambda m: (-m.priority_score, m.initiative_id))
        buckets = {"now": [], "next": [], "later": []}
        for measure in ordered:
            deps = [dep for dep in measure.dependencies if dep.startswith("INIT-")]
            if not deps and len(buckets["now"]) < 4:
                buckets["now"].append(measure.initiative_id)
            elif all(dep in buckets["now"] for dep in deps):
                buckets["next"].append(measure.initiative_id)
            else:
                buckets["later"].append(measure.initiative_id)
        return buckets

    @staticmethod
    def _sequence_reason(measure: Measure, rules_applied: dict[str, Any]) -> str:
        for gate in rules_applied.get("gates", []):
            if measure.initiative_id in gate.get("affected_measures", []):
                if gate.get("rule") == "governance_first":
                    return "Governance vor Skalierung"
                if gate.get("rule") == "data_quality_first":
                    return "Data Quality vor Industrialisierung"
        return "Keine aktive Gate-Blockade"

    def _load_question_meta(self) -> dict[str, tuple[float, float]]:
        path = self._scoring_dir / "questionnaire_v1.0.json"
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            str(question.get("id")): (float((question.get("scale") or {}).get("min", 1)), float((question.get("scale") or {}).get("max", 5)))
            for question in payload.get("questions", [])
            if question.get("id")
        }

    def _load_dimension_questions(self) -> dict[str, list[str]]:
        dimensions: dict[str, list[str]] = {}
        for name in ("scoring_bi_v1.0.json", "scoring_pa_v1.0.json"):
            path = self._scoring_dir / name
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            for dimension_id, meta in payload.get("dimensions", {}).items():
                dimensions[str(dimension_id)] = [str(item) for item in meta.get("questions", [])]
        return dimensions
