import os
import unittest
from unittest import mock

from ecosystem.llm import gemini


class GeminiTests(unittest.TestCase):
    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "k" * 20

    def tearDown(self):
        os.environ.pop("GEMINI_API_KEY", None)

    def call(self, reply):
        with mock.patch.object(gemini, "post_json", return_value=reply) as m:
            out = gemini.GeminiProvider().chat("sys", "hi")
        return out, m

    def test_key_is_sent_in_header_not_url(self):
        _, m = self.call({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
        url = m.call_args.args[0]
        self.assertNotIn("key=", url)
        self.assertNotIn("k" * 20, url)
        self.assertEqual(m.call_args.kwargs["headers"], {"x-goog-api-key": "k" * 20})

    def test_text_parts_are_joined(self):
        out, _ = self.call({"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}]})
        self.assertEqual(out, "ab")

    def test_default_model_is_one_the_api_accepted(self):
        self.assertEqual(gemini.GeminiProvider().model, "gemini-3.8-flash")
        self.assertEqual(gemini.GeminiProvider("x").model, "x")

    def test_blocked_or_empty_answer_is_a_clear_error(self):
        with self.assertRaises(RuntimeError):
            self.call({"promptFeedback": {"blockReason": "SAFETY"}})
        with self.assertRaises(RuntimeError):
            self.call({"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]})


if __name__ == "__main__":
    unittest.main()
