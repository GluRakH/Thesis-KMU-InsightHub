import unittest

from adapters.llm_client import LLMClient
from app.services.catalog_summary_service import build_catalog_summary


class CatalogSummaryServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "now": [
                {
                    "initiative_id": "INIT-BI-GOV-01",
                    "title": "Data Governance Betriebsmodell aufbauen",
                    "dimension": "BI_D1",
                    "priority": 1,
                    "dependencies": [],
                    "deliverables": ["RACI", "Gremium", "Policy"],
                    "kpi": {"name": "Owner-Abdeckung", "target": ">=90%", "measurement": "Monatliches Audit"},
                    "trigger_items": [{"item_id": "DA_01", "label": "DA_01"}],
                    "rationale": "Für BI_D1 priorisiert, weil Defizite in DA_01 dominieren.",
                }
            ],
            "next": [],
            "later": [],
        }

    def test_build_catalog_summary_deterministic_default(self) -> None:
        summary = build_catalog_summary(
            focus="Governance stabilisieren",
            measures_by_bucket=self.payload,
        )
        self.assertEqual(summary.get("generation_mode"), "deterministic")
        self.assertIn("Governance stabilisieren", summary.get("executive_summary", ""))
        self.assertTrue(summary.get("measure_details", {}).get("now"))

    def test_build_catalog_summary_uses_llm_for_texts_only(self) -> None:
        summary = build_catalog_summary(
            focus="Governance stabilisieren",
            measures_by_bucket=self.payload,
            llm_client=LLMClient(dry_run=True),
            use_llm_texts=True,
        )
        self.assertEqual(summary.get("generation_mode"), "deterministic+llm_text")
        self.assertTrue(summary.get("headline"))
        self.assertTrue(summary.get("measure_details", {}).get("now"))


if __name__ == "__main__":
    unittest.main()
