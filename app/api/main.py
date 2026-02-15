from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.services.assessment_service import AssessmentService
from app.services.questionnaire_service import QuestionnaireService
from domain.models import Answer, AnswerSet, AnswerSetStatus, UseCase, UseCaseType
from persistence.database import Base, create_sqlite_engine, create_session_factory
from persistence.repositories import PersistenceRepository

app = FastAPI(title="InsightHub API")
questionnaire_service = QuestionnaireService()
assessment_service = AssessmentService()

engine = create_sqlite_engine()
Base.metadata.create_all(engine)
session_factory = create_session_factory()


class ValidateAnswerSetRequest(BaseModel):
    version: str = Field(default="v1.0")
    answers: dict[str, Any] = Field(default_factory=dict)


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
