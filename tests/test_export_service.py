import unittest

from app.services.export_service import build_export_payload, payload_to_json, payload_to_markdown
from domain.models import CatalogStatus, Measure, MeasureCatalog, MeasureCategory


class ExportServiceTestCase(unittest.TestCase):
    def test_export_contains_run_id_and_rules(self) -> None:
        payload = build_export_payload(
            pipeline={"bi": {"score": 40.0}, "pa": {"score": 50.0}, "synthesis": {"answer_set_id": "as-1"}},
            answers={"DA_01": 2},
            catalog=None,
            rules_applied={"gates": [{"rule": "governance_first", "blocking_measure": "INIT-BI-GOVERNANCE-01", "affected_measures": ["INIT-BI-DATA-01"]}], "thresholds": {"governance": 0.6, "data_quality": 0.55}},
        )
        self.assertIn("run_id", payload)
        self.assertEqual(payload["rules_applied"]["thresholds"]["governance"], 0.6)

    def test_markdown_contains_evidence_trigger_and_sequence(self) -> None:
        catalog = MeasureCatalog(
            catalog_id="cat-1",
            title="t",
            status=CatalogStatus.DRAFT,
            synthesis_id="syn-1",
            measures=[
                Measure(
                    measure_id="m1",
                    initiative_id="INIT-BI-GOVERNANCE-01",
                    title="Gov",
                    description="desc",
                    category=MeasureCategory.GOVERNANCE,
                    dimension="BI_D1",
                    priority_score=2.0,
                    suggested_priority=1,
                    priority={"bucket": "now", "sequence_reason": "Governance vor Skalierung"},
                    deliverables=["d1", "d2", "d3"],
                    kpi={"name": "K", "target": ">=90%", "measurement": "Messung"},
                    evidence={"dimension_id": "BI_D1", "severity": 0.7, "trigger_items": [{"item_id": "DA_01", "answer": 1, "deficit_score": 1.0}]},
                )
            ],
        )
        payload = build_export_payload(pipeline={"bi": {"score": 20}, "pa": {"score": 30}, "synthesis": {}}, answers={}, catalog=catalog)
        md = payload_to_markdown(payload)
        self.assertIn("Evidenz-Trigger: DA_01", md)
        self.assertIn("Sequenz: Governance vor Skalierung", md)

    def test_payload_json(self) -> None:
        raw = payload_to_json({"a": 1})
        self.assertIn('"a": 1', raw)


if __name__ == "__main__":
    unittest.main()
