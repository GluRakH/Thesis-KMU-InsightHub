import unittest

from adapters.llm_client import LLMClient
from app.services.recommendation_service import RecommendationService
from domain.models import Measure, MeasureCategory, Synthesis


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
            answers={"DA_01": 1, "DA_02": 2, "PA_01": 1},
        )

        self.assertEqual(catalog.synthesis_id, "syn-1")
        self.assertEqual(len(catalog.measures), 6)
        self.assertTrue(all(len(item.deliverables) == 3 for item in catalog.measures))
        self.assertTrue(all(item.initiative_id.startswith("INIT-") for item in catalog.measures))

    def test_deficit_score_normalization(self) -> None:
        self.assertEqual(self.service.calculate_deficit_score(1, 1, 5), 1.0)
        self.assertEqual(self.service.calculate_deficit_score(5, 1, 5), 0.0)
        self.assertIsNone(self.service.calculate_deficit_score(None, 1, 5))

    def test_criticality_weight_rankings(self) -> None:
        weights = self.service._criticality_weights({"BI_D1": 20, "BI_D2": 30, "BI_D3": 40})
        self.assertEqual(weights["BI_D1"], 1.3)
        self.assertEqual(weights["BI_D2"], 1.15)
        self.assertEqual(weights["BI_D3"], 1.0)

    def test_gap_weight_default_and_clamp(self) -> None:
        self.assertEqual(self.service._gap_weight("L1", "BI", {}), 1.3)
        self.assertEqual(self.service._gap_weight("L1", "BI", {"BI": 10}), 1.6)
        self.assertEqual(self.service._gap_weight("L4", "BI", {"BI": 2}), 1.0)

    def test_priority_score_effort_zero_is_protected(self) -> None:
        score = self.service.calculate_priority_score(impact=4, effort=0, criticality_weight=1.3, gap_weight=1.15)
        self.assertAlmostEqual(score, 5.98)

    def test_dependency_bucketing_with_gate(self) -> None:
        measures = [
            Measure(
                measure_id="m1",
                initiative_id="INIT-BI-GOVERNANCE-01",
                title="Governance",
                description="",
                category=MeasureCategory.GOVERNANCE,
                dimension="BI_D1",
                impact=5,
                effort=2,
                priority_score=3.0,
            ),
            Measure(
                measure_id="m2",
                initiative_id="INIT-BI-TECHNICAL-01",
                title="Tech",
                description="",
                category=MeasureCategory.TECHNICAL,
                dimension="BI_D2",
                impact=5,
                effort=2,
                priority_score=4.0,
                dependencies=["INIT-BI-GOVERNANCE-01"],
            ),
        ]

        buckets = self.service._build_now_next_later(measures)
        self.assertEqual(buckets["now"], ["INIT-BI-GOVERNANCE-01"])
        self.assertEqual(buckets["next"], ["INIT-BI-TECHNICAL-01"])


if __name__ == "__main__":
    unittest.main()
