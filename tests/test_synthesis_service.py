import unittest

from adapters.llm_client import LLMClient
from app.services.synthesis_service import SynthesisService
from domain.models import BIAssessment, PAAssessment


class SynthesisServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SynthesisService(llm_client=LLMClient(dry_run=True))

    @staticmethod
    def _bi(score: float) -> BIAssessment:
        return BIAssessment(
            bi_assessment_id="bi-1",
            answer_set_id="as-1",
            score=score,
            summary="BI",
            maturity_level=2,
            level_label="MEDIUM",
            dimension_scores={"BI_D1": 1.0, "BI_D2": 2.4},
            findings={"BI_D1": "Datenbasis fehlt"},
            questionnaire_version="v1.0",
            scoring_version="v1.0",
        )

    @staticmethod
    def _pa(score: float) -> PAAssessment:
        return PAAssessment(
            pa_assessment_id="pa-1",
            answer_set_id="as-1",
            score=score,
            summary="PA",
            maturity_level=3,
            level_label="MEDIUM",
            dimension_scores={"PA_D1": 3.0, "PA_D2": 4.0},
            findings={"PA_D1": "Gute Automatisierungspotenziale"},
            questionnaire_version="v1.0",
            scoring_version="v1.0",
        )

    def test_synthesize_applies_bi_first_rule(self) -> None:
        synthesis = self.service.synthesize(self._bi(1.8), self._pa(3.5))

        self.assertIn("Datenfundament", synthesis.priority_focus)
        self.assertEqual(synthesis.questionnaire_version, "v1.0")
        self.assertEqual(synthesis.scoring_version, "v1.0")
        self.assertTrue(synthesis.llm_model)

    def test_synthesize_applies_pa_first_rule(self) -> None:
        synthesis = self.service.synthesize(self._bi(3.4), self._pa(1.9))

        self.assertIn("Prozessstandardisierung", synthesis.priority_focus)

    def test_synthesize_applies_balanced_rule(self) -> None:
        synthesis = self.service.synthesize(self._bi(2.8), self._pa(2.7))

        self.assertIn("Parallelisierung", synthesis.priority_focus)
        self.assertIn("KPI", synthesis.recommendation)


if __name__ == "__main__":
    unittest.main()
