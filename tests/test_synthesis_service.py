import unittest

from adapters.llm_client import LLMClient
from app.services.synthesis_service import SynthesisService
from domain.models import BIAssessment, PAAssessment


class SynthesisServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SynthesisService(llm_client=LLMClient(dry_run=True))

    def test_synthesize_applies_dependency_heuristic(self) -> None:
        bi = BIAssessment(
            bi_assessment_id="bi-1",
            answer_set_id="as-1",
            score=1.8,
            summary="BI niedrig",
            maturity_level=1,
            level_label="LOW",
            dimension_scores={"BI_D1": 1.0, "BI_D2": 2.4},
            findings={"BI_D1": "Datenbasis fehlt"},
        )
        pa = PAAssessment(
            pa_assessment_id="pa-1",
            answer_set_id="as-1",
            score=3.5,
            summary="PA hoch",
            maturity_level=4,
            level_label="HIGH",
            dimension_scores={"PA_D1": 3.0, "PA_D2": 4.0},
            findings={"PA_D1": "Gute Automatisierungspotenziale"},
        )

        synthesis = self.service.synthesize(bi, pa)

        self.assertEqual(synthesis.answer_set_id, "as-1")
        self.assertIn("Datenfundament", synthesis.priority_focus)
        self.assertIn("KPI", synthesis.recommendation)
        self.assertTrue(synthesis.combined_summary)


if __name__ == "__main__":
    unittest.main()
