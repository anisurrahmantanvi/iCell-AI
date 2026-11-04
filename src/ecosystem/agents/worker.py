from .base import ask


def work(task, step, ctx):
    return ask("worker", f"Overall task: {task}\nYour step: {step}", ctx)


def revise(task, answer, feedback, ctx):
    return ask("worker",
               f"Task: {task}\nPrevious answer:\n{answer}\nReviewer feedback: {feedback}\n"
               "Write one improved final answer.", ctx)
