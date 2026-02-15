from __future__ import annotations

from sqlalchemy.orm import Session

from domain.models import (
    Answer,
    AnswerSet,
    BIAssessment,
    Measure,
    MeasureCatalog,
    PAAssessment,
    Synthesis,
    UseCase,
    UserSelection,
)
from persistence.entities import (
    AnswerEntity,
    AnswerSetEntity,
    BIAssessmentEntity,
    MeasureCatalogEntity,
    MeasureEntity,
    PAAssessmentEntity,
    SynthesisEntity,
    UseCaseEntity,
    UserSelectionEntity,
)


class PersistenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_use_case(self, use_case: UseCase) -> UseCase:
        entity = UseCaseEntity(**use_case.model_dump())
        self.session.merge(entity)
        self.session.commit()
        return use_case

    def save_answer_set(self, answer_set: AnswerSet, answers: list[Answer]) -> None:
        answer_set_payload = answer_set.model_dump()
        answer_set_entity = AnswerSetEntity(
            answer_set_id=answer_set_payload["answer_set_id"],
            use_case_id=answer_set_payload["questionnaire_id"],
            status=answer_set_payload["status"],
            model_version=answer_set_payload["model_version"],
            prompt_version=answer_set_payload["prompt_version"],
            created_at=answer_set_payload["created_at"],
            details={"questionnaire_id": answer_set_payload["questionnaire_id"]},
        )

        existing_answer_set = self.session.get(AnswerSetEntity, answer_set.answer_set_id)
        if existing_answer_set:
            self.session.delete(existing_answer_set)
            self.session.flush()

        self.session.add(answer_set_entity)
        for answer in answers:
            answer_payload = answer.model_dump()
            self.session.add(
                AnswerEntity(
                    answer_id=answer_payload["answer_id"],
                    answer_set_id=answer_set.answer_set_id,
                    question_id=answer_payload["question_id"],
                    value=answer_payload["value"],
                    model_version=answer_payload["model_version"],
                    prompt_version=answer_payload["prompt_version"],
                    created_at=answer_payload["created_at"],
                    details={},
                )
            )

        self.session.commit()

    def load_answer_set(self, answer_set_id: str) -> tuple[AnswerSet, list[Answer]] | None:
        answer_set_entity = self.session.get(AnswerSetEntity, answer_set_id)
        if answer_set_entity is None:
            return None

        answer_set = AnswerSet(
            answer_set_id=answer_set_entity.answer_set_id,
            questionnaire_id=answer_set_entity.details.get("questionnaire_id", answer_set_entity.use_case_id),
            status=answer_set_entity.status,
            model_version=answer_set_entity.model_version,
            prompt_version=answer_set_entity.prompt_version,
            created_at=answer_set_entity.created_at,
        )
        answers = [
            Answer(
                answer_id=entity.answer_id,
                answer_set_id=entity.answer_set_id,
                question_id=entity.question_id,
                value=entity.value,
                model_version=entity.model_version,
                prompt_version=entity.prompt_version,
                created_at=entity.created_at,
            )
            for entity in answer_set_entity.answers
        ]
        return answer_set, answers

    def save_assessments(self, bi_assessment: BIAssessment, pa_assessment: PAAssessment) -> None:
        bi_payload = bi_assessment.model_dump()
        pa_payload = pa_assessment.model_dump()

        self.session.merge(
            BIAssessmentEntity(
                bi_assessment_id=bi_payload["bi_assessment_id"],
                answer_set_id=bi_payload["answer_set_id"],
                score=bi_payload["score"],
                summary=bi_payload["summary"],
                model_version=bi_payload["model_version"],
                prompt_version=bi_payload["prompt_version"],
                created_at=bi_payload["created_at"],
                details={"maturity_level": bi_payload.get("maturity_level"), "level_label": bi_payload.get("level_label"), "dimension_scores": bi_payload.get("dimension_scores", {}), "findings": bi_payload.get("findings", {})},
            )
        )
        self.session.merge(
            PAAssessmentEntity(
                pa_assessment_id=pa_payload["pa_assessment_id"],
                answer_set_id=pa_payload["answer_set_id"],
                score=pa_payload["score"],
                summary=pa_payload["summary"],
                model_version=pa_payload["model_version"],
                prompt_version=pa_payload["prompt_version"],
                created_at=pa_payload["created_at"],
                details={"maturity_level": pa_payload.get("maturity_level"), "level_label": pa_payload.get("level_label"), "dimension_scores": pa_payload.get("dimension_scores", {}), "findings": pa_payload.get("findings", {})},
            )
        )
        self.session.commit()

    def save_synthesis(self, synthesis: Synthesis) -> None:
        payload = synthesis.model_dump()
        self.session.merge(
            SynthesisEntity(
                synthesis_id=payload["synthesis_id"],
                bi_assessment_id=payload["bi_assessment_id"],
                pa_assessment_id=payload["pa_assessment_id"],
                recommendation=payload["recommendation"],
                model_version=payload["model_version"],
                prompt_version=payload["prompt_version"],
                created_at=payload["created_at"],
                details={},
            )
        )
        self.session.commit()

    def save_catalog(self, catalog: MeasureCatalog) -> None:
        payload = catalog.model_dump()
        existing = self.session.get(MeasureCatalogEntity, catalog.catalog_id)
        if existing:
            self.session.delete(existing)
            self.session.flush()

        catalog_entity = MeasureCatalogEntity(
            catalog_id=payload["catalog_id"],
            title=payload["title"],
            status=payload["status"],
            model_version=payload["model_version"],
            prompt_version=payload["prompt_version"],
            created_at=payload["created_at"],
            details={},
        )
        self.session.add(catalog_entity)

        for measure in catalog.measures:
            measure_payload = measure.model_dump()
            self.session.add(
                MeasureEntity(
                    measure_id=measure_payload["measure_id"],
                    catalog_id=catalog.catalog_id,
                    title=measure_payload["title"],
                    description=measure_payload["description"],
                    category=measure_payload["category"],
                    model_version=measure_payload["model_version"],
                    prompt_version=measure_payload["prompt_version"],
                    created_at=measure_payload["created_at"],
                    details={},
                )
            )

        self.session.commit()

    def save_user_selection(self, selection: UserSelection) -> None:
        payload = selection.model_dump()
        self.session.merge(
            UserSelectionEntity(
                user_selection_id=payload["user_selection_id"],
                synthesis_id=payload["synthesis_id"],
                selected_measure_ids=payload["selected_measure_ids"],
                model_version=payload["model_version"],
                prompt_version=payload["prompt_version"],
                created_at=payload["created_at"],
                details={},
            )
        )
        self.session.commit()


def load_catalog(session: Session, catalog_id: str) -> MeasureCatalog | None:
    entity = session.get(MeasureCatalogEntity, catalog_id)
    if entity is None:
        return None

    measures = [
        Measure(
            measure_id=measure.measure_id,
            title=measure.title,
            description=measure.description,
            category=measure.category,
            model_version=measure.model_version,
            prompt_version=measure.prompt_version,
            created_at=measure.created_at,
        )
        for measure in entity.measures
    ]
    return MeasureCatalog(
        catalog_id=entity.catalog_id,
        title=entity.title,
        status=entity.status,
        measures=measures,
        model_version=entity.model_version,
        prompt_version=entity.prompt_version,
        created_at=entity.created_at,
    )
