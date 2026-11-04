"""Ollama (local, free). UNTESTED against a real server so far."""
from ._http import post_json


class OllamaProvider:
    name = "ollama"

    def __init__(self, model=None):
        self.model = model or "llama3.2"

    def chat(self, system, user, role="worker"):
        r = post_json("http://localhost:11434/api/chat", {
            "model": self.model, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        })
        return r["message"]["content"]
