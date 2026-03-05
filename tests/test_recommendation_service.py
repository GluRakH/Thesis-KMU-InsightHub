import unittest

from adapters.llm_client import LLMClient
from app.services.initiative_templates import TemplateValidationError, load_templates
from app.services.recommendation_service import RecommendationService
from domain.models import Synthesis


class RecommendationServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RecommendationService(llm_client=LLMClient(dry_run=True))

    def test_yaml_loader_and_schema_validation(self) -> None:
        registry, version = load_templates()
        self.assertTrue(registry)
        self.assertNotEqual(version, "default")
        self.assertTrue(all(len(item.deliverables) == 3 for item in registry.values()))

    def test_priority_score_not_zero(self) -> None:
        synthesis = Synthesis(synthesis_id="syn-1", answer_set_id="as-1", bi_assessment_id="bi-1", pa_assessment_id="pa-1", recommendation="r")
        catalog = self.service.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label="L1",
            pa_maturity_label="L1",
            bi_dimension_scores={"BI_D1": 20.0, "BI_D2": 30.0, "BI_D3": 40.0},
            pa_dimension_scores={"PA_D1": 25.0, "PA_D2": 35.0, "PA_D3": 45.0},
            answers={"DA_01": 1, "DA_02": 2, "PA_01": 1, "PA_02": 2},
        )
        self.assertTrue(all(item.priority_score > 0 for item in catalog.measures))

    def test_bucket_rule_now_has_entry(self) -> None:
        synthesis = Synthesis(synthesis_id="syn-2", answer_set_id="as-2", bi_assessment_id="bi-2", pa_assessment_id="pa-2", recommendation="r")
        catalog = self.service.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label="L2",
            pa_maturity_label="L2",
            bi_dimension_scores={"BI_D1": 40.0, "BI_D2": 50.0, "BI_D3": 60.0},
            pa_dimension_scores={"PA_D1": 35.0, "PA_D2": 45.0, "PA_D3": 55.0},
            answers={"DA_01": 2, "DA_02": 2, "PA_01": 2, "PA_02": 2},
        )
        now_items = [m for m in catalog.measures if (m.priority or {}).get("bucket") == "now"]
        self.assertGreaterEqual(len(now_items), 1)


    def test_measure_generation_stays_deterministic_when_llm_flag_enabled(self) -> None:
        synthesis = Synthesis(
            synthesis_id="syn-llm",
            answer_set_id="as-llm",
            bi_assessment_id="bi-llm",
            pa_assessment_id="pa-llm",
            recommendation="r",
            priority_focus="Datenqualität zuerst",
            context_restrictions=["begrenzte Ressourcen"],
        )
        catalog = self.service.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label="L1",
            pa_maturity_label="L1",
            bi_dimension_scores={"BI_D1": 20.0, "BI_D2": 30.0, "BI_D3": 40.0},
            pa_dimension_scores={"PA_D1": 25.0, "PA_D2": 35.0, "PA_D3": 45.0},
            use_llm_texts=True,
            answers={"DA_01": 1, "DA_02": 2, "PA_01": 1, "PA_02": 2},
        )
        self.assertTrue(all("LLM-Impuls:" not in item.description for item in catalog.measures))
        self.assertTrue(all(not (item.evidence or {}).get("llm_impulse") for item in catalog.measures))


    def test_trigger_items_include_question_text_labels(self) -> None:
        evidence, _ = self.service._extract_evidence_by_dimension({"DA_01": 1, "DA_02": 2})
        normalized = self.service._normalize_trigger_items("BI_D1", evidence.get("BI_D1", []), {"DA_01": 1, "DA_02": 2})

        self.assertTrue(normalized)
        first_label = str(normalized[0].get("label") or "")
        self.assertTrue(first_label)
        self.assertNotEqual(first_label, normalized[0].get("item_id"))

    def test_evidence_extraction_range_and_size(self) -> None:
        evidence, _ = self.service._extract_evidence_by_dimension({"DA_01": 1, "DA_02": 2, "DA_03": 3})
        normalized = self.service._normalize_trigger_items("BI_D1", evidence.get("BI_D1", []), {"DA_01": 1, "DA_02": 2, "DA_03": 3})
        self.assertGreaterEqual(len(normalized), 2)
        self.assertLessEqual(len(normalized), 3)
        self.assertTrue(all(0.0 <= float(item["deficit_score"]) <= 1.0 for item in normalized))


if __name__ == "__main__":
    unittest.main()
