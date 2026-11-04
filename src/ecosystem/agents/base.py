"""Shared plumbing for all agents: context, prompt loading, the single model-call gate."""
import json
import re
from dataclasses import dataclass, field

from .. import config
from ..core import audit
from ..core.budget import Budget


@dataclass
class Context:
    provider: object
    budget: Budget = field(default_factory=Budget)
    overrides: dict = field(default_factory=dict)  # used by `test` to try a proposed prompt without applying it


def get_prompt(name, overrides=None):
    if name in config.EVOLVABLE:
        if overrides and name in overrides:
            return overrides[name]
        return (config.prompts_dir() / f"{name}.txt").read_text(encoding="utf-8").strip()
    return (config.locked_dir() / f"{name}.txt").read_text(encoding="utf-8").strip()


def ask(role, user, ctx):
    """The ONLY place a model is called. Kill switch and budget are enforced here, every time."""
    system = get_prompt("rules") + "\n\n" + get_prompt(role, ctx.overrides)
    ctx.budget.tick()
    out = ctx.provider.chat(system, user, role)
    audit.log("call", role=role, user=user[:300], out=out[:500])
    return out


def jparse(text, default):
    m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if not m:
        return default
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return default
