import json
import tempfile
import unittest
from pathlib import Path

from adapters.llm_client import LLMClient, LLMClientConfig


class LLMClientTestCase(unittest.TestCase):
    def test_dry_run_without_key_returns_dummy_and_writes_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            trace_file = Path(tmp_dir) / "llm_trace.jsonl"
            config = LLMClientConfig(trace_file=trace_file)
            client = LLMClient(config=config, api_key=None, dry_run=False)

            summary = client.summarize_use_case("Kontext", {"D1": "ok"}, {"D2": "ok"})

            self.assertIn("[Dummy]", summary)
            self.assertTrue(trace_file.exists())
            trace = json.loads(trace_file.read_text(encoding="utf-8").strip())
            self.assertEqual(trace["task"], "summarize_use_case")
            self.assertEqual(trace["mode"], "dry_run")
            self.assertIn("input_hash", trace)
            self.assertNotIn("company_context", trace)

    def test_draft_measures_parses_json_dummy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            trace_file = Path(tmp_dir) / "llm_trace.jsonl"
            config = LLMClientConfig(trace_file=trace_file)
            client = LLMClient(config=config, dry_run=True)

            measures = client.draft_measures(["Reporting", "Governance"], max_measures=2)

            self.assertEqual(len(measures), 2)
            self.assertTrue(all(isinstance(item, str) for item in measures))


if __name__ == "__main__":
    unittest.main()
