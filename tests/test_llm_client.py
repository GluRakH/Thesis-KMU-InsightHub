import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.llm_client import LLMClient, LLMClientConfig


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class LLMClientTestCase(unittest.TestCase):
    def test_dry_run_returns_dummy_and_writes_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            trace_file = Path(tmp_dir) / "llm_trace.jsonl"
            config = LLMClientConfig(trace_file=trace_file)
            client = LLMClient(config=config, dry_run=True)

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


    def test_summarize_measure_catalog_returns_structured_payload(self) -> None:
        client = LLMClient(dry_run=True)

        summary = client.summarize_measure_catalog(
            focus="Governance",
            measures_by_bucket={"now": [{"title": "M1"}], "next": [], "later": []},
        )

        self.assertEqual(summary["headline"], "Ergebnis Maßnahmenkatalog")
        self.assertTrue(summary["now"])

    def test_check_connection_in_dry_run_mode(self) -> None:
        client = LLMClient(dry_run=True)

        status = client.check_connection()

        self.assertTrue(status["ok"])
        self.assertEqual(status["mode"], "dry_run")

    @patch("urllib.request.urlopen")
    def test_check_connection_reports_error(self, mocked_urlopen) -> None:
        mocked_urlopen.side_effect = RuntimeError("offline")
        client = LLMClient(
            config=LLMClientConfig(trace_file=Path(tempfile.gettempdir()) / "trace.jsonl"),
            dry_run=False,
        )

        status = client.check_connection()

        self.assertFalse(status["ok"])
        self.assertIn("fehlgeschlagen", status["message"])

    @patch("urllib.request.urlopen")
    def test_call_api_uses_ollama_generate(self, mocked_urlopen) -> None:
        captured_request = {}

        def _fake_open(request, timeout=None):
            captured_request["url"] = request.full_url
            captured_request["body"] = json.loads(request.data.decode("utf-8"))
            captured_request["headers"] = dict(request.header_items())
            captured_request["timeout"] = timeout
            return _FakeResponse({"response": '{"summary":"Lokal via Ollama."}'})

        mocked_urlopen.side_effect = _fake_open

        client = LLMClient(
            config=LLMClientConfig(trace_file=Path(tempfile.gettempdir()) / "trace.jsonl"),
            api_key=None,
            dry_run=False,
        )

        summary = client.summarize_use_case("Kontext", {"d": "x"}, {"p": "y"})

        self.assertEqual(summary, "Lokal via Ollama.")
        self.assertEqual(captured_request["url"], "http://localhost:11434/api/generate")
        self.assertEqual(captured_request["body"]["format"], "json")


if __name__ == "__main__":
    unittest.main()
