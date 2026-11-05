import os
import unittest
from unittest import mock

from ecosystem import llm
from ecosystem.llm import RouterProvider, get_provider

KEYS = ["PROVIDER", "MODEL"] + [f"{k}_{r}" for r in ("PLANNER", "WORKER", "REVIEWER", "IMPROVER")
                                  for k in ("PROVIDER", "MODEL")]


class Fake:
    def __init__(self, name, model):
        self.name, self.model = name, model

    def chat(self, system, user, role="worker"):
        return f"{self.name}:{self.model}:{role}"


class RouterTests(unittest.TestCase):
    def setUp(self):
        self._old = {k: os.environ.pop(k, None) for k in KEYS}
        self.built = []

        def fake_build(name, model):
            self.built.append((name, model))
            return Fake(name, model)

        p = mock.patch.object(llm, "_build", side_effect=fake_build)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        for k in KEYS:
            os.environ.pop(k, None)
        for k, v in self._old.items():
            if v is not None:
                os.environ[k] = v

    def test_no_role_settings_gives_plain_provider(self):
        os.environ["PROVIDER"] = "groq"
        os.environ["MODEL"] = "m1"
        p = get_provider()
        self.assertNotIsInstance(p, RouterProvider)
        self.assertEqual(self.built, [("groq", "m1")])

    def test_other_model_for_reviewer_only(self):
        os.environ["PROVIDER"] = "groq"
        os.environ["MODEL"] = "m1"
        os.environ["MODEL_REVIEWER"] = "m2"
        p = get_provider()
        self.assertIsInstance(p, RouterProvider)
        self.assertEqual(p.chat("s", "u", "worker"), "groq:m1:worker")
        self.assertEqual(p.chat("s", "u", "planner"), "groq:m1:planner")
        self.assertEqual(p.chat("s", "u", "reviewer"), "groq:m2:reviewer")
        self.assertEqual(p.chat("s", "u", "improver"), "groq:m1:improver")

    def test_other_provider_does_not_inherit_default_model(self):
        os.environ["PROVIDER"] = "groq"
        os.environ["MODEL"] = "m1"
        os.environ["PROVIDER_REVIEWER"] = "gemini"
        p = get_provider()
        self.assertEqual(p.chat("s", "u", "reviewer"), "gemini:None:reviewer")  # groq's model name is not passed on
        os.environ["MODEL_REVIEWER"] = "g-model"
        self.assertEqual(get_provider().chat("s", "u", "reviewer"), "gemini:g-model:reviewer")

    def test_unknown_role_goes_to_worker_and_name_lists_roles(self):
        os.environ["PROVIDER"] = "groq"
        os.environ["MODEL_REVIEWER"] = "m2"
        p = get_provider()
        self.assertEqual(p.chat("s", "u", "something"), "groq:None:something")
        self.assertIn("reviewer=groq:m2", p.name)

    def test_explicit_name_ignores_role_settings(self):
        os.environ["MODEL_REVIEWER"] = "m2"
        p = get_provider("groq")
        self.assertNotIsInstance(p, RouterProvider)


if __name__ == "__main__":
    unittest.main()
