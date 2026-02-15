import unittest

from fastapi.testclient import TestClient

from app.api.main import app
from app.services.questionnaire_service import QuestionnaireService


class QuestionnaireServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = QuestionnaireService()

    def _build_valid_answers(self) -> dict[str, object]:
        questionnaire = self.service.get_questionnaire("v1.0")
        answers: dict[str, object] = {}

        for question in questionnaire.questions:
            if not question.required:
                continue
            if question.type == "TEXT":
                answers[question.id] = "Beispieltext"
            elif question.type == "SINGLE_CHOICE":
                answers[question.id] = question.options[0]
            elif question.type == "MULTI_CHOICE":
                answers[question.id] = [question.options[0]]
            elif question.type == "SCALE":
                answers[question.id] = question.scale.min if question.scale else 1
            elif question.type == "NUMBER":
                answers[question.id] = 1

        return answers

    def test_get_questionnaire(self) -> None:
        questionnaire = self.service.get_questionnaire("v1.0")

        self.assertEqual(questionnaire.version, "v1.0")
        self.assertEqual(len(questionnaire.questions), 30)

    def test_validate_answer_set_detects_missing_required_answers(self) -> None:
        result = self.service.validate_answer_set("v1.0", {})

        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "REQUIRED_MISSING" for issue in result.issues))

    def test_validate_answer_set_accepts_valid_answers(self) -> None:
        answers = self._build_valid_answers()
        result = self.service.validate_answer_set("v1.0", answers)

        self.assertTrue(result.valid)
        self.assertEqual(result.issues, [])


class QuestionnaireApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_get_questionnaire_route(self) -> None:
        response = self.client.get("/questionnaire", params={"version": "v1.0"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["version"], "v1.0")
        self.assertEqual(len(payload["questions"]), 30)

    def test_validate_route(self) -> None:
        response = self.client.post("/answerset/validate", json={"version": "v1.0", "answers": {}})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["valid"])
        self.assertGreater(len(payload["issues"]), 0)


if __name__ == "__main__":
    unittest.main()
