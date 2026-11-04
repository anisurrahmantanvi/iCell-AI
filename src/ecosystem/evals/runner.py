"""Fixed evaluation tasks (evals/tasks.json). Score = 50% reviewer + 50% deterministic keyword checks,
so the LLM reviewer alone cannot decide whether something improved."""
import json

from .. import config
from ..agents.base import Context
from ..agents.orchestrator import run_task
from ..core.budget import Budget


def run_eval(provider, overrides=None, on_result=None):
    tasks = json.loads((config.evals_dir() / "tasks.json").read_text(encoding="utf-8"))
    ctx = Context(provider=provider, budget=Budget(), overrides=overrides or {})
    results = []
    for t in tasks:
        res = run_task(t["task"], ctx)
        words = t.get("must_contain", [])
        low = res["answer"].lower()
        res["check"] = sum(w.lower() in low for w in words) / max(1, len(words))
        res["final"] = 0.5 * res["score"] / 10 + 0.5 * res["check"]
        results.append(res)
        if on_result:
            on_result(res)
    avg = sum(r["final"] for r in results) / max(1, len(results))
    return avg, results


def save_last(results):
    (config.state_dir() / "last_eval.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def load_last():
    """Results of the most recent eval, or None if none has been run yet."""
    f = config.state_dir() / "last_eval.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
