import unittest
from datetime import datetime

from pydantic import ValidationError

from domain.models import (
    AnswerSet,
    AnswerSetStatus,
    CatalogStatus,
    Measure,
    MeasureCatalog,
    MeasureCategory,
    UseCase,
    UseCaseType,
)


class DomainModelsTestCase(unittest.TestCase):
    def test_use_case_validates_enum_and_version_fields(self) -> None:
        use_case = UseCase(
            use_case_id="uc-1",
            name="Lead Triage",
            description="Classify inbound leads",
            use_case_type=UseCaseType.BUSINESS_IMPACT,
        )

        self.assertEqual(use_case.model_version, "1.0.0")
        self.assertEqual(use_case.prompt_version, "1.0.0")
        self.assertIsInstance(use_case.created_at, datetime)

    def test_use_case_rejects_invalid_enum_value(self) -> None:
        with self.assertRaises(ValidationError):
            UseCase(
                use_case_id="uc-2",
                name="Invalid",
                description="Invalid enum test",
                use_case_type="wrong-type",
            )

    def test_answer_set_default_status(self) -> None:
        answer_set = AnswerSet(answer_set_id="as-1", questionnaire_id="q-1")

        self.assertEqual(answer_set.status, AnswerSetStatus.DRAFT)

    def test_measure_catalog_with_measure(self) -> None:
        measure = Measure(
            measure_id="m-1",
            title="Data Governance Board",
            description="Establish cross-functional governance.",
            category=MeasureCategory.GOVERNANCE,
        )
        catalog = MeasureCatalog(
            catalog_id="c-1",
            title="Default Catalog",
            status=CatalogStatus.PUBLISHED,
            measures=[measure],
        )

        self.assertEqual(catalog.status, CatalogStatus.PUBLISHED)
        self.assertEqual(len(catalog.measures), 1)


if __name__ == "__main__":
    unittest.main()
