from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.services.questionnaire_service import QuestionnaireService

app = FastAPI(title="InsightHub API")
questionnaire_service = QuestionnaireService()


class ValidateAnswerSetRequest(BaseModel):
    version: str = Field(default="v1.0")
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
