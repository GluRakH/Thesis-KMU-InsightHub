import tempfile
import unittest
from pathlib import Path

from app.services.measure_item_adapter import _trigger_items_from_measure
from domain.models import CatalogStatus, Measure, MeasureCatalog, MeasureCategory
from persistence.database import Base, create_sqlite_engine, create_session_factory
from persistence.repositories import PersistenceRepository, load_catalog


class CatalogTraceabilityRoundtripTestCase(unittest.TestCase):
    def test_measure_evidence_trigger_items_survive_persistence_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            engine = create_sqlite_engine(db_path)
            Base.metadata.create_all(engine)
            session_factory = create_session_factory(db_path)

            measure = Measure(
                measure_id="m-rt-1",
                title="Data Governance stärken",
                description="Stellt Ownership und Kontrollen sicher",
                category=MeasureCategory.GOVERNANCE,
                dimension="BI_D1",
                maturity_label="L2",
                impact=4,
                effort=2,
                suggested_priority=1,
                priority_score=0.82,
                initiative_id="INIT-BI-GOV-01",
                goal="Verbesserung Datenqualität",
                dependencies=["INIT-BI-DATA-01"],
                deliverables=["RACI", "DQ-Regeln", "Review-Rhythmus"],
                evidence={
                    "dimension_id": "BI_D1",
                    "severity": 0.75,
                    "trigger_items": [
                        {
                            "item_id": "BI_Q01",
                            "answer": "teilweise",
                            "deficit_score": 0.91,
                            "question_text": "Sind Rollen und Verantwortlichkeiten klar definiert?",
                            "dimension_id": "BI_D1",
                        }
                    ],
                },
                kpi={
                    "name": "DQ Policy Abdeckung",
                    "target": ">= 90%",
                    "measurement": "Monatlicher Audit",
                    "frequency": "monatlich",
                    "source_system": "DWH",
                    "owner_role": "Data Owner",
                },
                priority={"score": 0.82, "bucket": "now"},
            )
            catalog = MeasureCatalog(
                catalog_id="cat-rt-1",
                title="Roundtrip Catalog",
                status=CatalogStatus.DRAFT,
                synthesis_id="syn-rt-1",
                measures=[measure],
            )

            with session_factory() as session:
                repository = PersistenceRepository(session)
                repository.save_catalog(catalog)
                loaded = load_catalog(session, "cat-rt-1")

            self.assertIsNotNone(loaded)
            loaded_measure = loaded.measures[0]
            self.assertIn("trigger_items", loaded_measure.evidence)
            self.assertTrue(loaded_measure.evidence["trigger_items"])

            trigger_items = _trigger_items_from_measure(loaded_measure)
            self.assertTrue(trigger_items)
            self.assertFalse(trigger_items[0]["item_id"].endswith("_FALLBACK"))


if __name__ == "__main__":
    unittest.main()
