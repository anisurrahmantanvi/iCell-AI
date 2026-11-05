"""Fixed evaluation tasks (evals/tasks.json). Score = 50% reviewer + 50% deterministic keyword checks,
so the LLM reviewer alone cannot decide whether something improved."""
import json
import os
import re

from .. import config
from ..agents.base import Context
from ..agents.orchestrator import run_task
from ..core.budget import Budget


def keyword_check(requirements, answer):
    """Fraction of requirements met. A requirement is a word, or a list of acceptable alternatives
    (any one of them counts). Matching is a case-insensitive substring test."""
    if not requirements:
        return 1.0
    return _count_met(requirements, answer) / len(requirements)


def _count_met(requirements, answer):
    low = answer.lower()
    met = 0
    for req in requirements:
        alternatives = [req] if isinstance(req, str) else list(req)
        if any(a.lower() in low for a in alternatives):
            met += 1
    return met

def paragraph_count(answer):
    return len([p for p in re.split(r"\n\s*\n", answer.strip()) if p.strip()])


def check_report(task, answer):
    """(score 0-1, list of failure strings) for one task. Each of these counts as one requirement:
    every "must_contain" entry, "max_words" (answer not longer than that) and "max_paragraphs"
    (answer not split into more blocks than that). The pipeline joins the output of every step with
    a blank line, so a simple question that gets chopped into several steps shows up as too many
    paragraphs; padded answers show up as too many words. Keyword checks alone cannot see either."""
    reqs = task.get("must_contain", [])
    max_words = task.get("max_words")
    max_par = task.get("max_paragraphs")
    total = len(reqs) + (1 if max_words else 0) + (1 if max_par else 0)
    if total == 0:
        return 1.0, []
    low = answer.lower()
    met, fails = 0, []
    for req in reqs:
        alts = [req] if isinstance(req, str) else list(req)
        if any(a.lower() in low for a in alts):
            met += 1
        else:
            fails.append("missing: " + " / ".join(alts))
    if max_words:
        n = len(answer.split())
        if n <= max_words:
            met += 1
        else:
            fails.append(f"too long: {n} words, limit {max_words}")
    if max_par:
        n = paragraph_count(answer)
        if n <= max_par:
            met += 1
        else:
            fails.append(f"too many paragraphs: {n}, limit {max_par}")
    return met / total, fails


def check_answer(task, answer):
    return check_report(task, answer)[0]


def load_tasks():
    return json.loads((config.evals_dir() / "tasks.json").read_text(encoding="utf-8"))


def _apply_checks(res, task):
    res["check"], res["check_failures"] = check_report(task, res["answer"])
    res["final"] = 0.5 * res["score"] / 10 + 0.5 * res["check"]


def rescore(results):
    """Recompute check, failures and final of saved results from the current tasks.json (matched by
    task text). Works offline, so old saved evals gain failure details without any model call."""
    by_text = {t["task"]: t for t in load_tasks()}
    for r in results or []:
        if r["task"] in by_text:
            _apply_checks(r, by_text[r["task"]])
        else:
            r.setdefault("check_failures", [])
    return results


def run_eval(provider, overrides=None, on_result=None):
    tasks = load_tasks()
    # One task makes at most 8 model calls (plan, 4 steps, review, revision, review). Unless the owner
    # set MAX_CALLS / MAX_SECONDS explicitly, size the budget to the task list so a longer eval is
    # not cut off. An explicit owner setting is always honoured.
    max_calls = config.max_calls() if os.getenv("MAX_CALLS") else 8 * len(tasks)
    max_seconds = config.max_seconds() if os.getenv("MAX_SECONDS") else max(900, 90 * len(tasks))
    ctx = Context(provider=provider, budget=Budget(max_calls=max_calls, max_seconds=max_seconds),
                  overrides=overrides or {})
    results = []
    for t in tasks:
        res = run_task(t["task"], ctx)
        _apply_checks(res, t)
        results.append(res)
        if on_result:
            on_result(res)
    avg = sum(r["final"] for r in results) / max(1, len(results))
    return avg, results


def run_eval_many(provider, runs, overrides=None, on_result=None, on_run=None):
    """Run the whole eval `runs` times. Returns (list of averages, results of the last run).
    Repeating shows how much the score moves on its own (model and reviewer randomness)."""
    avgs, last = [], None
    for i in range(runs):
        avg, last = run_eval(provider, overrides=overrides, on_result=on_result)
        avgs.append(avg)
        if on_run:
            on_run(i + 1, avg)
    return avgs, last


def summarize(avgs):
    """(mean, min, max) of a list of scores."""
    return sum(avgs) / len(avgs), min(avgs), max(avgs)


def save_last(results):
    (config.state_dir() / "last_eval.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def load_last():
    """Results of the most recent eval, or None if none has been run yet."""
    f = config.state_dir() / "last_eval.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
