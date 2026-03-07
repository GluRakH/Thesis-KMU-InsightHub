import unittest

from adapters.llm_client import LLMClient
from app.services.synthesis_service import SynthesisService
from domain.models import BIAssessment, PAAssessment


class SynthesisServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SynthesisService(llm_client=LLMClient(dry_run=True))

    @staticmethod
    def _bi(score: float, maturity_level: int = 2) -> BIAssessment:
        return BIAssessment(
            bi_assessment_id="bi-1",
            answer_set_id="as-1",
            score=score,
            summary="BI",
            maturity_level=maturity_level,
            level_label=f"L{maturity_level}",
            dimension_scores={"BI_D1": 30.0, "BI_D2": 55.0},
            dimension_levels={"BI_D1": "L2", "BI_D2": "L3"},
            findings={"BI_D1": "Datenbasis fehlt"},
            questionnaire_version="v1.0",
            scoring_version="v1.0",
        )

    @staticmethod
    def _pa(score: float, maturity_level: int = 3) -> PAAssessment:
        return PAAssessment(
            pa_assessment_id="pa-1",
            answer_set_id="as-1",
            score=score,
            summary="PA",
            maturity_level=maturity_level,
            level_label=f"L{maturity_level}",
            dimension_scores={"PA_D1": 70.0, "PA_D2": 80.0},
            dimension_levels={"PA_D1": "L3", "PA_D2": "L4"},
            findings={"PA_D1": "Gute Automatisierungspotenziale"},
            questionnaire_version="v1.0",
            scoring_version="v1.0",
        )

    def test_synthesize_applies_bi_first_rule(self) -> None:
        synthesis = self.service.synthesize(self._bi(35), self._pa(70), {"SYN_02": "Budget sehr begrenzt"})

        self.assertEqual(synthesis.priority_focus, "BI-first")
        self.assertEqual(synthesis.context_factors["GLOBAL"], 0.8)

    def test_synthesize_applies_pa_first_rule(self) -> None:
        synthesis = self.service.synthesize(self._bi(70, maturity_level=2), self._pa(35, maturity_level=2))

        self.assertEqual(synthesis.priority_focus, "Automation-first")

    def test_synthesize_applies_balanced_rule(self) -> None:
        synthesis = self.service.synthesize(self._bi(55, maturity_level=2), self._pa(57, maturity_level=2), {"SYN_03": ["Reporting/Monitoring"]})

        self.assertEqual(synthesis.priority_focus, "Balanced")
        self.assertEqual(synthesis.target_objectives, ["Reporting/Monitoring"])

    def test_synthesize_uses_bi_first_for_large_positive_delta(self) -> None:
        synthesis = self.service.synthesize(self._bi(12.92), self._pa(34.72))

        self.assertEqual(synthesis.priority_focus, "BI-first")

    def test_synthesize_keeps_balanced_for_small_score_differences(self) -> None:
        synthesis_up = self.service.synthesize(self._bi(50, maturity_level=2), self._pa(51, maturity_level=2))
        synthesis_down = self.service.synthesize(self._bi(51, maturity_level=2), self._pa(50, maturity_level=2))

        self.assertEqual(synthesis_up.priority_focus, "Balanced")
        self.assertEqual(synthesis_down.priority_focus, "Balanced")

if __name__ == "__main__":
    unittest.main()
