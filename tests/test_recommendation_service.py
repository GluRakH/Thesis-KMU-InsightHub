from pathlib import Path
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


    def test_templates_deliverables_not_three_errors(self) -> None:
        from tempfile import NamedTemporaryFile
        import json

        broken = {
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "templates": [
                {
                    "template_id": "BROKEN_01",
                    "title": "Broken Template",
                    "category": "governance",
                    "applies_to": {"dimensions": ["BI_D1"]},
                    "goal": "A sufficiently long goal text",
                    "deliverables": ["only one"],
                    "kpi": {
                        "name": "KPI",
                        "baseline_definition": "baseline defined",
                        "target": "target",
                        "measurement": "measurement text",
                        "frequency": "monthly"
                    },
                    "impact": 3,
                    "effort": 2
                }
            ]
        }
        with NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            json.dump(broken, handle)
            path = handle.name

        with self.assertRaises(TemplateValidationError):
            load_templates(Path(path), dev_mode=True)

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
        self.assertTrue(str(normalized[0].get("question_text") or ""))

    def test_evidence_extraction_range_and_size(self) -> None:
        evidence, _ = self.service._extract_evidence_by_dimension({"DA_01": 1, "DA_02": 2, "DA_03": 3})
        normalized = self.service._normalize_trigger_items("BI_D1", evidence.get("BI_D1", []), {"DA_01": 1, "DA_02": 2, "DA_03": 3})
        self.assertGreaterEqual(len(normalized), 2)
        self.assertLessEqual(len(normalized), 3)
        self.assertTrue(all(0.0 <= float(item["deficit_score"]) <= 1.0 for item in normalized))

    def test_deficit_with_invalid_scale_returns_zero_with_warning(self) -> None:
        self.assertEqual(self.service.calculate_deficit_score(3, 5, 5, "higher_is_better"), 0.0)


    def test_missing_direction_still_creates_trigger_items(self) -> None:
        from tempfile import TemporaryDirectory
        import json

        with TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            questionnaire = {
                "questions": [
                    {
                        "id": "Q_1",
                        "text": "Frage ohne Richtung",
                        "scale": {"min": 1, "max": 5},
                    }
                ]
            }
            scoring = {"dimensions": {"BI_D1": {"questions": ["Q_1"]}}}
            (config_dir / "questionnaire_v1.0.json").write_text(json.dumps(questionnaire), encoding="utf-8")
            (config_dir / "scoring_bi_v1.0.json").write_text(json.dumps(scoring), encoding="utf-8")
            (config_dir / "scoring_pa_v1.0.json").write_text(json.dumps({"dimensions": {}}), encoding="utf-8")

            service = RecommendationService(llm_client=LLMClient(dry_run=True), scoring_dir=config_dir)
            evidence, _ = service._extract_evidence_by_dimension({"Q_1": 2})

            self.assertTrue(evidence.get("BI_D1"))
            self.assertEqual(evidence["BI_D1"][0]["direction"], "higher_is_better")

    def test_deficit_score_for_both_directions(self) -> None:
        self.assertEqual(self.service.calculate_deficit_score(2, 1, 5, "higher_is_better"), 0.75)
        self.assertEqual(self.service.calculate_deficit_score(2, 1, 5, "lower_is_better"), 0.25)
    def test_preferred_trigger_items_are_selected_first(self) -> None:
        evidence, _ = self.service._extract_evidence_by_dimension({"DA_01": 1, "DA_02": 2, "DA_03": 3})
        normalized = self.service._normalize_trigger_items(
            "BI_D1", evidence.get("BI_D1", []), {"DA_01": 1, "DA_02": 2, "DA_03": 3}, ["DA_03"]
        )
        self.assertTrue(normalized)
        self.assertEqual(normalized[0].get("item_id"), "DA_03")

    def test_catalog_contains_max_four_measures(self) -> None:
        synthesis = Synthesis(synthesis_id="syn-3", answer_set_id="as-3", bi_assessment_id="bi-3", pa_assessment_id="pa-3", recommendation="r")
        catalog = self.service.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label="L1",
            pa_maturity_label="L1",
            bi_dimension_scores={"BI_D1": 20.0, "BI_D2": 30.0, "BI_D3": 40.0},
            pa_dimension_scores={"PA_D1": 25.0, "PA_D2": 35.0, "PA_D3": 45.0},
            answers={"DA_01": 1, "DA_02": 2, "PA_01": 1, "PA_02": 2},
        )
        self.assertEqual(len(catalog.measures), 4)

    def test_catalog_contains_bi_and_pa_measures_when_both_domains_exist(self) -> None:
        synthesis = Synthesis(synthesis_id="syn-4", answer_set_id="as-4", bi_assessment_id="bi-4", pa_assessment_id="pa-4", recommendation="r")
        catalog = self.service.generate_catalog(
            synthesis=synthesis,
            bi_maturity_label="L2",
            pa_maturity_label="L2",
            bi_dimension_scores={"BI_D1": 10.0, "BI_D2": 11.0, "BI_D3": 12.0},
            pa_dimension_scores={"PA_D1": 80.0, "PA_D2": 81.0, "PA_D3": 82.0},
            answers={"DA_01": 1, "DA_02": 2, "PA_01": 1, "PA_02": 2},
        )
        domains = {"BI" if item.dimension.startswith("BI_") else "PA" if item.dimension.startswith("PA_") else "GLOBAL" for item in catalog.measures}
        self.assertIn("BI", domains)
        self.assertIn("PA", domains)


if __name__ == "__main__":
    unittest.main()
