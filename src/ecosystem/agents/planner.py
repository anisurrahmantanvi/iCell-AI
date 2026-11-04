from .base import ask, jparse


def plan(task, ctx):
    raw = ask("planner", f"Task: {task}\nReturn ONLY a JSON list of 2-4 short steps.", ctx)
    steps = jparse(raw, None)
    if not isinstance(steps, list) or not steps:
        return [task]
    return [str(s) for s in steps][:4]
