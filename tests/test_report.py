import io
import json
from contextlib import redirect_stdout
from unittest import mock

from _base import EcoTestCase

from ecosystem import cli, config
from ecosystem.agents.base import Context
from ecosystem.evals.runner import check_report, load_tasks, rescore, save_last
from ecosystem.evolution import improver


class ReportTests(EcoTestCase):
    def test_check_report_lists_each_failure(self):
        task = {"must_contain": ["391", ["foo", "bar"]], "max_words": 3, "max_paragraphs": 1}
        score, fails = check_report(task, "nope nope nope nope\n\nx")
        self.assertEqual(score, 0.0)
        self.assertEqual(len(fails), 4)
        self.assertIn("missing: foo / bar", fails)
        self.assertTrue(any(f.startswith("too long") for f in fails))
        self.assertTrue(any(f.startswith("too many paragraphs") for f in fails))
        self.assertEqual(check_report(task, "391 foo"), (1.0, []))

    def _old_result(self):
        t = load_tasks()[0]
        return {"task": t["task"], "plan": ["a", "b"], "answer": "zzz", "score": 9.0, "feedback": "ok",
                "check": 1.0, "final": 0.95}

    def test_rescore_adds_failures_to_old_saved_results(self):
        r = rescore([self._old_result()])[0]
        self.assertTrue(r["check_failures"])
        self.assertAlmostEqual(r["final"], 0.5 * 0.9 + 0.5 * r["check"])

    def test_report_command_is_offline(self):
        save_last([self._old_result()])
        buf = io.StringIO()
        with mock.patch.object(cli, "get_provider", side_effect=AssertionError("no model calls")):
            with redirect_stdout(buf):
                cli.cmd_report([])
        self.assertIn("✗", buf.getvalue())
        self.assertIn("steps=2", buf.getvalue())

    def test_improver_payload_contains_failed_checks(self):
        seen = {}
        def fake_ask(role, user, ctx):
            seen["p"] = json.loads(user)
            return "{}"
        r = rescore([self._old_result()])
        with mock.patch.object(improver, "ask", fake_ask):
            improver.propose(r, Context(provider=None))
        e = seen["p"]["eval_feedback"][0]
        self.assertTrue(e["failed_checks"])
        self.assertEqual(e["steps_used"], 2)
