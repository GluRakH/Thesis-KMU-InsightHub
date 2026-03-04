from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from adapters.llm_client import LLMClient
from app.services.initiative_templates import template_for_dimension
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
        del use_llm_texts  # 1.2.0 bleibt deterministisch ohne LLM-Texte.
        answers_payload = answers or {}
        scores = {**bi_dimension_scores, **pa_dimension_scores}
        levels = {**(bi_dimension_levels or {}), **(pa_dimension_levels or {})}
        if not levels:
            levels = {
                dimension: (bi_maturity_label if dimension.startswith("BI_") else pa_maturity_label)
                for dimension in scores
            }

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

            triggers = evidence_by_dimension.get(dimension, [])[:3]
            diagnosis = self._build_diagnosis(template.diagnosis_template, dimension, triggers)
            kpi_target = template.kpi_target_template.format(target_level=self._target_score(level, domain, target_level_by_domain or {}))

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
                    evidence={
                        "deficit_statement": self._build_deficit_statement(dimension, scores.get(dimension, 0.0)),
                        "trigger_items": triggers,
                        "severity": severity_by_dimension.get(dimension, 0.0),
                    },
                    priority={
                        "impact": float(impact),
                        "effort": float(effort),
                        "criticality_weight": criticality_weight,
                        "gap_weight": gap_weight,
                        "score": priority_score,
                    },
                    kpi={"name": template.kpi_name, "target": kpi_target, "measurement": template.kpi_measurement},
                    deliverables=list(template.deliverables),
                )
            )

        self._apply_governance_gate(measures, severity_by_dimension)
        self._apply_data_quality_gate(measures, severity_by_dimension)
        buckets = self._build_now_next_later(measures)
        ordered_ids = buckets["now"] + buckets["next"] + buckets["later"]
        order_map = {initiative_id: idx + 1 for idx, initiative_id in enumerate(ordered_ids)}
        bucket_map = {initiative_id: bucket for bucket, ids in buckets.items() for initiative_id in ids}
        for measure in measures:
            measure.suggested_priority = order_map.get(measure.initiative_id, 999)
            measure.priority["bucket"] = bucket_map.get(measure.initiative_id, "later")

        return MeasureCatalog(
            catalog_id=f"cat-{uuid4().hex[:12]}",
            title=f"Maßnahmenkatalog für {synthesis.answer_set_id}",
            status=CatalogStatus.DRAFT,
            synthesis_id=synthesis.synthesis_id,
            measures=sorted(measures, key=lambda item: item.suggested_priority),
            model_version="recommendation-v1.2.0",
            prompt_version="recommendation-v1.2.0",
        )

    @staticmethod
    def calculate_deficit_score(answer: Any, min_value: float = 1.0, max_value: float = 5.0) -> float | None:
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
        safe_effort = max(1, effort)
        return (impact / safe_effort) * criticality_weight * gap_weight

    def _extract_evidence_by_dimension(self, answers: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, float]]:
        evidence: dict[str, list[dict[str, Any]]] = {}
        severity_by_dimension: dict[str, float] = {}
        for scoring_path in (self._scoring_dir / "scoring_bi_v1.0.json", self._scoring_dir / "scoring_pa_v1.0.json"):
            if not scoring_path.exists():
                continue
            with scoring_path.open("r", encoding="utf-8") as handle:
                scoring_payload = json.load(handle)
            for dimension_id, dimension_meta in scoring_payload.get("dimensions", {}).items():
                items: list[dict[str, Any]] = []
                for question_id in dimension_meta.get("questions", []):
                    if question_id not in answers:
                        continue
                    min_v, max_v = self._question_meta.get(question_id, (1.0, 5.0))
                    deficit = self.calculate_deficit_score(answers.get(question_id), min_v, max_v)
                    if deficit is None:
                        continue
                    items.append({"item_id": question_id, "answer": answers.get(question_id), "deficit_score": deficit})

                items.sort(key=lambda x: x["deficit_score"], reverse=True)
                top_items = items[:3]
                evidence[dimension_id] = top_items
                if top_items:
                    severity_by_dimension[dimension_id] = round(sum(x["deficit_score"] for x in top_items) / len(top_items), 4)
                else:
                    severity_by_dimension[dimension_id] = 0.0
        return evidence, severity_by_dimension

    @staticmethod
    def _criticality_weights(dimension_scores: dict[str, float]) -> dict[str, float]:
        ordered = sorted(dimension_scores.items(), key=lambda item: item[1])
        weights: dict[str, float] = {}
        for rank, (dimension, _) in enumerate(ordered, start=1):
            if rank == 1:
                weights[dimension] = 1.30
            elif rank == 2:
                weights[dimension] = 1.15
            else:
                weights[dimension] = 1.0
        return weights

    @staticmethod
    def _gap_weight(level_label: str, domain: str, target_level_by_domain: dict[str, int]) -> float:
        defaults = {"BI": 3, "PA": 3}
        target = target_level_by_domain.get(domain, defaults.get(domain))
        if target is None:
            return 1.0
        try:
            current = int(level_label.replace("L", ""))
        except ValueError:
            return 1.0
        gap = max(0, target - current)
        return round(max(1.0, min(1.6, 1.0 + gap * 0.15)), 2)

    @staticmethod
    def _target_score(level_label: str, domain: str, target_level_by_domain: dict[str, int]) -> str:
        defaults = {"BI": 3, "PA": 3}
        target = target_level_by_domain.get(domain, defaults.get(domain))
        return f"L{target} (ausgehend von {level_label})" if target else ">= aktueller Baseline"

    @staticmethod
    def _build_initiative_id(domain: str, category: MeasureCategory, sequence: int) -> str:
        return f"INIT-{domain}-{category.value.upper()}-{sequence:02d}"

    @staticmethod
    def _domain_from_dimension(dimension: str) -> str:
        if dimension.startswith("BI_"):
            return "BI"
        if dimension.startswith("PA_"):
            return "PA"
        return "GLOBAL"

    def _select_triggers(self, bundle: DimensionTemplateBundle, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rules = bundle.template.evidence_rules
        preferred = [str(item) for item in rules.get("trigger_items_preferred", [])]
        threshold = float(rules.get("deficit_threshold", 0.0))

        preferred_items = [item for item in evidence if item["item_id"] in preferred and item["deficit_score"] >= threshold]
        if preferred_items:
            preferred_items.sort(key=lambda item: item["deficit_score"], reverse=True)
            return preferred_items[:3]
        return evidence[:3]

    @staticmethod
    def _domain_from_dimension(dimension: str) -> str:
        if dimension.startswith("BI_"):
            return "BI"
        if dimension.startswith("PA_"):
            return "PA"
        return "GLOBAL"

    @staticmethod
    def _build_diagnosis(template: str, dimension: str, triggers: list[dict[str, Any]]) -> str:
        if triggers:
            trigger_summary = ", ".join(
                f"{item['item_id']}={item['answer']} (deficit {item['deficit_score']:.2f})" for item in triggers[:3]
            )
        else:
            trigger_summary = "keine verwertbaren Trigger-Items"
        return template.format(dimension=dimension, trigger_summary=trigger_summary)

    @staticmethod
    def _governance_basics_missing(severity_by_dimension: dict[str, float], domain: str) -> bool:
        return severity_by_dimension.get(f"{domain}_D1", 0.0) > 0.6

    def _apply_governance_gate(self, measures: list[Measure], severity_by_dimension: dict[str, float]) -> None:
        governance_by_domain = {
            "BI": [m for m in measures if m.dimension.startswith("BI_") and m.category == MeasureCategory.GOVERNANCE],
            "PA": [m for m in measures if m.dimension.startswith("PA_") and m.category == MeasureCategory.GOVERNANCE],
        }
        for measure in measures:
            domain = self._domain_from_dimension(measure.dimension)
            if domain not in ("BI", "PA") or measure.category == MeasureCategory.GOVERNANCE:
                continue
            if not self._governance_basics_missing(severity_by_dimension, domain):
                continue
            governors = governance_by_domain.get(domain, [])
            if governors:
                dependency_id = governors[0].initiative_id
                if dependency_id not in measure.dependencies:
                    measure.dependencies.append(dependency_id)

    @staticmethod
    def _apply_data_quality_gate(measures: list[Measure], severity_by_dimension: dict[str, float]) -> None:
        dq_candidates = [m for m in measures if m.dimension == "BI_D2" and m.category == MeasureCategory.DATA]
        if not dq_candidates or severity_by_dimension.get("BI_D2", 0.0) <= 0.55:
            return
        dq_id = dq_candidates[0].initiative_id
        for measure in measures:
            if measure.initiative_id == dq_id:
                continue
            advanced = (
                measure.dimension in {"BI_D3", "PA_D3"}
                or (measure.category == MeasureCategory.TECHNICAL and measure.dimension in {"BI_D2", "PA_D2"})
            )
            if advanced and dq_id not in measure.dependencies:
                measure.dependencies.append(dq_id)

    @staticmethod
    def _build_now_next_later(measures: list[Measure]) -> dict[str, list[str]]:
        ordered = sorted(measures, key=lambda m: (-m.priority_score, m.initiative_id))
        buckets = {"now": [], "next": [], "later": []}
        domain_now_count = {"BI": 0, "PA": 0, "GLOBAL": 0}

        for measure in ordered:
            domain = RecommendationService._domain_from_dimension(measure.dimension)
            deps = [dep for dep in measure.dependencies if dep.startswith("INIT-")]
            deps_in_now = all(dep in buckets["now"] for dep in deps)
            if len(buckets["now"]) < 4 and domain_now_count.get(domain, 0) < 2 and deps_in_now:
                buckets["now"].append(measure.initiative_id)
                domain_now_count[domain] = domain_now_count.get(domain, 0) + 1

        for measure in ordered:
            if measure.initiative_id in buckets["now"]:
                continue
            deps = [dep for dep in measure.dependencies if dep.startswith("INIT-")]
            if all(dep in buckets["now"] for dep in deps):
                buckets["next"].append(measure.initiative_id)
            else:
                buckets["later"].append(measure.initiative_id)

        return buckets

    def _load_question_meta(self) -> dict[str, tuple[float, float]]:
        path = self._scoring_dir / "questionnaire_v1.0.json"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        result: dict[str, tuple[float, float]] = {}
        for question in payload.get("questions", []):
            q_id = question.get("id")
            scale = question.get("scale") or {}
            if not q_id:
                continue
            result[str(q_id)] = (float(scale.get("min", 1)), float(scale.get("max", 5)))
        return result
