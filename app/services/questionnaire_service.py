from __future__ import annotations

import json
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    TEXT = "text"
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    NUMBER = "number"
    LIKERT = "likert"


class ValidationStage(str, Enum):
    DRAFT = "draft"
    FINALIZE = "finalize"


class ScaleDefinition(BaseModel):
    min: int
    max: int


class QuestionDefinition(BaseModel):
    id: str
    text: str
    answer_type: QuestionType
    type: str | None = None
    required: bool = False
    options: list[str] = Field(default_factory=list)
    scale: ScaleDefinition | None = None
    direction: str | None = None
    dimension_id: str | None = None


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
    normalized_answers: dict[str, Any] = Field(default_factory=dict)


class QuestionnaireService:
    def __init__(self, config_dir: Path | None = None, schemas_dir: Path | None = None, dev_mode: bool = True) -> None:
        self._config_dir = config_dir or Path(__file__).resolve().parents[1] / "config"
        self._schemas_dir = schemas_dir or Path(__file__).resolve().parents[2] / "schemas"
        self._dev_mode = dev_mode

    @lru_cache(maxsize=8)
    def _schema_validator(self, schema_name: str) -> Draft202012Validator:
        payload = json.loads((self._schemas_dir / schema_name).read_text(encoding="utf-8"))
        return Draft202012Validator(payload)

    @staticmethod
    def _to_semver(version: str) -> str:
        cleaned = version.strip().lstrip("v")
        if cleaned.count(".") == 1:
            return f"{cleaned}.0"
        return cleaned

    def _canonicalize_questionnaire(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "questionnaire_version" in payload and "questions" in payload:
            return payload

        questions: list[dict[str, Any]] = []
        for item in payload.get("questions", []):
            q_type = str(item.get("answer_type") or item.get("type", "")).lower()
            answer_type = {"scale": "likert", "text": "text", "single_choice": "single_choice", "multi_choice": "multi_choice", "number": "number"}.get(q_type, q_type)
            question_id = str(item.get("id", ""))
            prefix = question_id.split("_", 1)[0]
            default_dimension = {"CTX": "CTX", "COUP": "COUP", "SYN": "SYN", "DA": "BI_D2", "PA": "PA_D2"}.get(prefix, "CTX")
            dimension_id = str(item.get("dimension_id") or default_dimension)
            question_payload = {
                "id": question_id,
                "text": item.get("text"),
                "answer_type": answer_type,
                "required": bool(item.get("required", False)),
                "dimension_id": dimension_id,
            }
            direction = item.get("direction") or ("higher_is_better" if answer_type in {"likert", "single_choice", "multi_choice"} else None)
            if direction is not None:
                question_payload["direction"] = direction
            if item.get("scale") is not None:
                question_payload["scale"] = item.get("scale")
            if item.get("options") is not None:
                question_payload["options"] = item.get("options")
            questions.append(question_payload)

        return {
            "schema_version": str(payload.get("schema_version", "1.0.0")),
            "questionnaire_version": self._to_semver(str(payload.get("questionnaire_version") or payload.get("version", "1.0.0"))),
            "questions": questions,
        }

    @lru_cache(maxsize=16)
    def get_questionnaire(self, version: str) -> QuestionnaireDefinition:
        config_path = self._config_dir / f"questionnaire_{version}.json"
        if not config_path.exists():
            raise ValueError(f"Questionnaire version '{version}' not found.")

        payload = json.loads(config_path.read_text(encoding="utf-8"))
        canonical = self._canonicalize_questionnaire(payload)

        errors = sorted(self._schema_validator("questionnaire.schema.json").iter_errors(canonical), key=lambda e: e.path)
        if errors:
            raise ValueError(f"Questionnaire schema validation failed: {errors[0].message}")

        ids = [str(question.get("id")) for question in canonical.get("questions", [])]
        if len(ids) != len(set(ids)):
            raise ValueError("Questionnaire enthält doppelte question IDs.")

        for question in canonical.get("questions", []):
            if question.get("answer_type") == "likert" and (not question.get("direction") or not isinstance(question.get("scale"), dict)):
                raise ValueError(f"Likert Frage '{question.get('id')}' benötigt direction und scale.")
            if question.get("answer_type") in {"likert", "single_choice", "multi_choice"} and not question.get("direction"):
                if self._dev_mode:
                    raise ValueError(f"Frage '{question.get('id')}' benötigt direction.")

        return QuestionnaireDefinition(
            version=version,
            title=str(payload.get("title", "Questionnaire")),
            questions=[QuestionDefinition.model_validate({**question, "type": {"likert": "SCALE", "single_choice": "SINGLE_CHOICE", "multi_choice": "MULTI_CHOICE", "text": "TEXT", "number": "NUMBER"}.get(str(question.get("answer_type")), str(question.get("answer_type", "")).upper())}) for question in canonical.get("questions", [])],
        )

    def validate_answer_set(self, version: str, answer_set: dict[str, Any], stage: ValidationStage = ValidationStage.FINALIZE) -> ValidationResult:
        questionnaire = self.get_questionnaire(version)
        issues: list[ValidationIssue] = []
        normalized: dict[str, Any] = {}

        wrapped = {
            "schema_version": "1.0.0",
            "questionnaire_version": self._to_semver(version),
            "answers": answer_set,
        }
        schema_errors = sorted(self._schema_validator("answerset.schema.json").iter_errors(wrapped), key=lambda e: e.path)
        if schema_errors:
            return ValidationResult(valid=False, issues=[self._issue("answers", "SCHEMA_INVALID", schema_errors[0].message)], normalized_answers={})

        lookup = {question.id: question for question in questionnaire.questions}

        for question_id in answer_set:
            if question_id not in lookup:
                issues.append(self._issue(question_id, "UNKNOWN_QUESTION", "Frage-ID ist im Fragenkatalog nicht vorhanden."))

        for question in questionnaire.questions:
            raw_value = answer_set.get(question.id, None)
            value, issue = self._normalize_and_validate_answer(question, raw_value, stage)
            if issue:
                issues.append(issue)
            normalized[question.id] = value

        issues.extend(self._consistency_checks(normalized))
        return ValidationResult(valid=len(issues) == 0, issues=issues, normalized_answers=normalized)

    def _normalize_and_validate_answer(
        self,
        question: QuestionDefinition,
        value: Any,
        stage: ValidationStage,
    ) -> tuple[Any, ValidationIssue | None]:
        if value is None:
            if stage == ValidationStage.FINALIZE and question.required:
                return None, self._issue(question.id, "REQUIRED_MISSING", "Pflichtfrage wurde nicht beantwortet.")
            return None, None

        if question.answer_type == QuestionType.LIKERT:
            normalized = int(value) if isinstance(value, str) and value.strip().isdigit() else value
            if not isinstance(normalized, int) or isinstance(normalized, bool):
                return None, self._issue(question.id, "INVALID_LIKERT_TYPE", "Likert Antwort muss int sein.")
            if question.scale and not (question.scale.min <= normalized <= question.scale.max):
                return None, self._issue(question.id, "SCALE_OUT_OF_RANGE", "Likert Antwort außerhalb der Skala.")
            return normalized, None

        if question.answer_type == QuestionType.SINGLE_CHOICE:
            if not isinstance(value, str):
                return None, self._issue(question.id, "INVALID_SINGLE_CHOICE", "Antwort muss String sein.")
            if value not in question.options:
                return None, self._issue(question.id, "UNKNOWN_OPTION", "Option ist nicht im Fragenkatalog enthalten.")
            return value, None

        if question.answer_type == QuestionType.MULTI_CHOICE:
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return None, self._issue(question.id, "INVALID_MULTI_CHOICE", "Antwort muss String-Liste sein.")
            if len(value) != len(set(value)):
                return None, self._issue(question.id, "DUPLICATE_MULTI_CHOICE", "Mehrfachauswahl muss unique sein.")
            if any(item not in question.options for item in value):
                return None, self._issue(question.id, "UNKNOWN_OPTION", "Mindestens eine Option ist unbekannt.")
            return value, None

        if question.answer_type == QuestionType.TEXT:
            if not isinstance(value, str):
                return None, self._issue(question.id, "INVALID_TEXT", "Textantwort muss String sein.")
            trimmed = value.strip()
            normalized = trimmed or None
            if normalized is None and stage == ValidationStage.FINALIZE and question.required:
                return None, self._issue(question.id, "REQUIRED_MISSING", "Pflichtfrage wurde nicht beantwortet.")
            return normalized, None

        if question.answer_type == QuestionType.NUMBER:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return None, self._issue(question.id, "INVALID_NUMBER", "Antwort muss Zahl sein.")
            return value, None

        return None, self._issue(question.id, "UNKNOWN_ANSWER_TYPE", "Unbekannter Fragetyp.")

    def _consistency_checks(self, answer_set: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if isinstance(answer_set.get("DA_03"), (int, float)) and isinstance(answer_set.get("COUP_03"), (int, float)):
            if answer_set["DA_03"] >= 4 and answer_set["COUP_03"] <= 2:
                issues.append(self._issue("COUP_03", "CONSISTENCY_WARNING", "Hohe BI-Standardisierung bei niedriger End-to-End-Verantwortung sollte geprüft werden."))
        if isinstance(answer_set.get("PA_08"), (int, float)) and isinstance(answer_set.get("PA_02"), (int, float)):
            if answer_set["PA_08"] >= 4 and answer_set["PA_02"] <= 2:
                issues.append(self._issue("PA_08", "CONSISTENCY_WARNING", "Geplante Skalierung steht im Widerspruch zu niedriger organisatorischer Readiness."))
        return issues

    @staticmethod
    def _issue(question_id: str, code: str, message: str) -> ValidationIssue:
        return ValidationIssue(question_id=question_id, code=code, message=message)
