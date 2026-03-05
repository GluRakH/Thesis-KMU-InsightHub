from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select

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
                details={
                    "maturity_level": bi_payload.get("maturity_level"),
                    "level_label": bi_payload.get("level_label"),
                    "dimension_scores": bi_payload.get("dimension_scores", {}),
                    "findings": bi_payload.get("findings", {}),
                    "critical_dimension_id": bi_payload.get("critical_dimension_id", ""),
                    "critical_dimension_severity": bi_payload.get("critical_dimension_severity", 0.0),
                    "critical_dimension_top_items": bi_payload.get("critical_dimension_top_items", []),
                    "questionnaire_version": bi_payload.get("questionnaire_version", ""),
                    "scoring_version": bi_payload.get("scoring_version", ""),
                },
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
                details={
                    "maturity_level": pa_payload.get("maturity_level"),
                    "level_label": pa_payload.get("level_label"),
                    "dimension_scores": pa_payload.get("dimension_scores", {}),
                    "findings": pa_payload.get("findings", {}),
                    "critical_dimension_id": pa_payload.get("critical_dimension_id", ""),
                    "critical_dimension_severity": pa_payload.get("critical_dimension_severity", 0.0),
                    "critical_dimension_top_items": pa_payload.get("critical_dimension_top_items", []),
                    "questionnaire_version": pa_payload.get("questionnaire_version", ""),
                    "scoring_version": pa_payload.get("scoring_version", ""),
                },
            )
        )
        self.session.commit()

    def load_assessments_for_answer_set(self, answer_set_id: str) -> tuple[BIAssessment, PAAssessment] | None:
        bi_entity = self.session.scalar(
            select(BIAssessmentEntity)
            .where(BIAssessmentEntity.answer_set_id == answer_set_id)
            .order_by(BIAssessmentEntity.created_at.desc())
            .limit(1)
        )
        pa_entity = self.session.scalar(
            select(PAAssessmentEntity)
            .where(PAAssessmentEntity.answer_set_id == answer_set_id)
            .order_by(PAAssessmentEntity.created_at.desc())
            .limit(1)
        )

        if bi_entity is None or pa_entity is None:
            return None

        bi_assessment = BIAssessment(
            bi_assessment_id=bi_entity.bi_assessment_id,
            answer_set_id=bi_entity.answer_set_id,
            score=bi_entity.score,
            summary=bi_entity.summary,
            maturity_level=bi_entity.details.get("maturity_level", 1),
            level_label=bi_entity.details.get("level_label", "LOW"),
            dimension_scores=bi_entity.details.get("dimension_scores", {}),
            findings=bi_entity.details.get("findings", {}),
            critical_dimension_id=bi_entity.details.get("critical_dimension_id", ""),
            critical_dimension_severity=bi_entity.details.get("critical_dimension_severity", 0.0),
            critical_dimension_top_items=bi_entity.details.get("critical_dimension_top_items", []),
            questionnaire_version=bi_entity.details.get("questionnaire_version", ""),
            scoring_version=bi_entity.details.get("scoring_version", ""),
            model_version=bi_entity.model_version,
            prompt_version=bi_entity.prompt_version,
            created_at=bi_entity.created_at,
        )
        pa_assessment = PAAssessment(
            pa_assessment_id=pa_entity.pa_assessment_id,
            answer_set_id=pa_entity.answer_set_id,
            score=pa_entity.score,
            summary=pa_entity.summary,
            maturity_level=pa_entity.details.get("maturity_level", 1),
            level_label=pa_entity.details.get("level_label", "LOW"),
            dimension_scores=pa_entity.details.get("dimension_scores", {}),
            findings=pa_entity.details.get("findings", {}),
            critical_dimension_id=pa_entity.details.get("critical_dimension_id", ""),
            critical_dimension_severity=pa_entity.details.get("critical_dimension_severity", 0.0),
            critical_dimension_top_items=pa_entity.details.get("critical_dimension_top_items", []),
            questionnaire_version=pa_entity.details.get("questionnaire_version", ""),
            scoring_version=pa_entity.details.get("scoring_version", ""),
            model_version=pa_entity.model_version,
            prompt_version=pa_entity.prompt_version,
            created_at=pa_entity.created_at,
        )

        return bi_assessment, pa_assessment

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
                details={
                    "answer_set_id": payload.get("answer_set_id"),
                    "combined_summary": payload.get("combined_summary", ""),
                    "priority_focus": payload.get("priority_focus", ""),
                    "heuristic_reason": payload.get("heuristic_reason", ""),
                    "questionnaire_version": payload.get("questionnaire_version", ""),
                    "scoring_version": payload.get("scoring_version", ""),
                    "llm_model": payload.get("llm_model", ""),
                    "llm_prompt_version": payload.get("llm_prompt_version", ""),
                },
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
            details={"measure_count": len(catalog.measures), "synthesis_id": payload.get("synthesis_id", "")},
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
                    details={
                        "dimension": measure_payload.get("dimension", ""),
                        "maturity_label": measure_payload.get("maturity_label", ""),
                        "measure_class": measure_payload.get("measure_class", ""),
                        "impact": measure_payload.get("impact", 1),
                        "effort": measure_payload.get("effort", 1),
                        "priority_score": measure_payload.get("priority_score", 0.0),
                        "prerequisites": measure_payload.get("prerequisites", []),
                        "dependencies": measure_payload.get("dependencies", []),
                        "suggested_priority": measure_payload.get("suggested_priority", 1),
                        "initiative_id": measure_payload.get("initiative_id", ""),
                        "goal": measure_payload.get("goal", ""),
                        "evidence": measure_payload.get("evidence", {}),
                        "priority": measure_payload.get("priority", {}),
                        "kpi": measure_payload.get("kpi", {}),
                        "deliverables": measure_payload.get("deliverables", []),
                    },
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
                details={
                    "catalog_id": payload.get("catalog_id", ""),
                    "final_priority": payload.get("final_priority", {}),
                },
            )
        )
        self.session.commit()

    def load_latest_synthesis_for_answer_set(self, answer_set_id: str) -> Synthesis | None:
        entities = self.session.scalars(select(SynthesisEntity).order_by(SynthesisEntity.created_at.desc())).all()
        for entity in entities:
            if entity.details.get("answer_set_id") != answer_set_id:
                continue
            return Synthesis(
                synthesis_id=entity.synthesis_id,
                answer_set_id=entity.details.get("answer_set_id", ""),
                bi_assessment_id=entity.bi_assessment_id,
                pa_assessment_id=entity.pa_assessment_id,
                combined_summary=entity.details.get("combined_summary", ""),
                priority_focus=entity.details.get("priority_focus", ""),
                heuristic_reason=entity.details.get("heuristic_reason", ""),
                questionnaire_version=entity.details.get("questionnaire_version", ""),
                scoring_version=entity.details.get("scoring_version", ""),
                llm_model=entity.details.get("llm_model", ""),
                llm_prompt_version=entity.details.get("llm_prompt_version", ""),
                recommendation=entity.recommendation,
                model_version=entity.model_version,
                prompt_version=entity.prompt_version,
                created_at=entity.created_at,
            )
        return None


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
            dimension=measure.details.get("dimension", ""),
            maturity_label=measure.details.get("maturity_label", ""),
            measure_class=measure.details.get("measure_class", ""),
            impact=measure.details.get("impact", 1),
            effort=measure.details.get("effort", 1),
            priority_score=measure.details.get("priority_score", 0.0),
            prerequisites=measure.details.get("prerequisites", []),
            dependencies=measure.details.get("dependencies", []),
            suggested_priority=measure.details.get("suggested_priority", 1),
            initiative_id=measure.details.get("initiative_id", ""),
            goal=measure.details.get("goal", ""),
            evidence=measure.details.get("evidence", {}),
            priority=measure.details.get("priority", {}),
            kpi=measure.details.get("kpi", {}),
            deliverables=measure.details.get("deliverables", []),
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
        synthesis_id=entity.details.get("synthesis_id", ""),
        measures=measures,
        model_version=entity.model_version,
        prompt_version=entity.prompt_version,
        created_at=entity.created_at,
    )
