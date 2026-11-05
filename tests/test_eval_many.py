import json
import os
import unittest

from _base import EcoTestCase

from ecosystem import config
from ecosystem.core.killswitch import Stopped
from ecosystem.evals.runner import run_eval, run_eval_many, summarize
from ecosystem.llm import get_provider


class EvalManyTests(EcoTestCase):
    def test_task_file_is_valid(self):
        tasks = json.loads((config.evals_dir() / "tasks.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(tasks), 10)
        for t in tasks:
            self.assertIsInstance(t["task"], str)
            for req in t["must_contain"]:
                self.assertTrue(isinstance(req, str) or (isinstance(req, list) and req))
            for key in ("max_words", "max_paragraphs"):
                if key in t:
                    self.assertIsInstance(t[key], int)
                    self.assertGreater(t[key], 0)

    def test_budget_scales_with_task_count(self):
        # mock: ~4 calls per task, 13+ tasks is more than the old default of 60 calls in total
        avg, results = run_eval(get_provider())
        self.assertEqual(len(results), len(json.loads((config.evals_dir() / "tasks.json").read_text())))
        self.assertTrue(0.0 <= avg <= 1.0)

    def test_explicit_max_calls_is_honoured(self):
        os.environ["MAX_CALLS"] = "5"
        try:
            with self.assertRaises(Stopped):
                run_eval(get_provider())
        finally:
            os.environ.pop("MAX_CALLS", None)

    def test_many_runs_and_summary(self):
        avgs, last = run_eval_many(get_provider(), 3)
        self.assertEqual(len(avgs), 3)
        self.assertTrue(last)
        mean, lo, hi = summarize([0.5, 0.7, 0.9])
        self.assertAlmostEqual(mean, 0.7)
        self.assertEqual((lo, hi), (0.5, 0.9))


if __name__ == "__main__":
    unittest.main()
