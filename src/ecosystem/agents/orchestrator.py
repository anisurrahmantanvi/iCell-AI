"""Coordinator: plan -> work each step -> review -> at most one revision round."""
from . import planner, reviewer, worker

PASS_SCORE = 6


def run_task(task, ctx):
    steps = planner.plan(task, ctx)
    answer = "\n\n".join(worker.work(task, s, ctx) for s in steps)
    score, feedback = reviewer.review(task, answer, ctx)
    if score < PASS_SCORE:  # a single revision, then stop (no endless loops)
        answer = worker.revise(task, answer, feedback, ctx)
        score, feedback = reviewer.review(task, answer, ctx)
    return {"task": task, "plan": steps, "answer": answer, "score": score, "feedback": feedback}
