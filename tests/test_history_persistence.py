import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.vietnam_bd.history import (
    complete_analysis,
    fail_analysis,
    get_analysis,
    list_analyses,
    start_analysis,
    update_analysis_progress,
)


class SharedHistoryPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "history.sqlite3"
        self.environment = patch.dict(os.environ, {"BD_HISTORY_DB_PATH": str(self.db_path)})
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temp_dir.cleanup()

    def test_failed_attempt_and_progress_events_are_persisted(self) -> None:
        history_id = start_analysis(
            seed="Thermo Fisher NIC",
            engine="BD v3",
            research_provider="existing",
            guided_context="Find project partners",
        )
        trace = {"events": [{"event": "seed_understanding", "details": {}}]}
        update_analysis_progress(history_id, trace)
        fail_analysis(history_id, error_message="Connection error", research_trace=trace)

        saved = get_analysis(history_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.status, "failed")
        self.assertEqual(saved.research_trace, trace)
        self.assertEqual(saved.guided_context, "Find project partners")
        self.assertIn("Connection error", saved.error_message)

    def test_completed_attempt_is_visible_in_shared_newest_first_history(self) -> None:
        first_id = start_analysis(seed="first", engine="BD v3")
        fail_analysis(first_id, error_message="failed")
        second_id = start_analysis(seed="second", engine="BD v3")
        complete_analysis(
            second_id,
            result_version="v3",
            result={"opportunity_title": "Second Opportunity"},
            research_trace={"quick": {"company": "Example"}},
        )

        history = list_analyses()
        self.assertEqual([item.history_id for item in history], [second_id, first_id])
        self.assertEqual(history[0].status, "completed")
        self.assertEqual(history[1].status, "failed")


if __name__ == "__main__":
    unittest.main()
