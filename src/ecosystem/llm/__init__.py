"""Model providers. Add a new provider = one new file with a class that has chat(system, user, role).

PROVIDER env: mock (default) | ollama | gemini | groq
MODEL env overrides the provider's default model name.
"""
import os

from .mock import MockProvider


def get_provider(name=None):
    name = (name or os.getenv("PROVIDER", "mock")).lower()
    model = os.getenv("MODEL") or None
    if name == "mock":
        return MockProvider()
    if name == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(model)
    if name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(model)
    if name == "groq":
        from .groq import GroqProvider
        return GroqProvider(model)
    raise ValueError(f"অজানা PROVIDER: {name}")
