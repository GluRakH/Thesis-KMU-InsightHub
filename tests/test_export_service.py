import random
import unittest
from datetime import date, datetime, timezone

from app.services.export_service import build_export_payload, payload_to_json, payload_to_markdown
from domain.models import CatalogStatus, Measure, MeasureCatalog, MeasureCategory


class ExportServiceTestCase(unittest.TestCase):
    def test_export_v11_with_random_answers_is_stable(self) -> None:
        answers = {f"DA_{idx:02d}": random.randint(1, 5) for idx in range(1, 13)}
        pipeline = {
            "bi": {"summary": "BI", "dimension_scores": {"BI_D1": 30.0, "BI_D2": 50.0}},
            "pa": {"summary": "PA", "dimension_scores": {"PA_D1": 35.0, "PA_D2": 55.0}},
            "synthesis": {"combined_summary": "combo", "recommendation": "reco"},
        }

        payload = build_export_payload(pipeline=pipeline, answers=answers, catalog=None, export_version="1.1.0")
        markdown = payload_to_markdown(payload)
        raw_json = payload_to_json(payload)

        self.assertEqual(payload["export_version"], "1.1.0")
        self.assertIn("Export Version: 1.1.0", markdown)
        self.assertIn('"export_version": "1.1.0"', raw_json)


    def test_export_v11_fills_missing_measure_fields(self) -> None:
        pipeline = {
            "bi": {"summary": "BI", "dimension_scores": {"BI_D1": 30.0}},
            "pa": {"summary": "PA", "dimension_scores": {"PA_D1": 35.0}},
            "synthesis": {"combined_summary": "combo", "recommendation": "reco"},
        }
        catalog = MeasureCatalog(
            catalog_id="cat-1",
            title="Test",
            status=CatalogStatus.DRAFT,
            synthesis_id="syn-1",
            measures=[
                Measure(
                    measure_id="mea-1",
                    initiative_id="",
                    title="",
                    description="d",
                    category=MeasureCategory.TECHNICAL,
                    impact=3,
                    effort=2,
                    priority_score=1.5,
                )
            ],
        )

        payload = build_export_payload(pipeline=pipeline, answers={}, catalog=catalog, export_version="1.1.0")
        markdown = payload_to_markdown(payload)

        self.assertIn("Ohne Titel", markdown)
        self.assertIn("PriorityScore=1.5", markdown)

    def test_export_v11_derives_legacy_priority_and_bucket_values(self) -> None:
        pipeline = {
            "bi": {"summary": "BI", "dimension_scores": {"BI_D1": 30.0}},
            "pa": {"summary": "PA", "dimension_scores": {"PA_D1": 35.0}},
            "synthesis": {"combined_summary": "combo", "recommendation": "reco"},
        }
        catalog = MeasureCatalog(
            catalog_id="cat-legacy",
            title="Legacy",
            status=CatalogStatus.DRAFT,
            synthesis_id="syn-legacy",
            measures=[
                Measure(
                    measure_id="mea-1",
                    title="M1",
                    description="d",
                    category=MeasureCategory.TECHNICAL,
                    dimension="BI_D1",
                    impact=5,
                    effort=2,
                    suggested_priority=1,
                ),
                Measure(
                    measure_id="mea-2",
                    title="M2",
                    description="d",
                    category=MeasureCategory.TECHNICAL,
                    dimension="PA_D1",
                    impact=3,
                    effort=3,
                    suggested_priority=3,
                ),
            ],
        )

        payload = build_export_payload(pipeline=pipeline, answers={}, catalog=catalog, export_version="1.1.0")
        markdown = payload_to_markdown(payload)

        self.assertIn("### NOW", markdown)
        self.assertIn("### NEXT", markdown)
        self.assertIn("PriorityScore=2.5", markdown)
        self.assertIn("Target: Mindestwert >= aktueller Baseline", markdown)


    def test_export_v12_includes_compact_evidence_and_measure_details(self) -> None:
        pipeline = {
            "bi": {
                "summary": "BI",
                "critical_dimension_id": "BI_D1",
                "critical_dimension_severity": 0.72,
                "critical_dimension_top_items": [{"item_id": "DA_01", "answer": 1, "deficit_score": 1.0}],
            },
            "pa": {
                "summary": "PA",
                "critical_dimension_id": "PA_D1",
                "critical_dimension_severity": 0.64,
                "critical_dimension_top_items": [{"item_id": "PA_01", "answer": 2, "deficit_score": 0.75}],
            },
            "synthesis": {"combined_summary": "combo", "recommendation": "reco"},
        }
        catalog = MeasureCatalog(
            catalog_id="cat-2",
            title="Test",
            status=CatalogStatus.DRAFT,
            synthesis_id="syn-1",
            measures=[
                Measure(
                    measure_id="mea-1",
                    initiative_id="INIT-BI-GOVERNANCE-01",
                    title="Governance",
                    description="Diagnose",
                    category=MeasureCategory.GOVERNANCE,
                    dimension="BI_D1",
                    impact=5,
                    effort=2,
                    priority_score=3.25,
                    deliverables=["D1", "D2", "D3"],
                    kpi={"name": "K", "target": "T", "measurement": "M"},
                    priority={"bucket": "now"},
                )
            ],
        )
        payload = build_export_payload(pipeline=pipeline, answers={}, catalog=catalog, export_version="1.2.0")
        markdown = payload_to_markdown(payload)

        self.assertEqual(payload["export_version"], "1.2.0")
        self.assertIn("Severity: 0.72", markdown)
        self.assertIn("Deliverable: D1", markdown)

    def test_export_v12_fills_missing_kpi_and_deliverables_from_template(self) -> None:
        pipeline = {
            "bi": {"critical_dimension_id": "BI_D1", "critical_dimension_severity": 0.7},
            "pa": {"critical_dimension_id": "PA_D1", "critical_dimension_severity": 0.6},
            "synthesis": {"combined_summary": "combo", "recommendation": "reco"},
        }
        catalog = MeasureCatalog(
            catalog_id="cat-3",
            title="Test",
            status=CatalogStatus.DRAFT,
            synthesis_id="syn-1",
            measures=[
                Measure(
                    measure_id="mea-1",
                    initiative_id="INIT-BI-GOVERNANCE-01",
                    title="BI-Governance-Basics etablieren",
                    description="Diagnose",
                    category=MeasureCategory.GOVERNANCE,
                    dimension="BI_D1",
                    priority_score=0,
                    kpi={},
                    deliverables=[],
                    priority={"bucket": "later"},
                )
            ],
        )

        payload = build_export_payload(pipeline=pipeline, answers={}, catalog=catalog, export_version="1.2.0")
        markdown = payload_to_markdown(payload)

        later = payload["recommendations"]["later"][0]
        self.assertTrue(later["priority_score"] > 0)
        self.assertEqual(later["kpi"]["name"], "Abgedeckte kritische Datenobjekte mit benanntem Owner")
        self.assertEqual(len(later["deliverables"]), 3)
        self.assertIn("KPI: Abgedeckte kritische Datenobjekte mit benanntem Owner", markdown)


    def test_export_v12_appends_catalog_summary_section(self) -> None:
        pipeline = {
            "bi": {"critical_dimension_id": "BI_D1", "critical_dimension_severity": 0.7},
            "pa": {"critical_dimension_id": "PA_D1", "critical_dimension_severity": 0.6},
            "synthesis": {"combined_summary": "combo", "recommendation": "reco"},
        }
        summary = {
            "headline": "Ergebnis Maßnahmenkatalog",
            "executive_summary": "Die priorisierten Maßnahmen stabilisieren zuerst Grundlagen.",
            "now": ["Governance aufsetzen"],
            "next": ["Standards ausrollen"],
            "later": ["Skalierung"],
            "risks_and_dependencies": ["Datenqualität als Voraussetzung"],
            "first_30_days": ["Kernteam benennen"],
            "measure_details": {
                "now": [
                    {
                        "title": "Governance aufsetzen",
                        "deliverables_summary": "RACI und Rollenhandbuch",
                        "kpi_summary": "Owner-Abdeckung >= 90%",
                    }
                ],
                "next": [],
                "later": [],
            },
        }

        payload = build_export_payload(pipeline=pipeline, answers={}, catalog=None, export_version="1.2.0", catalog_summary=summary)
        markdown = payload_to_markdown(payload)

        self.assertEqual(payload["catalog_summary"]["headline"], "Ergebnis Maßnahmenkatalog")
        self.assertIn("## Ergebnis Maßnahmenkatalog (LLM)", markdown)
        self.assertIn("Kernteam benennen", markdown)
        self.assertIn("Maßnahmen-Details (Deliverables & KPI)", markdown)
        self.assertIn("Owner-Abdeckung >= 90%", markdown)

    def test_payload_to_json_serializes_date_and_datetime(self) -> None:
        payload = {
            "timestamp": datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc),
            "answers": {
                "survey_date": date(2026, 1, 1),
            },
        }

        raw_json = payload_to_json(payload)

        self.assertIn('"timestamp": "2026-01-02T03:04:00+00:00"', raw_json)
        self.assertIn('"survey_date": "2026-01-01"', raw_json)


if __name__ == "__main__":
    unittest.main()
