from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class UseCaseType(str, Enum):
    BUSINESS_IMPACT = "business_impact"
    PROCESS_AUTOMATION = "process_automation"
    COMBINED = "combined"


class AnswerSetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    LOCKED = "locked"


class CatalogStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class MeasureCategory(str, Enum):
    ORGANIZATIONAL = "organizational"
    TECHNICAL = "technical"
    GOVERNANCE = "governance"
    DATA = "data"


class VersionedModel(BaseModel):
    model_version: str = Field(default="1.0.0")
    prompt_version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UseCase(VersionedModel):
    use_case_id: str
    name: str
    description: str
    use_case_type: UseCaseType


class Questionnaire(VersionedModel):
    questionnaire_id: str
    use_case_id: str
    title: str
    questionnaire_version: str


class Question(VersionedModel):
    question_id: str
    questionnaire_id: str
    text: str
    order: int = Field(ge=1)


class AnswerSet(VersionedModel):
    answer_set_id: str
    questionnaire_id: str
    status: AnswerSetStatus = Field(default=AnswerSetStatus.DRAFT)


class Answer(VersionedModel):
    answer_id: str
    answer_set_id: str
    question_id: str
    value: str


class BIAssessment(VersionedModel):
    bi_assessment_id: str
    answer_set_id: str
    score: float = Field(ge=0)
    summary: str
    maturity_level: int = Field(default=1, ge=1, le=5)
    level_label: str = Field(default="LOW")
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    findings: dict[str, str] = Field(default_factory=dict)


class PAAssessment(VersionedModel):
    pa_assessment_id: str
    answer_set_id: str
    score: float = Field(ge=0)
    summary: str
    maturity_level: int = Field(default=1, ge=1, le=5)
    level_label: str = Field(default="LOW")
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    findings: dict[str, str] = Field(default_factory=dict)


class Synthesis(VersionedModel):
    synthesis_id: str
    bi_assessment_id: str
    pa_assessment_id: str
    recommendation: str


class Measure(VersionedModel):
    measure_id: str
    title: str
    description: str
    category: MeasureCategory


class MeasureCatalog(VersionedModel):
    catalog_id: str
    title: str
    status: CatalogStatus
    measures: list[Measure] = Field(default_factory=list)


class UserSelection(VersionedModel):
    user_selection_id: str
    synthesis_id: str
    selected_measure_ids: list[str] = Field(default_factory=list)
