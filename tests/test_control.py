import unittest

from _base import EcoTestCase

from ecosystem.agents.base import Context
from ecosystem.agents.orchestrator import run_task
from ecosystem.core import killswitch
from ecosystem.core.budget import Budget
from ecosystem.core.killswitch import Stopped
from ecosystem.llm import get_provider


class ControlTests(EcoTestCase):
    def test_kill_switch_blocks_calls(self):
        killswitch.engage()
        with self.assertRaises(Stopped):
            run_task("x", Context(provider=get_provider()))
        killswitch.release()
        res = run_task("x", Context(provider=get_provider()))
        self.assertIn("answer", res)

    def test_budget_limit(self):
        b = Budget(max_calls=2)
        b.tick()
        b.tick()
        with self.assertRaises(Stopped):
            b.tick()

    def test_budget_stops_pipeline(self):
        with self.assertRaises(Stopped):
            run_task("x", Context(provider=get_provider(), budget=Budget(max_calls=2)))


if __name__ == "__main__":
    unittest.main()
