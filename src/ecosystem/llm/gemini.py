"""Google Gemini (free tier via AI Studio key). UNTESTED against the real API so far.
Needs GEMINI_API_KEY. Model names change over time: set MODEL if the default stops working."""
import os

from ._http import post_json


class GeminiProvider:
    name = "gemini"

    def __init__(self, model=None):
        self.model = model or "gemini-2.0-flash"

    def chat(self, system, user, role="worker"):
        key = os.environ["GEMINI_API_KEY"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={key}"
        r = post_json(url, {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
        })
        return r["candidates"][0]["content"]["parts"][0]["text"]
