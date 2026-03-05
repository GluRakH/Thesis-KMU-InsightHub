from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from domain.models import BIAssessment, PAAssessment


class MaturityThreshold(BaseModel):
    max: float
    level: int = Field(ge=1, le=5)
    label: str


class DimensionConfig(BaseModel):
    title: str
    questions: list[str]
    finding_templates: dict[str, str] = Field(default_factory=dict)


class QuestionScoringConfig(BaseModel):
    type: str
    map: dict[str, float] = Field(default_factory=dict)
    max: float | None = None


class AssessmentScoringConfig(BaseModel):
    assessment_type: str
    dimensions: dict[str, DimensionConfig]
    question_scoring: dict[str, QuestionScoringConfig]
    maturity_thresholds: list[MaturityThreshold]


class AssessmentResult(BaseModel):
    score: float
    maturity_level: int
    level_label: str
    dimension_scores: dict[str, float]
    dimension_levels: dict[str, str]
    findings: dict[str, str]
    critical_dimension_id: str = Field(default="")
    critical_dimension_severity: float = Field(default=0.0)
    critical_dimension_top_items: list[dict[str, Any]] = Field(default_factory=list)


class AssessmentService:
    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or Path(__file__).resolve().parents[1] / "config"
        self._question_meta = self._load_question_meta()


    def _load_question_meta(self) -> dict[str, tuple[float, float, str]]:
        path = self._config_dir / "questionnaire_v1.0.json"
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta: dict[str, tuple[float, float, str]] = {}
        for question in payload.get("questions", []):
            question_id = str(question.get("id") or "")
            if not question_id:
                continue
            scale = question.get("scale") or {}
            meta[question_id] = (float(scale.get("min", 1)), float(scale.get("max", 5)), str(question.get("direction") or "higher_is_better"))
        return meta

    @lru_cache(maxsize=8)
    def _load_scoring(self, area: str, version: str) -> AssessmentScoringConfig:
        path = self._config_dir / f"scoring_{area}_{version}.json"
        if not path.exists():
            raise ValueError(f"Scoring-Konfiguration '{path.name}' nicht gefunden.")

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        return AssessmentScoringConfig.model_validate(payload)

    def compute_bi_assessment(self, answer_set_id: str, answers: dict[str, Any], version: str = "v1.0") -> BIAssessment:
        result = self._compute(answers, self._load_scoring("bi", version))
        return BIAssessment(
            bi_assessment_id=f"bi-{uuid4().hex[:12]}",
            answer_set_id=answer_set_id,
            score=result.score,
            summary=f"BI-Reifegrad {result.maturity_level} ({result.level_label}) bei Score {result.score:.2f}.",
            maturity_level=result.maturity_level,
            level_label=result.level_label,
            dimension_scores=result.dimension_scores,
            dimension_levels=result.dimension_levels,
            findings=result.findings,
            critical_dimension_id=result.critical_dimension_id,
            critical_dimension_severity=result.critical_dimension_severity,
            critical_dimension_top_items=result.critical_dimension_top_items,
            questionnaire_version=version,
            scoring_version=version,
            model_version="assessment-rules-v1",
            prompt_version=f"scoring_{version}",
        )

    def compute_pa_assessment(self, answer_set_id: str, answers: dict[str, Any], version: str = "v1.0") -> PAAssessment:
        result = self._compute(answers, self._load_scoring("pa", version))
        return PAAssessment(
            pa_assessment_id=f"pa-{uuid4().hex[:12]}",
            answer_set_id=answer_set_id,
            score=result.score,
            summary=f"PA-Reifegrad {result.maturity_level} ({result.level_label}) bei Score {result.score:.2f}.",
            maturity_level=result.maturity_level,
            level_label=result.level_label,
            dimension_scores=result.dimension_scores,
            dimension_levels=result.dimension_levels,
            findings=result.findings,
            critical_dimension_id=result.critical_dimension_id,
            critical_dimension_severity=result.critical_dimension_severity,
            critical_dimension_top_items=result.critical_dimension_top_items,
            questionnaire_version=version,
            scoring_version=version,
            model_version="assessment-rules-v1",
            prompt_version=f"scoring_{version}",
        )

    def _compute(self, answers: dict[str, Any], config: AssessmentScoringConfig) -> AssessmentResult:
        dimension_scores: dict[str, float] = {}
        dimension_levels: dict[str, str] = {}
        findings: dict[str, str] = {}

        for dimension_id, dimension in config.dimensions.items():
            question_scores: list[float] = []
            for question_id in dimension.questions:
                score_config = config.question_scoring.get(question_id)
                if score_config is None or question_id not in answers:
                    continue

                question_scores.append(self._score_answer(answers[question_id], score_config))

            dimension_score = mean(question_scores) if question_scores else 0.0
            dimension_scores[dimension_id] = round(dimension_score, 2)
            _, dim_label = self._resolve_maturity(dimension_score, config.maturity_thresholds)
            dimension_levels[dimension_id] = dim_label

        overall_score = round(mean(dimension_scores.values()) if dimension_scores else 0.0, 2)
        maturity_level, level_label = self._resolve_maturity(overall_score, config.maturity_thresholds)

        for dimension_id, dimension in config.dimensions.items():
            dimension_label = dimension_levels.get(dimension_id, level_label)
            findings[dimension_id] = dimension.finding_templates.get(
                dimension_label,
                f"Dimension {dimension_id} bewertet als {dimension_label}.",
            )

        critical_dimension_id, critical_dimension_severity, critical_dimension_top_items = self._critical_dimension_evidence(answers, config, dimension_scores)

        return AssessmentResult(
            score=overall_score,
            maturity_level=maturity_level,
            level_label=level_label,
            dimension_scores=dimension_scores,
            dimension_levels=dimension_levels,
            findings=findings,
            critical_dimension_id=critical_dimension_id,
            critical_dimension_severity=critical_dimension_severity,
            critical_dimension_top_items=critical_dimension_top_items,
        )


    def _critical_dimension_evidence(
        self, answers: dict[str, Any], config: AssessmentScoringConfig, dimension_scores: dict[str, float]
    ) -> tuple[str, float, list[dict[str, Any]]]:
        if not dimension_scores:
            return "", 0.0, []
        critical_dimension_id = min(dimension_scores.items(), key=lambda item: item[1])[0]
        dimension = config.dimensions.get(critical_dimension_id)
        if dimension is None:
            return critical_dimension_id, 0.0, []

        top_items: list[dict[str, Any]] = []
        for question_id in dimension.questions:
            answer = answers.get(question_id)
            min_v, max_v, direction = self._question_meta.get(question_id, (1.0, 5.0, "higher_is_better"))
            deficit = self._deficit_score(answer, min_v, max_v, direction)
            if deficit is None:
                continue
            top_items.append({"item_id": question_id, "answer": answer, "deficit_score": deficit})
        top_items.sort(key=lambda item: item["deficit_score"], reverse=True)
        top_items = top_items[:3]
        severity = round(mean(item["deficit_score"] for item in top_items), 4) if top_items else 0.0
        return critical_dimension_id, severity, top_items

    @staticmethod
    def _deficit_score(answer: Any, min_value: float = 1.0, max_value: float = 5.0, direction: str = "higher_is_better") -> float | None:
        if max_value <= min_value:
            return None
        try:
            value = float(answer)
        except (TypeError, ValueError):
            return None

        normalized = (1 - ((value - min_value) / (max_value - min_value))) if direction == "higher_is_better" else ((value - min_value) / (max_value - min_value))
        return round(max(0.0, min(1.0, normalized)), 4)

    def _score_answer(self, answer: Any, score_config: QuestionScoringConfig) -> float:
        if score_config.type == "scale_minus_one":
            return float(max(0, int(answer) - 1))
        if score_config.type == "scale_reverse_5":
            return float(max(0, 5 - int(answer)))
        if score_config.type == "choice_map":
            return float(score_config.map.get(str(answer), 0.0))
        if score_config.type == "multi_count_minus_one_capped":
            count = len(answer) if isinstance(answer, list) else 0
            cap = score_config.max if score_config.max is not None else 4
            return float(max(0, min(cap, count - 1)))
        if score_config.type == "scale_to_100":
            value = float(answer)
            return round(max(0.0, min(100.0, ((value - 1.0) / 4.0) * 100.0)), 2)

        raise ValueError(f"Unbekannter Scoring-Typ: {score_config.type}")

    @staticmethod
    def _resolve_maturity(score: float, thresholds: list[MaturityThreshold]) -> tuple[int, str]:
        sorted_thresholds = sorted(thresholds, key=lambda item: item.max)
        for threshold in sorted_thresholds:
            if score <= threshold.max:
                return threshold.level, threshold.label

        top = sorted_thresholds[-1]
        return top.level, top.label
