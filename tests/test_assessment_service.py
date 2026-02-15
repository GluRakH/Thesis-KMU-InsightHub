import unittest

from app.services.assessment_service import AssessmentService


class AssessmentServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AssessmentService()

    def test_compute_bi_assessment(self) -> None:
        answers = {
            "BI_01": ["ERP", "CRM", "Data Warehouse"],
            "BI_02": 4,
            "BI_03": 3,
            "BI_04": "Ja",
            "BI_05": "Regelmäßig und standardisiert",
            "BI_06": "Täglich",
            "BI_07": 4,
            "BI_08": "Teilweise",
            "BI_09": 3,
            "BI_10": 4,
        }

        result = self.service.compute_bi_assessment("as-1", answers)

        self.assertEqual(result.answer_set_id, "as-1")
        self.assertGreaterEqual(result.score, 0)
        self.assertIn(result.maturity_level, [1, 2, 3, 4, 5])
        self.assertEqual(set(result.dimension_scores.keys()), {"BI_D1", "BI_D2", "BI_D3"})

    def test_compute_pa_assessment(self) -> None:
        answers = {
            "PA_01": 4,
            "PA_02": 3,
            "PA_03": "Gelegentlich",
            "PA_04": 4,
            "PA_05": 3,
            "PA_06": "2–3",
            "PA_07": 4,
            "PA_08": 3,
            "PA_09": 4,
            "PA_10": "Erste Piloten",
        }

        result = self.service.compute_pa_assessment("as-2", answers)

        self.assertEqual(result.answer_set_id, "as-2")
        self.assertGreaterEqual(result.score, 0)
        self.assertIn(result.maturity_level, [1, 2, 3, 4, 5])
        self.assertEqual(set(result.dimension_scores.keys()), {"PA_D1", "PA_D2", "PA_D3"})


if __name__ == "__main__":
    unittest.main()
