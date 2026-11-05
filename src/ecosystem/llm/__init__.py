"""Model providers. Add a new provider = one new file with a class that has chat(system, user, role).

PROVIDER env: mock (default) | ollama | gemini | groq
MODEL env overrides the provider's default model name.

Per-role models (optional): PROVIDER_<ROLE> and MODEL_<ROLE> override the defaults for one agent,
with ROLE one of PLANNER, WORKER, REVIEWER, IMPROVER. Example: a different model as the judge.
The mapping is fixed for the whole run (no silent fallback to another model), so an eval score
always describes exactly one configuration.
"""
import os

from .mock import MockProvider

ROLES = ("planner", "worker", "reviewer", "improver")


def _build(name, model):
    name = name.lower()
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


class RouterProvider:
    """Sends each agent role to its own provider/model."""

    def __init__(self, by_role):
        self.by_role = by_role
        self.name = "router[" + ", ".join(
            f"{r}={p.name}:{getattr(p, 'model', '-')}" for r, p in by_role.items()) + "]"

    def chat(self, system, user, role="worker"):
        return self.by_role.get(role, self.by_role["worker"]).chat(system, user, role)


def get_provider(name=None):
    default_name = (name or os.getenv("PROVIDER", "mock")).lower()
    default_model = os.getenv("MODEL") or None
    if name is not None:  # explicit single provider, no per-role settings
        return _build(default_name, default_model)
    overridden = any(os.getenv(f"{k}_{r.upper()}") for r in ROLES for k in ("PROVIDER", "MODEL"))
    if not overridden:
        return _build(default_name, default_model)
    by_role = {}
    for r in ROLES:
        r_name = (os.getenv(f"PROVIDER_{r.upper()}") or default_name).lower()
        r_model = os.getenv(f"MODEL_{r.upper()}") or (default_model if r_name == default_name else None)
        by_role[r] = _build(r_name, r_model)
    return RouterProvider(by_role)
