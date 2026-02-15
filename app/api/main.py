from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.services.assessment_service import AssessmentService
from app.services.questionnaire_service import QuestionnaireService
from app.services.recommendation_service import RecommendationService
from app.services.synthesis_service import SynthesisService
from domain.models import Answer, AnswerSet, AnswerSetStatus, UseCase, UseCaseType, UserSelection
from persistence.database import Base, create_sqlite_engine, create_session_factory
from persistence.repositories import PersistenceRepository, load_catalog

app = FastAPI(title="InsightHub API")
questionnaire_service = QuestionnaireService()
assessment_service = AssessmentService()
synthesis_service = SynthesisService()
recommendation_service = RecommendationService()

engine = create_sqlite_engine()
Base.metadata.create_all(engine)
session_factory = create_session_factory()


class ValidateAnswerSetRequest(BaseModel):
    version: str = Field(default="v1.0")
    answers: dict[str, Any] = Field(default_factory=dict)




class RunSynthesisRequest(BaseModel):
    answer_set_id: str


class RunRecommendationsRequest(BaseModel):
    answer_set_id: str
    use_llm_texts: bool = Field(default=False)


class FinalizeMeasureSelection(BaseModel):
    measure_id: str
    selected: bool = Field(default=True)
    final_priority: int | None = Field(default=None, ge=1)


class FinalizeRecommendationsRequest(BaseModel):
    selections: list[FinalizeMeasureSelection] = Field(default_factory=list)


class RunAssessmentsRequest(BaseModel):
    version: str = Field(default="v1.0")
    answer_set_id: str = Field(default_factory=lambda: f"as-{uuid4().hex[:12]}")
    use_case_id: str = Field(default_factory=lambda: f"uc-{uuid4().hex[:12]}")
    use_case_name: str = Field(default="Ad-hoc Assessment")
    use_case_description: str = Field(default="Automatisch erzeugter Use Case für Assessment-Lauf.")
    use_case_type: UseCaseType = Field(default=UseCaseType.COMBINED)
    answers: dict[str, Any] = Field(default_factory=dict)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/questionnaire")
def get_questionnaire(version: str = "v1.0") -> dict[str, Any]:
    try:
        questionnaire = questionnaire_service.get_questionnaire(version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return questionnaire.model_dump()


@app.post("/answerset/validate")
def validate_answer_set(request: ValidateAnswerSetRequest) -> dict[str, Any]:
    try:
        result = questionnaire_service.validate_answer_set(request.version, request.answers)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = result.model_dump()
    if result.valid:
        payload.update(questionnaire_service.finalize_answer_set())
    return payload


@app.post("/assessments/run")
def run_assessments(request: RunAssessmentsRequest) -> dict[str, Any]:
    validation = questionnaire_service.validate_answer_set(request.version, request.answers)
    if not validation.valid:
        raise HTTPException(status_code=422, detail={"message": "Answer-Set ist nicht valide.", "issues": validation.model_dump()})

    bi_assessment = assessment_service.compute_bi_assessment(request.answer_set_id, request.answers, request.version)
    pa_assessment = assessment_service.compute_pa_assessment(request.answer_set_id, request.answers, request.version)

    with session_factory() as session:
        repository = PersistenceRepository(session)
        repository.create_use_case(
            UseCase(
                use_case_id=request.use_case_id,
                name=request.use_case_name,
                description=request.use_case_description,
                use_case_type=request.use_case_type,
            )
        )
        repository.save_answer_set(
            AnswerSet(
                answer_set_id=request.answer_set_id,
                questionnaire_id=request.use_case_id,
                status=AnswerSetStatus.SUBMITTED,
            ),
            [
                Answer(
                    answer_id=f"ans-{uuid4().hex[:12]}",
                    answer_set_id=request.answer_set_id,
                    question_id=question_id,
                    value=json.dumps(value, ensure_ascii=False),
                )
                for question_id, value in request.answers.items()
            ],
        )
        repository.save_assessments(bi_assessment, pa_assessment)

    return {
        "answer_set_id": request.answer_set_id,
        "bi_assessment": bi_assessment.model_dump(),
        "pa_assessment": pa_assessment.model_dump(),
    }


@app.post("/synthesis/run")
def run_synthesis(request: RunSynthesisRequest) -> dict[str, Any]:
    with session_factory() as session:
        repository = PersistenceRepository(session)
        assessments = repository.load_assessments_for_answer_set(request.answer_set_id)
        if assessments is None:
            raise HTTPException(status_code=404, detail="Keine gespeicherten Assessments für answer_set_id gefunden.")

        bi_assessment, pa_assessment = assessments
        synthesis = synthesis_service.synthesize(bi_assessment, pa_assessment)
        repository.save_synthesis(synthesis)

    return synthesis.model_dump()


@app.post("/recommendations/run")
def run_recommendations(request: RunRecommendationsRequest) -> dict[str, Any]:
    with session_factory() as session:
        repository = PersistenceRepository(session)
        assessments = repository.load_assessments_for_answer_set(request.answer_set_id)
        if assessments is None:
            raise HTTPException(status_code=404, detail="Keine gespeicherten Assessments für answer_set_id gefunden.")

        bi_assessment, pa_assessment = assessments
        synthesis = repository.load_latest_synthesis_for_answer_set(request.answer_set_id)
        if synthesis is None:
            synthesis = synthesis_service.synthesize(bi_assessment, pa_assessment)
            repository.save_synthesis(synthesis)

        catalog = recommendation_service.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label=bi_assessment.level_label,
            pa_maturity_label=pa_assessment.level_label,
            bi_dimension_scores=bi_assessment.dimension_scores,
            pa_dimension_scores=pa_assessment.dimension_scores,
            use_llm_texts=request.use_llm_texts,
        )
        repository.save_catalog(catalog)

    return catalog.model_dump()


@app.post("/recommendations/{catalog_id}/finalize")
def finalize_recommendations(catalog_id: str, request: FinalizeRecommendationsRequest) -> dict[str, Any]:
    with session_factory() as session:
        catalog = load_catalog(session, catalog_id)
        if catalog is None:
            raise HTTPException(status_code=404, detail="Maßnahmenkatalog nicht gefunden.")

        selection_map = {entry.measure_id: entry for entry in request.selections}
        selected_measure_ids = [
            measure.measure_id
            for measure in catalog.measures
            if selection_map.get(measure.measure_id, FinalizeMeasureSelection(measure_id=measure.measure_id)).selected
        ]
        final_priority = {
            entry.measure_id: entry.final_priority
            for entry in request.selections
            if entry.selected and entry.final_priority is not None
        }

        repository = PersistenceRepository(session)
        selection = UserSelection(
            user_selection_id=f"sel-{uuid4().hex[:12]}",
            synthesis_id=catalog.synthesis_id,
            catalog_id=catalog_id,
            selected_measure_ids=selected_measure_ids,
            final_priority=final_priority,
        )
        repository.save_user_selection(selection)

    return selection.model_dump()
