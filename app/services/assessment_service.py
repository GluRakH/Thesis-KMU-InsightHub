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
    findings: dict[str, str]


class AssessmentService:
    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or Path(__file__).resolve().parents[1] / "config"

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
            findings=result.findings,
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
            findings=result.findings,
        )

    def _compute(self, answers: dict[str, Any], config: AssessmentScoringConfig) -> AssessmentResult:
        dimension_scores: dict[str, float] = {}
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

        overall_score = round(mean(dimension_scores.values()) if dimension_scores else 0.0, 2)
        maturity_level, level_label = self._resolve_maturity(overall_score, config.maturity_thresholds)

        for dimension_id, dimension in config.dimensions.items():
            findings[dimension_id] = dimension.finding_templates.get(
                level_label,
                f"Dimension {dimension_id} bewertet als {level_label}.",
            )

        return AssessmentResult(
            score=overall_score,
            maturity_level=maturity_level,
            level_label=level_label,
            dimension_scores=dimension_scores,
            findings=findings,
        )

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

        raise ValueError(f"Unbekannter Scoring-Typ: {score_config.type}")

    @staticmethod
    def _resolve_maturity(score: float, thresholds: list[MaturityThreshold]) -> tuple[int, str]:
        sorted_thresholds = sorted(thresholds, key=lambda item: item.max)
        for threshold in sorted_thresholds:
            if score <= threshold.max:
                return threshold.level, threshold.label

        top = sorted_thresholds[-1]
        return top.level, top.label
