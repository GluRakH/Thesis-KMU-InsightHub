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
            context_factors={"GLOBAL": 1.0},
        )

        catalog = self.service.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label="L2",
            pa_maturity_label="L1",
            bi_dimension_scores={"BI_D1": 20.0, "BI_D2": 45.0, "BI_D3": 65.0},
            pa_dimension_scores={"PA_D1": 25.0, "PA_D2": 30.0, "PA_D3": 55.0},
            bi_dimension_levels={"BI_D1": "L1", "BI_D2": "L2", "BI_D3": "L3"},
            pa_dimension_levels={"PA_D1": "L1", "PA_D2": "L2", "PA_D3": "L3"},
        )

        self.assertEqual(catalog.synthesis_id, "syn-1")
        self.assertEqual(len(catalog.measures), 6)
        self.assertEqual(catalog.measures[0].suggested_priority, 1)
        self.assertTrue(all(item.measure_class for item in catalog.measures))


if __name__ == "__main__":
    unittest.main()
