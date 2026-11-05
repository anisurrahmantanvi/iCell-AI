"""Groq (free tier, OpenAI-compatible endpoint). Ran successfully once against the live API
(openai/gpt-oss-20b). Needs GROQ_API_KEY. Model names change: set MODEL if the default is retired.
List the models your key can use with:
  curl -s -A "iCell-AI/0.1" -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models"""
import os

from ._http import post_json


class GroqProvider:
    name = "groq"

    def __init__(self, model=None):
        self.model = model or "openai/gpt-oss-20b"

    def chat(self, system, user, role="worker"):
        key = os.environ["GROQ_API_KEY"]
        r = post_json("https://api.groq.com/openai/v1/chat/completions", {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }, headers={"Authorization": f"Bearer {key}"})
        return r["choices"][0]["message"]["content"]
