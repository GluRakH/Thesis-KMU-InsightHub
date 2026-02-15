import unittest

from fastapi.testclient import TestClient

from app.api.main import app


class RecommendationsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_end_to_end_minimal_api(self) -> None:
        use_case = self.client.post(
            "/usecases",
            json={"name": "E2E", "description": "End-to-End Test", "use_case_type": "combined"},
        )
        self.assertEqual(use_case.status_code, 200)
        use_case_id = use_case.json()["use_case_id"]

        questionnaire = self.client.get("/questionnaire", params={"version": "v1.0"}).json()
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

        saved_answerset = self.client.post(
            "/answersets",
            json={"version": "v1.0", "use_case_id": use_case_id, "answers": answers},
        )
        self.assertEqual(saved_answerset.status_code, 200)
        answer_set_id = saved_answerset.json()["answer_set_id"]

        validate = self.client.post(f"/answersets/{answer_set_id}/validate")
        self.assertEqual(validate.status_code, 200)
        self.assertTrue(validate.json()["valid"])

        run_assessment = self.client.post(f"/assessments/{answer_set_id}")
        self.assertEqual(run_assessment.status_code, 200)

        run_synthesis = self.client.post(f"/synthesis/{answer_set_id}")
        self.assertEqual(run_synthesis.status_code, 200)

        run_catalog = self.client.post(f"/catalog/{answer_set_id}", json={"use_llm_texts": False})
        self.assertEqual(run_catalog.status_code, 200)
        catalog = run_catalog.json()
        self.assertIn("catalog_id", catalog)
        self.assertGreater(len(catalog["measures"]), 0)

        first_measure = catalog["measures"][0]
        finalize_payload = {
            "selections": [
                {"measure_id": first_measure["measure_id"], "selected": True, "final_priority": 1},
            ]
        }
        finalize = self.client.post(f"/catalog/{catalog['catalog_id']}/selection", json=finalize_payload)
        self.assertEqual(finalize.status_code, 200)

        aggregated = self.client.get(f"/results/{use_case_id}")
        self.assertEqual(aggregated.status_code, 200)
        payload = aggregated.json()
        self.assertEqual(payload["use_case"]["use_case_id"], use_case_id)
        self.assertGreaterEqual(len(payload["results"]), 1)


if __name__ == "__main__":
    unittest.main()
