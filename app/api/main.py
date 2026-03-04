from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.services.assessment_service import AssessmentService
from app.services.questionnaire_service import QuestionnaireService
from app.services.recommendation_service import RecommendationService
from app.services.synthesis_service import SynthesisService
from adapters.llm_client import LLMClient
from domain.models import Answer, AnswerSet, AnswerSetStatus, UseCase, UseCaseType, UserSelection
from persistence.database import Base, create_sqlite_engine, create_session_factory
from persistence.entities import (
    AnswerSetEntity,
    BIAssessmentEntity,
    MeasureCatalogEntity,
    PAAssessmentEntity,
    SynthesisEntity,
    UseCaseEntity,
    UserSelectionEntity,
)
from persistence.repositories import PersistenceRepository, load_catalog

app = FastAPI(title="InsightHub API")
questionnaire_service = QuestionnaireService()
assessment_service = AssessmentService()

engine = create_sqlite_engine()
Base.metadata.create_all(engine)
session_factory = create_session_factory()


class CreateUseCaseRequest(BaseModel):
    use_case_id: str = Field(default_factory=lambda: f"uc-{uuid4().hex[:12]}")
    name: str
    description: str
    use_case_type: UseCaseType = Field(default=UseCaseType.COMBINED)


class SaveAnswerSetRequest(BaseModel):
    answer_set_id: str = Field(default_factory=lambda: f"as-{uuid4().hex[:12]}")
    use_case_id: str
    version: str = Field(default="v1.0")
    answers: dict[str, Any] = Field(default_factory=dict)


class RunRecommendationsRequest(BaseModel):
    use_llm_texts: bool = Field(default=False)
    ollama_api_key: str | None = Field(default=None, description="Optionaler Ollama API Key")


class RunSynthesisRequest(BaseModel):
    ollama_api_key: str | None = Field(default=None, description="Optionaler Ollama API Key")


class FinalizeMeasureSelection(BaseModel):
    measure_id: str
    selected: bool = Field(default=True)
    final_priority: int | None = Field(default=None, ge=1)


class FinalizeRecommendationsRequest(BaseModel):
    selections: list[FinalizeMeasureSelection] = Field(default_factory=list)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.post("/usecases")
def create_use_case(request: CreateUseCaseRequest) -> dict[str, Any]:
    use_case = UseCase(
        use_case_id=request.use_case_id,
        name=request.name,
        description=request.description,
        use_case_type=request.use_case_type,
    )

    with session_factory() as session:
        repository = PersistenceRepository(session)
        repository.create_use_case(use_case)

    return use_case.model_dump()


@app.get("/questionnaire")
def get_questionnaire(version: str = "v1.0") -> dict[str, Any]:
    try:
        questionnaire = questionnaire_service.get_questionnaire(version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return questionnaire.model_dump()


@app.post("/answersets")
def save_answer_set(request: SaveAnswerSetRequest) -> dict[str, Any]:
    validation = questionnaire_service.validate_answer_set(request.version, request.answers)
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail={"message": "Answer-Set ist nicht valide.", "issues": validation.model_dump()},
        )

    with session_factory() as session:
        repository = PersistenceRepository(session)
        use_case_entity = session.get(UseCaseEntity, request.use_case_id)
        if use_case_entity is None:
            raise HTTPException(status_code=404, detail="Use Case nicht gefunden.")

        repository.save_answer_set(
            AnswerSet(
                answer_set_id=request.answer_set_id,
                questionnaire_id=request.use_case_id,
                status=AnswerSetStatus.SUBMITTED,
                prompt_version=f"questionnaire_{request.version}",
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

    return {
        "answer_set_id": request.answer_set_id,
        "use_case_id": request.use_case_id,
        "status": AnswerSetStatus.SUBMITTED,
        "validation": validation.model_dump(),
    }


@app.post("/answersets/{answer_set_id}/validate")
def validate_answer_set(answer_set_id: str) -> dict[str, Any]:
    with session_factory() as session:
        repository = PersistenceRepository(session)
        loaded = repository.load_answer_set(answer_set_id)
        if loaded is None:
            raise HTTPException(status_code=404, detail="Answer-Set nicht gefunden.")

        answer_set, answers = loaded
        answer_payload = {answer.question_id: json.loads(answer.value) for answer in answers}
        version = answer_set.prompt_version.replace("questionnaire_", "") if answer_set.prompt_version.startswith("questionnaire_") else "v1.0"
        result = questionnaire_service.validate_answer_set(version, answer_payload)

        if result.valid:
            repository.save_answer_set(
                AnswerSet(
                    answer_set_id=answer_set.answer_set_id,
                    questionnaire_id=answer_set.questionnaire_id,
                    status=AnswerSetStatus.LOCKED,
                    model_version=answer_set.model_version,
                    prompt_version=answer_set.prompt_version,
                    created_at=answer_set.created_at,
                ),
                answers,
            )

    return {
        "answer_set_id": answer_set_id,
        "valid": result.valid,
        "issues": [issue.model_dump() for issue in result.issues],
        "status": AnswerSetStatus.LOCKED if result.valid else AnswerSetStatus.SUBMITTED,
    }


@app.post("/assessments/{answer_set_id}")
def run_assessments(answer_set_id: str) -> dict[str, Any]:
    with session_factory() as session:
        repository = PersistenceRepository(session)
        loaded = repository.load_answer_set(answer_set_id)
        if loaded is None:
            raise HTTPException(status_code=404, detail="Answer-Set nicht gefunden.")

        answer_set, answers = loaded
        answer_payload = {answer.question_id: json.loads(answer.value) for answer in answers}
        version = answer_set.prompt_version.replace("questionnaire_", "") if answer_set.prompt_version.startswith("questionnaire_") else "v1.0"
        validation = questionnaire_service.validate_answer_set(version, answer_payload)
        if not validation.valid:
            raise HTTPException(
                status_code=422,
                detail={"message": "Answer-Set ist nicht valide.", "issues": validation.model_dump()},
            )

        bi_assessment = assessment_service.compute_bi_assessment(answer_set_id, answer_payload, version)
        pa_assessment = assessment_service.compute_pa_assessment(answer_set_id, answer_payload, version)
        repository.save_assessments(bi_assessment, pa_assessment)

    return {
        "answer_set_id": answer_set_id,
        "bi_assessment": bi_assessment.model_dump(),
        "pa_assessment": pa_assessment.model_dump(),
    }


@app.post("/synthesis/{answer_set_id}")
def run_synthesis(answer_set_id: str, request: RunSynthesisRequest | None = None) -> dict[str, Any]:
    ollama_api_key = request.ollama_api_key if request else None
    llm_client = LLMClient(api_key=ollama_api_key, dry_run=False) if ollama_api_key else LLMClient()
    synthesis_service_with_config = SynthesisService(llm_client=llm_client)

    with session_factory() as session:
        repository = PersistenceRepository(session)
        assessments = repository.load_assessments_for_answer_set(answer_set_id)
        if assessments is None:
            raise HTTPException(status_code=404, detail="Keine gespeicherten Assessments für answer_set_id gefunden.")

        bi_assessment, pa_assessment = assessments
        loaded = repository.load_answer_set(answer_set_id)
        answer_payload = {}
        if loaded is not None:
            _, answers = loaded
            answer_payload = {answer.question_id: json.loads(answer.value) for answer in answers}

        synthesis = synthesis_service_with_config.synthesize(bi_assessment, pa_assessment, answer_payload)
        repository.save_synthesis(synthesis)

    return synthesis.model_dump()


@app.post("/catalog/{answer_set_id}")
def run_catalog(answer_set_id: str, request: RunRecommendationsRequest) -> dict[str, Any]:
    llm_client = LLMClient(api_key=request.ollama_api_key, dry_run=False) if request.ollama_api_key else LLMClient()
    recommendation_service_with_config = RecommendationService(llm_client=llm_client)

    with session_factory() as session:
        repository = PersistenceRepository(session)
        assessments = repository.load_assessments_for_answer_set(answer_set_id)
        if assessments is None:
            raise HTTPException(status_code=404, detail="Keine gespeicherten Assessments für answer_set_id gefunden.")

        bi_assessment, pa_assessment = assessments
        synthesis = repository.load_latest_synthesis_for_answer_set(answer_set_id)
        if synthesis is None:
            loaded = repository.load_answer_set(answer_set_id)
            answer_payload = {}
            if loaded is not None:
                _, answers = loaded
                answer_payload = {answer.question_id: json.loads(answer.value) for answer in answers}
            synthesis = SynthesisService(llm_client=llm_client).synthesize(bi_assessment, pa_assessment, answer_payload)
            repository.save_synthesis(synthesis)

        loaded = repository.load_answer_set(answer_set_id)
        answer_payload = {}
        if loaded is not None:
            _, answers = loaded
            answer_payload = {answer.question_id: json.loads(answer.value) for answer in answers}

        catalog = recommendation_service_with_config.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label=bi_assessment.level_label,
            pa_maturity_label=pa_assessment.level_label,
            bi_dimension_scores=bi_assessment.dimension_scores,
            pa_dimension_scores=pa_assessment.dimension_scores,
            bi_dimension_levels=bi_assessment.dimension_levels,
            pa_dimension_levels=pa_assessment.dimension_levels,
            use_llm_texts=request.use_llm_texts,
            answers=answer_payload,
        )
        repository.save_catalog(catalog)

    return catalog.model_dump()


@app.post("/catalog/{catalog_id}/selection")
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


@app.get("/results/{use_case_id}")
def get_results(use_case_id: str) -> dict[str, Any]:
    with session_factory() as session:
        use_case = session.get(UseCaseEntity, use_case_id)
        if use_case is None:
            raise HTTPException(status_code=404, detail="Use Case nicht gefunden.")

        answer_sets = session.scalars(select(AnswerSetEntity).where(AnswerSetEntity.use_case_id == use_case_id)).all()
        results: list[dict[str, Any]] = []

        for answer_set in answer_sets:
            bi_assessment = session.scalar(
                select(BIAssessmentEntity)
                .where(BIAssessmentEntity.answer_set_id == answer_set.answer_set_id)
                .order_by(BIAssessmentEntity.created_at.desc())
                .limit(1)
            )
            pa_assessment = session.scalar(
                select(PAAssessmentEntity)
                .where(PAAssessmentEntity.answer_set_id == answer_set.answer_set_id)
                .order_by(PAAssessmentEntity.created_at.desc())
                .limit(1)
            )
            synthesis = session.scalar(
                select(SynthesisEntity)
                .where(SynthesisEntity.details["answer_set_id"].as_string() == answer_set.answer_set_id)
                .order_by(SynthesisEntity.created_at.desc())
                .limit(1)
            )

            catalog = None
            selection = None
            if synthesis is not None:
                catalog = session.scalar(
                    select(MeasureCatalogEntity)
                    .where(MeasureCatalogEntity.details["synthesis_id"].as_string() == synthesis.synthesis_id)
                    .order_by(MeasureCatalogEntity.created_at.desc())
                    .limit(1)
                )
                if catalog is not None:
                    selection = session.scalar(
                        select(UserSelectionEntity)
                        .where(UserSelectionEntity.details["catalog_id"].as_string() == catalog.catalog_id)
                        .order_by(UserSelectionEntity.created_at.desc())
                        .limit(1)
                    )

            results.append(
                {
                    "answer_set_id": answer_set.answer_set_id,
                    "status": answer_set.status,
                    "bi_assessment": None
                    if bi_assessment is None
                    else {
                        "bi_assessment_id": bi_assessment.bi_assessment_id,
                        "score": bi_assessment.score,
                        "summary": bi_assessment.summary,
                        "details": bi_assessment.details,
                    },
                    "pa_assessment": None
                    if pa_assessment is None
                    else {
                        "pa_assessment_id": pa_assessment.pa_assessment_id,
                        "score": pa_assessment.score,
                        "summary": pa_assessment.summary,
                        "details": pa_assessment.details,
                    },
                    "synthesis": None
                    if synthesis is None
                    else {
                        "synthesis_id": synthesis.synthesis_id,
                        "recommendation": synthesis.recommendation,
                        "details": synthesis.details,
                    },
                    "catalog": None
                    if catalog is None
                    else {
                        "catalog_id": catalog.catalog_id,
                        "title": catalog.title,
                        "status": catalog.status,
                        "details": catalog.details,
                    },
                    "selection": None
                    if selection is None
                    else {
                        "user_selection_id": selection.user_selection_id,
                        "selected_measure_ids": selection.selected_measure_ids,
                        "details": selection.details,
                    },
                }
            )

    return {
        "use_case": {
            "use_case_id": use_case.use_case_id,
            "name": use_case.name,
            "description": use_case.description,
            "use_case_type": use_case.use_case_type,
        },
        "results": results,
    }
