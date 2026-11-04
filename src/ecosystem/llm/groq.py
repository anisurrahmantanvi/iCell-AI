"""Groq (free tier, OpenAI-compatible endpoint). UNTESTED against the real API so far.
Needs GROQ_API_KEY. Set MODEL if the default model name is retired."""
import os

from ._http import post_json


class GroqProvider:
    name = "groq"

    def __init__(self, model=None):
        self.model = model or "llama-3.3-70b-versatile"

    def chat(self, system, user, role="worker"):
        key = os.environ["GROQ_API_KEY"]
        r = post_json("https://api.groq.com/openai/v1/chat/completions", {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }, headers={"Authorization": f"Bearer {key}"})
        return r["choices"][0]["message"]["content"]
