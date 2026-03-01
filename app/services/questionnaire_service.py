from __future__ import annotations

import json
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    TEXT = "TEXT"
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTI_CHOICE = "MULTI_CHOICE"
    NUMBER = "NUMBER"
    SCALE = "SCALE"


class AnswerSetFinalizeStatus(str, Enum):
    VALIDATED = "VALIDATED"


class ScaleDefinition(BaseModel):
    min: int
    max: int


class QuestionDefinition(BaseModel):
    id: str
    text: str
    type: QuestionType
    required: bool = False
    options: list[str] = Field(default_factory=list)
    scale: ScaleDefinition | None = None


class QuestionnaireDefinition(BaseModel):
    version: str
    title: str
    questions: list[QuestionDefinition]


class ValidationIssue(BaseModel):
    question_id: str
    code: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class QuestionnaireService:
    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or Path(__file__).resolve().parents[1] / "config"

    @lru_cache(maxsize=16)
    def get_questionnaire(self, version: str) -> QuestionnaireDefinition:
        config_path = self._config_dir / f"questionnaire_{version}.json"
        if not config_path.exists():
            raise ValueError(f"Questionnaire version '{version}' not found.")

        with config_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        return QuestionnaireDefinition.model_validate(payload)

    def validate_answer_set(self, version: str, answer_set: dict[str, Any]) -> ValidationResult:
        questionnaire = self.get_questionnaire(version)
        issues: list[ValidationIssue] = []

        for question in questionnaire.questions:
            value = answer_set.get(question.id)

            if question.required and self._is_empty(value):
                issues.append(
                    ValidationIssue(
                        question_id=question.id,
                        code="REQUIRED_MISSING",
                        message="Pflichtfrage wurde nicht beantwortet.",
                    )
                )
                continue

            if self._is_empty(value):
                continue

            type_issue = self._validate_type(question, value)
            if type_issue:
                issues.append(type_issue)

        issues.extend(self._consistency_checks(answer_set))

        return ValidationResult(valid=len(issues) == 0, issues=issues)

    def finalize_answer_set(
        self,
        status: AnswerSetFinalizeStatus = AnswerSetFinalizeStatus.VALIDATED,
    ) -> dict[str, str]:
        return {"status": status.value}

    def _validate_type(self, question: QuestionDefinition, value: Any) -> ValidationIssue | None:
        if question.type == QuestionType.TEXT:
            if not isinstance(value, str) or not value.strip():
                return self._issue(question.id, "INVALID_TEXT", "Textantwort muss ein nicht-leerer String sein.")

        if question.type == QuestionType.NUMBER:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return self._issue(question.id, "INVALID_NUMBER", "Antwort muss eine Zahl sein.")

        if question.type == QuestionType.SCALE:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return self._issue(question.id, "INVALID_SCALE_TYPE", "Skalenwert muss numerisch sein.")
            if question.scale and not (question.scale.min <= value <= question.scale.max):
                return self._issue(
                    question.id,
                    "SCALE_OUT_OF_RANGE",
                    f"Skalenwert muss zwischen {question.scale.min} und {question.scale.max} liegen.",
                )

        if question.type == QuestionType.SINGLE_CHOICE:
            if not isinstance(value, str):
                return self._issue(question.id, "INVALID_SINGLE_CHOICE", "Antwort muss eine Option als String sein.")
            if question.options and value not in question.options:
                return self._issue(question.id, "UNKNOWN_OPTION", "Option ist nicht im Fragenkatalog enthalten.")

        if question.type == QuestionType.MULTI_CHOICE:
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return self._issue(
                    question.id,
                    "INVALID_MULTI_CHOICE",
                    "Antwort muss eine Liste von Optionen sein.",
                )
            if question.options and any(item not in question.options for item in value):
                return self._issue(
                    question.id,
                    "UNKNOWN_OPTION",
                    "Mindestens eine Option ist nicht im Fragenkatalog enthalten.",
                )

        return None

    def _consistency_checks(self, answer_set: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Hohe Governance-Reife bei gleichzeitig fehlender End-to-End-Verantwortung prüfen.
        if isinstance(answer_set.get("DA_03"), (int, float)) and isinstance(answer_set.get("COUP_03"), (int, float)):
            if answer_set["DA_03"] >= 4 and answer_set["COUP_03"] <= 2:
                issues.append(
                    self._issue(
                        "COUP_03",
                        "CONSISTENCY_WARNING",
                        "Hohe BI-Standardisierung bei niedriger End-to-End-Verantwortung sollte geprüft werden.",
                    )
                )

        # Hohe Automatisierungs-Skalierung bei niedriger Change-Bereitschaft prüfen.
        if isinstance(answer_set.get("PA_08"), (int, float)) and isinstance(answer_set.get("PA_02"), (int, float)):
            if answer_set["PA_08"] >= 4 and answer_set["PA_02"] <= 2:
                issues.append(
                    self._issue(
                        "PA_08",
                        "CONSISTENCY_WARNING",
                        "Geplante Skalierung steht im Widerspruch zu niedriger organisatorischer Readiness.",
                    )
                )

        return issues

    @staticmethod
    def _is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, list):
            return len(value) == 0
        return False

    @staticmethod
    def _issue(question_id: str, code: str, message: str) -> ValidationIssue:
        return ValidationIssue(question_id=question_id, code=code, message=message)
