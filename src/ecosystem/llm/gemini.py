"""Google Gemini (free tier via AI Studio key). Needs GEMINI_API_KEY.
Reached with a real key: the model list worked and `gemini-3.8-flash` was accepted (the API itself
named it after rejecting gemini-2.5-flash for new users). A complete successful answer has not been
seen yet: the first attempts hit a timeout and HTTP 503 "high demand". Model names change over time:
set MODEL if the default stops working. The key goes in a header, not in the URL."""
import os

from ._http import post_json


class GeminiProvider:
    name = "gemini"

    def __init__(self, model=None):
        self.model = model or "gemini-3.8-flash"

    def chat(self, system, user, role="worker"):
        key = os.environ["GEMINI_API_KEY"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        r = post_json(url, {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
        }, headers={"x-goog-api-key": key})
        candidates = r.get("candidates") or []
        if not candidates:  # e.g. blocked by a safety filter
            raise RuntimeError(f"Gemini কোনো উত্তর দেয়নি: {str(r.get('promptFeedback', r))[:200]}")
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            raise RuntimeError(f"Gemini-র উত্তর ফাঁকা (finishReason={candidates[0].get('finishReason')})")
        return text
