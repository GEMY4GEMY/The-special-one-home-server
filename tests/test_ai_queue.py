"""Regression tests for durable AI jobs and per-user access."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import ai_queue

class DurableQueueTests(unittest.TestCase):
    def test_result_survives_reinitialization(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(ai_queue, "DB", Path(folder) / "queue.sqlite3"):
                with patch.object(ai_queue, "ready", False):
                    key = ai_queue.submit(7, lambda: [{"prompt": "Hello"}])
                    for _ in range(100):
                        job = ai_queue.lookup(key, 7)
                        if job["state"] == "complete":
                            break
                        time.sleep(0.02)
                    self.assertEqual(job["state"], "complete")
                    self.assertIsNone(ai_queue.lookup(key, 8))
                    with patch.object(ai_queue, "ready", False):
                        ai_queue.initialize()
                        self.assertEqual(ai_queue.lookup(key, 7)["output"][0]["prompt"], "Hello")

    def test_interrupted_job_is_not_mistaken_for_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(ai_queue, "DB", Path(folder) / "queue.sqlite3"):
                with patch.object(ai_queue, "ready", False):
                    ai_queue.initialize()
                    with ai_queue._connect() as db:
                        db.execute("INSERT INTO ai_tasks VALUES ('pending', 7, 'working', NULL)")
                    with patch.object(ai_queue, "ready", False):
                        ai_queue.initialize()
                        self.assertEqual(ai_queue.lookup("pending", 7)["state"], "interrupted")

if __name__ == "__main__":
    unittest.main()
