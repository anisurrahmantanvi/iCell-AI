from .base import ask, jparse


def review(task, answer, ctx):
    """Returns (score 0-10, feedback). A malformed reply counts as score 0."""
    raw = ask("reviewer",
              f"Task: {task}\n\nAnswer:\n{answer}\n\n"
              'Return ONLY JSON: {"score": <0-10>, "feedback": "<one short paragraph>"}', ctx)
    r = jparse(raw, {})
    if not isinstance(r, dict):
        r = {}
    try:
        score = max(0.0, min(10.0, float(r.get("score", 0))))
    except (TypeError, ValueError):
        score = 0.0
    return score, str(r.get("feedback", ""))
