import random
import unittest

from app.services.export_service import build_export_payload, payload_to_json, payload_to_markdown


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


if __name__ == "__main__":
    unittest.main()
