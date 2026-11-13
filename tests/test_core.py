import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.fact_checker import check_claims
from agents.source_analyst import assess_source
from core.ai_engine import AIEngine
from core.orchestrator import run_editorial
from core.storage import Storage
from services.web_reader import _validate_public_url


class CoreTests(unittest.TestCase):
    def test_sqlite_persists_and_updates_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Storage(Path(tmp) / "test.sqlite3")
            session_id = db.save_session({"topic": "RWA", "article": "draft", "sources": [{"url": "https://example.com"}], "fact_checks": []})
            found = db.get_session(session_id)
            self.assertEqual(found["article"], "draft")
            self.assertEqual(found["sources"][0]["url"], "https://example.com")
            found["article"] = "edited"
            db.save_session(found, session_id)
            self.assertEqual(db.get_session(session_id)["article"], "edited")

    def test_private_and_invalid_urls_are_blocked(self):
        for url in ("http://127.0.0.1", "http://localhost", "file:///etc/passwd", "http://user:pass@example.com"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                _validate_public_url(url)

    def test_fact_check_parser_discards_invalid_ids_and_status(self):
        class FakeAI:
            def ask(self, _prompt, _agent):
                return '```json\n{"claims":[{"claim":"TVL doubled","status":"verified","source_ids":[1,99,"bad"],"note":"source supports it"}]}\n```'
        result = check_claims("draft", "analysis", [{"url": "https://example.com"}], FakeAI())
        self.assertEqual(result[0]["status"], "VERIFIED")
        self.assertEqual(result[0]["source_ids"], [1])

    def test_source_assessment_does_not_claim_certainty(self):
        result = assess_source({"url": "https://example.gov/report", "content": "x" * 2000, "published_at": "2026-01-01"})
        self.assertEqual(result["source_type"], "primary/official candidate")
        self.assertIn("не подтверждает точность", result["credibility_notes"])

    def test_provider_fallback_uses_next_provider(self):
        engine = AIEngine("g", "o", retry_delay=0)
        with patch.object(engine, "_ask_gemini", side_effect=RuntimeError("down")), patch.object(engine, "_ask_openrouter", return_value="ok"):
            self.assertEqual(engine.ask("prompt", "test"), "ok")
        self.assertEqual(engine.current_provider, "OpenRouter")
        self.assertTrue(any(row["status"] == "failed" for row in engine.logs))

    def test_orchestrator_runs_pipeline_and_returns_auditable_draft(self):
        class FakeAI:
            def __init__(self):
                self.steps = iter([
                    "Research dossier [1]",
                    "Angle and structure",
                    "Draft [1]",
                    '{"claims":[{"claim":"Example claim","status":"PARTIALLY VERIFIED","source_ids":[1],"note":"limited evidence"}]}',
                    "Edited draft [1]",
                ])

            def ask(self, _prompt, _agent):
                return next(self.steps)

        source = {"title": "Report", "url": "https://example.com/report", "snippet": "Evidence",
                  "content": "Supporting evidence " * 100, "published_at": "2026-01-01",
                  "extraction_status": "extracted"}
        with patch("core.orchestrator.search_web", return_value=[source]), patch("core.orchestrator.enrich_source", side_effect=lambda item: item):
            result = run_editorial("Topic", "English", "Analytical", 500, "X Article", FakeAI())
        self.assertEqual(result["article"], "Edited draft [1]")
        self.assertEqual(result["fact_checks"][0]["status"], "PARTIALLY VERIFIED")
        self.assertEqual(result["sources"][0]["source_type"], "secondary or unclassified")


if __name__ == "__main__":
    unittest.main()
