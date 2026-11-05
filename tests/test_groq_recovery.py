import json
import os
import unittest
from unittest import mock

from ecosystem.llm import groq
from ecosystem.llm._http import HttpError


def _tool_error(failed_generation):
    body = json.dumps({"error": {
        "message": "Tool choice is none, but model called a tool",
        "type": "invalid_request_error",
        "code": "tool_use_failed",
        "failed_generation": failed_generation,
    }})
    return HttpError(400, body)


class GroqToolRecoveryTests(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "x" * 20

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    def chat_with_error(self, err):
        with mock.patch.object(groq, "post_json", side_effect=err):
            return groq.GroqProvider().chat("s", "u")

    def test_raw_code_inside_broken_tool_call(self):
        # the exact shape seen from the live API: arguments is raw code, not a JSON string
        gen = '{"name": "code", "arguments": def is_even(n):\n    return n % 2 == 0}'
        out = self.chat_with_error(_tool_error(gen))
        self.assertEqual(out, "def is_even(n):\n    return n % 2 == 0")

    def test_well_formed_string_arguments(self):
        gen = '{"name": "code", "arguments": "def f():\\n    return 1"}'
        self.assertEqual(self.chat_with_error(_tool_error(gen)), "def f():\n    return 1")

    def test_dict_arguments(self):
        gen = '{"name": "code", "arguments": {"code": "print(1)"}}'
        self.assertEqual(self.chat_with_error(_tool_error(gen)), "print(1)")

    def test_unrecognised_shape_returns_whole_text(self):
        self.assertEqual(self.chat_with_error(_tool_error("some text")), "some text")

    def test_other_errors_are_not_swallowed(self):
        with self.assertRaises(HttpError):
            self.chat_with_error(HttpError(401, '{"error": {"code": "invalid_api_key"}}'))
        with self.assertRaises(HttpError):  # 400 but not a tool failure
            self.chat_with_error(HttpError(400, '{"error": {"code": "something_else"}}'))

    def test_normal_reply_passes_through(self):
        ok = {"choices": [{"message": {"content": "hello"}}]}
        with mock.patch.object(groq, "post_json", return_value=ok):
            self.assertEqual(groq.GroqProvider().chat("s", "u"), "hello")


if __name__ == "__main__":
    unittest.main()
