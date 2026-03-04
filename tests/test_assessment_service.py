import unittest

from app.services.assessment_service import AssessmentService, QuestionScoringConfig


class AssessmentServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AssessmentService()

    def test_compute_bi_assessment(self) -> None:
        answers = {qid: 4 for qid in [
            "DA_01", "DA_02", "DA_03", "DA_04", "DA_05", "DA_06", "DA_07", "DA_08", "DA_09", "DA_10", "DA_11", "DA_12", "COUP_01"
        ]}

        result = self.service.compute_bi_assessment("as-1", answers)

        self.assertEqual(result.answer_set_id, "as-1")
        self.assertGreaterEqual(result.score, 0)
        self.assertIn(result.maturity_level, [1, 2, 3, 4])
        self.assertEqual(set(result.dimension_scores.keys()), {"BI_D1", "BI_D2", "BI_D3"})
        self.assertEqual(set(result.dimension_levels.keys()), {"BI_D1", "BI_D2", "BI_D3"})

    def test_compute_pa_assessment(self) -> None:
        answers = {qid: 3 for qid in ["PA_01", "PA_02", "PA_03", "PA_04", "PA_05", "PA_06", "PA_07", "PA_08", "COUP_02", "COUP_03", "COUP_04"]}

        result = self.service.compute_pa_assessment("as-2", answers)

        self.assertEqual(result.answer_set_id, "as-2")
        self.assertGreaterEqual(result.score, 0)
        self.assertIn(result.maturity_level, [1, 2, 3, 4])
        self.assertEqual(set(result.dimension_scores.keys()), {"PA_D1", "PA_D2", "PA_D3"})


    def test_critical_dimension_evidence_is_included(self) -> None:
        answers = {
            "DA_01": 1, "DA_02": 1, "DA_03": 2, "DA_04": 2,
            "DA_05": 5, "DA_06": 5, "DA_07": 5, "DA_08": 5,
            "DA_09": 5, "DA_10": 5, "DA_11": 5, "DA_12": 5, "COUP_01": 5,
        }
        result = self.service.compute_bi_assessment("as-3", answers)
        self.assertEqual(result.critical_dimension_id, "BI_D1")
        self.assertGreater(result.critical_dimension_severity, 0.0)
        self.assertGreaterEqual(len(result.critical_dimension_top_items), 2)

    def test_score_rule_scale_to_100(self) -> None:
        config = QuestionScoringConfig(type="scale_to_100")
        self.assertEqual(self.service._score_answer(3, config), 50.0)

    def test_unknown_scoring_type_raises(self) -> None:
        config = QuestionScoringConfig(type="does_not_exist")
        with self.assertRaises(ValueError):
            self.service._score_answer(1, config)


if __name__ == "__main__":
    unittest.main()
