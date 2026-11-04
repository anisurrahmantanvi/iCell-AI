"""Paths and limits. Everything is resolved lazily from ECOSYSTEM_HOME (default: current directory)
so tests can point the whole system at a temporary folder."""
import os
from pathlib import Path

# Only these prompts may ever be changed (and only after a human approves).
EVOLVABLE = ("planner", "worker")


def home() -> Path:
    return Path(os.getenv("ECOSYSTEM_HOME") or Path.cwd()).resolve()


def prompts_dir() -> Path:
    return home() / "prompts"      # evolvable prompts


def locked_dir() -> Path:
    return home() / "locked"       # rules, reviewer, improver: agents never change these


def evals_dir() -> Path:
    return home() / "evals"


def state_dir() -> Path:
    d = home() / "state"           # STOP file, audit log, proposals, history (git-ignored)
    d.mkdir(parents=True, exist_ok=True)
    return d


def max_calls() -> int:
    return int(os.getenv("MAX_CALLS", "60"))


def max_seconds() -> int:
    return int(os.getenv("MAX_SECONDS", "900"))
