import unittest

from adapters.llm_client import LLMClient
from app.services.recommendation_service import RecommendationService
from domain.models import Synthesis


class RecommendationServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RecommendationService(llm_client=LLMClient(dry_run=True))

    def test_generate_catalog_from_dimension_level_mapping(self) -> None:
        synthesis = Synthesis(
            synthesis_id="syn-1",
            answer_set_id="as-1",
            bi_assessment_id="bi-1",
            pa_assessment_id="pa-1",
            recommendation="Reco",
            priority_focus="Fokus Datenbasis",
            heuristic_reason="Niedrige BI-Reife",
        )

        catalog = self.service.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label="LOW",
            pa_maturity_label="LOW",
            bi_dimension_scores={"BI_D1": 1.2, "BI_D2": 2.0},
            pa_dimension_scores={"PA_D1": 1.0, "PA_D2": 2.5},
        )

        self.assertEqual(catalog.synthesis_id, "syn-1")
        self.assertGreaterEqual(len(catalog.measures), 2)
        self.assertEqual(catalog.measures[0].suggested_priority, 1)
        self.assertTrue(any(item.dimension.startswith("BI_") for item in catalog.measures))
        self.assertTrue(any(item.dimension.startswith("PA_") for item in catalog.measures))


if __name__ == "__main__":
    unittest.main()
