"""Groq (free tier, OpenAI-compatible endpoint). Ran successfully against the live API
(openai/gpt-oss-20b). Needs GROQ_API_KEY. Model names change: set MODEL if the default is retired.
List the models your key can use with:
  curl -s -A "iCell-AI/0.1" -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models"""
import json
import os
import re

from ._http import HttpError, post_json


def _recover_tool_call(err):
    """gpt-oss models sometimes try to call a built-in tool (e.g. "code") when asked for code, and
    Groq then rejects the call with HTTP 400 "tool_use_failed". The text the model tried to send to
    the tool is in error.failed_generation; use it as the answer. Returns None if this is some
    other error (the caller then re-raises it)."""
    if err.code != 400 or "tool_use_failed" not in err.body:
        return None
    try:
        gen = json.loads(err.body)["error"]["failed_generation"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(gen, str) or not gen.strip():
        return None
    m = re.search(r'"arguments"\s*:\s*(.*)\}\s*$', gen, re.S)
    if m:
        args = m.group(1).strip()
        try:
            val = json.loads(args)
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                return "\n".join(str(v) for v in val.values())
        except ValueError:
            pass
        if args:
            return args  # not valid JSON (raw code without quotes), still the model's text
    return gen


class GroqProvider:
    name = "groq"

    def __init__(self, model=None):
        self.model = model or "openai/gpt-oss-20b"

    def chat(self, system, user, role="worker"):
        key = os.environ["GROQ_API_KEY"]
        try:
            r = post_json("https://api.groq.com/openai/v1/chat/completions", {
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            }, headers={"Authorization": f"Bearer {key}"})
        except HttpError as e:
            recovered = _recover_tool_call(e)
            if recovered is None:
                raise
            return recovered
        return r["choices"][0]["message"]["content"]
