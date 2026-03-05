import unittest

from app.services.measure_item_adapter import build_measures_by_bucket
from domain.models import CatalogStatus, Measure, MeasureCatalog, MeasureCategory


class MeasureItemAdapterTestCase(unittest.TestCase):
    def test_adapter_enriches_missing_fields_from_template(self) -> None:
        measure = Measure(
            measure_id="m-1",
            initiative_id="INIT-BI-GOV-01",
            title="Maßnahme",
            description="",
            category=MeasureCategory.GOVERNANCE,
            dimension="BI_D1",
            priority_score=2.0,
            suggested_priority=1,
            deliverables=[],
            kpi={},
            evidence={
                "trigger_items": [
                    {"item_id": "DA_01", "question_text": "Sind Rollen definiert?", "answer": 1, "deficit_score": 1.0, "dimension_id": "BI_D1"}
                ]
            },
        )
        catalog = MeasureCatalog(catalog_id="c-1", title="t", status=CatalogStatus.DRAFT, measures=[measure])
        payload = build_measures_by_bucket(catalog)

        item = payload["now"][0]
        self.assertEqual(len(item["deliverables"]), 3)
        self.assertTrue(item["kpi"].get("name"))
        self.assertTrue(item["trigger_items"][0]["label"])
        self.assertIn("deficit", item["rationale"])

    def test_adapter_creates_fallback_trigger_when_missing(self) -> None:
        measure = Measure(
            measure_id="m-2",
            initiative_id="INIT-PA-GOV-01",
            title="Maßnahme",
            description="",
            category=MeasureCategory.GOVERNANCE,
            dimension="PA_D1",
            priority_score=1.0,
            suggested_priority=1,
            deliverables=[],
            kpi={},
            evidence={"severity": 0.8, "trigger_items": []},
        )
        catalog = MeasureCatalog(catalog_id="c-2", title="t", status=CatalogStatus.DRAFT, measures=[measure])
        payload = build_measures_by_bucket(catalog)

        item = payload["now"][0]
        self.assertEqual(len(item["trigger_items"]), 1)
        self.assertTrue(item["trigger_items"][0]["item_id"].endswith("_FALLBACK"))
        self.assertEqual(item["trigger_items"][0]["answer_value"], "aus Dimensionsscore abgeleitet")


if __name__ == "__main__":
    unittest.main()
