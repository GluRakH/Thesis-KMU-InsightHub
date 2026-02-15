from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from domain.models import AnswerSetStatus, CatalogStatus, MeasureCategory, UseCaseType
from persistence.database import Base


class TimestampVersionMixin:
    model_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class UseCaseEntity(TimestampVersionMixin, Base):
    __tablename__ = "use_cases"

    use_case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    use_case_type: Mapped[UseCaseType] = mapped_column(Enum(UseCaseType), nullable=False)

    answer_sets: Mapped[list[AnswerSetEntity]] = relationship(back_populates="use_case")


class AnswerSetEntity(TimestampVersionMixin, Base):
    __tablename__ = "answer_sets"

    answer_set_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    use_case_id: Mapped[str] = mapped_column(ForeignKey("use_cases.use_case_id"), nullable=False)
    status: Mapped[AnswerSetStatus] = mapped_column(
        Enum(AnswerSetStatus), default=AnswerSetStatus.DRAFT, nullable=False
    )
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    use_case: Mapped[UseCaseEntity] = relationship(back_populates="answer_sets")
    answers: Mapped[list[AnswerEntity]] = relationship(back_populates="answer_set", cascade="all, delete-orphan")


class AnswerEntity(TimestampVersionMixin, Base):
    __tablename__ = "answers"

    answer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    answer_set_id: Mapped[str] = mapped_column(ForeignKey("answer_sets.answer_set_id"), nullable=False)
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    answer_set: Mapped[AnswerSetEntity] = relationship(back_populates="answers")


class BIAssessmentEntity(TimestampVersionMixin, Base):
    __tablename__ = "assessments_bi"

    bi_assessment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    answer_set_id: Mapped[str] = mapped_column(ForeignKey("answer_sets.answer_set_id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class PAAssessmentEntity(TimestampVersionMixin, Base):
    __tablename__ = "assessments_pa"

    pa_assessment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    answer_set_id: Mapped[str] = mapped_column(ForeignKey("answer_sets.answer_set_id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class SynthesisEntity(TimestampVersionMixin, Base):
    __tablename__ = "synthesis"

    synthesis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    bi_assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments_bi.bi_assessment_id"), nullable=False)
    pa_assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments_pa.pa_assessment_id"), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class MeasureCatalogEntity(TimestampVersionMixin, Base):
    __tablename__ = "measure_catalogs"

    catalog_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CatalogStatus] = mapped_column(Enum(CatalogStatus), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    measures: Mapped[list[MeasureEntity]] = relationship(back_populates="catalog", cascade="all, delete-orphan")


class MeasureEntity(TimestampVersionMixin, Base):
    __tablename__ = "measures"

    measure_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    catalog_id: Mapped[str] = mapped_column(ForeignKey("measure_catalogs.catalog_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[MeasureCategory] = mapped_column(Enum(MeasureCategory), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    catalog: Mapped[MeasureCatalogEntity] = relationship(back_populates="measures")


class UserSelectionEntity(TimestampVersionMixin, Base):
    __tablename__ = "user_selections"

    user_selection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    synthesis_id: Mapped[str] = mapped_column(ForeignKey("synthesis.synthesis_id"), nullable=False)
    selected_measure_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
