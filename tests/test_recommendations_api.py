import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


class RecommendationsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_run_and_finalize_recommendations(self) -> None:
        answer_set_id = f"as-{uuid4().hex[:8]}"
        assessments_payload = {
            "answer_set_id": answer_set_id,
            "use_case_id": f"uc-{uuid4().hex[:8]}",
            "answers": {
                "BI_01": ["ERP", "CRM"],
                "BI_02": 2,
                "BI_03": 2,
                "BI_04": "Teilweise",
                "BI_05": "Unregelmäßig/ad hoc",
                "BI_06": "Wöchentlich",
                "BI_07": 2,
                "BI_08": "Nein",
                "BI_09": 2,
                "BI_10": 2,
                "PA_01": 2,
                "PA_02": 2,
                "PA_03": "Häufig",
                "PA_04": 2,
                "PA_05": 2,
                "PA_06": "4–5",
                "PA_07": 2,
                "PA_08": 2,
                "PA_09": 2,
                "PA_10": "Keine",
            },
        }
        run_assessment = self.client.post("/assessments/run", json=assessments_payload)
        self.assertEqual(run_assessment.status_code, 200)

        run_reco = self.client.post("/recommendations/run", json={"answer_set_id": answer_set_id})
        self.assertEqual(run_reco.status_code, 200)
        catalog = run_reco.json()
        self.assertIn("catalog_id", catalog)
        self.assertGreater(len(catalog["measures"]), 0)

        first_measure = catalog["measures"][0]
        finalize_payload = {
            "selections": [
                {"measure_id": first_measure["measure_id"], "selected": True, "final_priority": 1},
            ]
        }
        finalize = self.client.post(f"/recommendations/{catalog['catalog_id']}/finalize", json=finalize_payload)
        self.assertEqual(finalize.status_code, 200)
        finalized = finalize.json()
        self.assertEqual(finalized["catalog_id"], catalog["catalog_id"])
        self.assertIn(first_measure["measure_id"], finalized["selected_measure_ids"])


if __name__ == "__main__":
    unittest.main()
