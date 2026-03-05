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
                    "kpi": {"name": "Owner-Abdeckung", "target": ">=90%", "measurement": "Monatliches Audit", "frequency": "monthly"},
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

    def test_build_catalog_summary_fills_missing_llm_measure_details(self) -> None:
        payload = {
            "now": [
                self.payload["now"][0],
                {
                    "initiative_id": "INIT-BI-DQ-02",
                    "title": "Datenqualitätsregeln etablieren",
                    "dimension": "BI_D2",
                    "priority": 2,
                    "dependencies": [],
                    "deliverables": ["Regelwerk", "Dashboard", "Review"],
                    "kpi": {"name": "DQ-Fehlerquote", "target": "<5%", "measurement": "Wöchentlich", "frequency": "weekly"},
                    "trigger_items": [{"item_id": "DA_02", "label": "DA_02"}],
                    "rationale": "Für BI_D2 priorisiert, weil DQ-Defizite dominieren.",
                },
            ],
            "next": [],
            "later": [],
        }

        class PartialDetailsLLM:
            def summarize_measure_catalog(self, focus: str, measures_by_bucket: dict[str, list[dict]]) -> dict:
                return {
                    "headline": "LLM Headline",
                    "executive_summary": "LLM Summary",
                    "now": ["Kurztext 1", "Kurztext 2"],
                    "next": [],
                    "later": [],
                    "risks_and_dependencies": [],
                    "first_30_days": [],
                    "measure_details": {
                        "now": [
                            {
                                "title": "Data Governance Betriebsmodell aufbauen",
                                "deliverables": ["LLM-RACI"],
                                "kpi_summary": "LLM KPI",
                                "evidence_summary": "LLM Evidenz",
                                "trigger_refs": ["DA_01"],
                            }
                        ],
                        "next": [],
                        "later": [],
                    },
                }

        summary = build_catalog_summary(
            focus="Governance stabilisieren",
            measures_by_bucket=payload,
            llm_client=PartialDetailsLLM(),
            use_llm_texts=True,
        )

        now_details = summary.get("measure_details", {}).get("now", [])
        self.assertEqual(len(now_details), 2)
        self.assertEqual(now_details[0].get("deliverables"), ["LLM-RACI"])
        self.assertEqual(now_details[1].get("title"), "Datenqualitätsregeln etablieren")


    def test_llm_invalid_kpi_summary_falls_back_to_deterministic(self) -> None:
        class InvalidKpiLLM:
            def summarize_measure_catalog(self, focus: str, measures_by_bucket: dict[str, list[dict]]) -> dict:
                return {
                    "headline": "LLM Headline",
                    "executive_summary": "LLM Summary",
                    "now": ["Kurztext"],
                    "next": [],
                    "later": [],
                    "risks_and_dependencies": [],
                    "first_30_days": [],
                    "measure_details": {
                        "now": [
                            {
                                "title": "Data Governance Betriebsmodell aufbauen",
                                "deliverables": ["D1", "D2", "D3"],
                                "kpi_summary": "INVALID ITEM - parse error",
                                "evidence_summary": "n/a",
                                "trigger_refs": ["x"],
                            }
                        ],
                        "next": [],
                        "later": [],
                    },
                }

        summary = build_catalog_summary(
            focus="Governance stabilisieren",
            measures_by_bucket=self.payload,
            llm_client=InvalidKpiLLM(),
            use_llm_texts=True,
        )

        detail = summary["measure_details"]["now"][0]
        self.assertIn("Owner-Abdeckung", detail["kpi_summary"])
        self.assertNotIn("INVALID", detail["kpi_summary"])
        self.assertIn("Dimension BI_D1", detail["evidence_summary"])

    def test_deterministic_trigger_refs_include_answer_and_deficit(self) -> None:
        payload = {
            "now": [
                {
                    "initiative_id": "INIT-BI-GOV-01",
                    "title": "Data Governance Betriebsmodell aufbauen",
                    "dimension": "BI_D1",
                    "priority": 1,
                    "dependencies": [],
                    "deliverables": ["RACI", "Gremium", "Policy"],
                    "kpi": {"name": "Owner-Abdeckung", "target": ">=90%", "measurement": "Monatliches Audit", "frequency": "monthly"},
                    "trigger_items": [{"item_id": "DA_01", "label": "Ownership", "answer": 2, "deficit_score": 0.75}],
                    "rationale": "Für BI_D1 priorisiert.",
                }
            ],
            "next": [],
            "later": [],
        }
        summary = build_catalog_summary(focus="x", measures_by_bucket=payload)
        ref = summary["measure_details"]["now"][0]["trigger_refs"][0]
        self.assertIn("answer=2", ref)
        self.assertIn("deficit=0.75", ref)

    def test_invalid_item_is_marked_invalid(self) -> None:
        invalid_payload = {
            "now": [
                {
                    "initiative_id": "INIT-1",
                    "title": "Broken",
                    "dimension": "BI_D1",
                    "priority": 1,
                    "dependencies": [],
                    "deliverables": ["only one"],
                    "kpi": {},
                    "trigger_items": [],
                    "rationale": "",
                }
            ],
            "next": [],
            "later": [],
        }
        summary = build_catalog_summary(focus="x", measures_by_bucket=invalid_payload)
        kpi_summary = summary["measure_details"]["now"][0]["kpi_summary"]
        self.assertIn("INVALID ITEM", kpi_summary)
        self.assertNotIn("KPI nicht definiert", kpi_summary)

    def test_invalid_item_raises_in_dev_mode(self) -> None:
        invalid_payload = {"now": [{"initiative_id": "INIT-1", "title": "Broken", "deliverables": [], "kpi": {}, "trigger_items": []}], "next": [], "later": []}
        with self.assertRaises(ValueError):
            build_catalog_summary(focus="x", measures_by_bucket=invalid_payload, dev_mode=True)


if __name__ == "__main__":
    unittest.main()
