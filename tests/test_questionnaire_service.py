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
        self.assertEqual(len(questionnaire.questions), 36)

    def test_validate_answer_set_detects_missing_required_answers(self) -> None:
        result = self.service.validate_answer_set("v1.0", {})

        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "REQUIRED_MISSING" for issue in result.issues))

    def test_validate_answer_set_accepts_valid_answers(self) -> None:
        answers = self._build_valid_answers()
        result = self.service.validate_answer_set("v1.0", answers)

        self.assertTrue(result.valid)
        self.assertEqual(result.issues, [])

    def test_validate_answer_set_detects_invalid_scale_type(self) -> None:
        answers = self._build_valid_answers()
        answers["DA_02"] = "hoch"

        result = self.service.validate_answer_set("v1.0", answers)

        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "INVALID_SCALE_TYPE" for issue in result.issues))

    def test_validate_answer_set_adds_consistency_warning(self) -> None:
        answers = self._build_valid_answers()
        answers["DA_03"] = 5
        answers["COUP_03"] = 1

        result = self.service.validate_answer_set("v1.0", answers)

        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "CONSISTENCY_WARNING" for issue in result.issues))


class QuestionnaireApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def _build_valid_answers(self) -> dict[str, object]:
        response = self.client.get("/questionnaire", params={"version": "v1.0"})
        questionnaire = response.json()
        answers: dict[str, object] = {}
        for question in questionnaire["questions"]:
            if not question.get("required"):
                continue
            if question["type"] == "TEXT":
                answers[question["id"]] = "Test"
            elif question["type"] == "SINGLE_CHOICE":
                answers[question["id"]] = question["options"][0]
            elif question["type"] == "MULTI_CHOICE":
                answers[question["id"]] = [question["options"][0]]
            elif question["type"] == "SCALE":
                answers[question["id"]] = question["scale"]["min"]
        return answers

    def test_get_questionnaire_route(self) -> None:
        response = self.client.get("/questionnaire", params={"version": "v1.0"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["version"], "v1.0")
        self.assertEqual(len(payload["questions"]), 36)

    def test_validate_route(self) -> None:
        use_case = self.client.post(
            "/usecases",
            json={"name": "Validierung", "description": "Test", "use_case_type": "combined"},
        ).json()
        saved = self.client.post(
            "/answersets",
            json={"version": "v1.0", "use_case_id": use_case["use_case_id"], "answers": self._build_valid_answers()},
        )
        self.assertEqual(saved.status_code, 200)

        response = self.client.post(f"/answersets/{saved.json()['answer_set_id']}/validate")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], "locked")

    def test_run_assessments_and_synthesis_routes(self) -> None:
        use_case = self.client.post(
            "/usecases",
            json={"name": "Assessment", "description": "Test", "use_case_type": "combined"},
        ).json()
        save_response = self.client.post(
            "/answersets",
            json={"version": "v1.0", "use_case_id": use_case["use_case_id"], "answers": self._build_valid_answers()},
        )
        self.assertEqual(save_response.status_code, 200)
        answer_set_id = save_response.json()["answer_set_id"]

        run_response = self.client.post(f"/assessments/{answer_set_id}")

        self.assertEqual(run_response.status_code, 200)
        payload = run_response.json()
        self.assertIn("bi_assessment", payload)
        self.assertIn("pa_assessment", payload)
        self.assertIn("maturity_level", payload["bi_assessment"])
        self.assertIn("maturity_level", payload["pa_assessment"])

        run_synthesis = self.client.post(f"/synthesis/{answer_set_id}")

        self.assertEqual(run_synthesis.status_code, 200)
        synthesis_payload = run_synthesis.json()
        self.assertEqual(synthesis_payload["answer_set_id"], answer_set_id)
        self.assertIn("combined_summary", synthesis_payload)


if __name__ == "__main__":
    unittest.main()
