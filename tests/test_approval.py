import unittest

from _base import EcoTestCase

from ecosystem import config
from ecosystem.agents.base import Context
from ecosystem.core import proposals
from ecosystem.evals.runner import run_eval
from ecosystem.evolution.improver import propose
from ecosystem.llm import get_provider


class ApprovalTests(EcoTestCase):
    def _prompt(self):
        return (config.prompts_dir() / "worker.txt").read_text(encoding="utf-8")

    def test_locked_targets_cannot_be_proposed(self):
        for bad in ("reviewer", "improver", "rules"):
            with self.assertRaises(ValueError):
                proposals.create(bad, "x" * 50, "try to change the judge")

    def test_bad_length_rejected(self):
        with self.assertRaises(ValueError):
            proposals.create("worker", "short", "")

    def test_declined_proposal_changes_nothing(self):
        before = self._prompt()
        pid = proposals.create("worker", "You are the Worker. Be concise and give one example.", "t")
        self.assertFalse(proposals.approve(pid, lambda p: False))
        self.assertEqual(before, self._prompt())
        self.assertEqual(proposals.get(pid)["status"], "pending")

    def test_approved_proposal_applies_and_keeps_history(self):
        before = self._prompt()
        pid = proposals.create("worker", "You are the Worker. Be concise and give one example.", "t")
        self.assertTrue(proposals.approve(pid, lambda p: True))
        self.assertNotEqual(before, self._prompt())
        hist = list((config.state_dir() / "history").glob("worker-*.txt"))
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0].read_text(encoding="utf-8"), before)

    def test_improver_only_proposes(self):
        before = self._prompt()
        avg, results = run_eval(get_provider())
        pid = propose(results, Context(provider=get_provider()))
        self.assertIsNotNone(pid)
        self.assertEqual(before, self._prompt())  # nothing applied without approval


if __name__ == "__main__":
    unittest.main()
