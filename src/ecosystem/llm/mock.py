"""Fake provider for testing the plumbing. Its answers say nothing about real model quality."""
import json


class MockProvider:
    name = "mock"

    def chat(self, system, user, role="worker"):
        if role == "planner":
            return '["Understand the task", "Write the answer"]'
        if role == "worker":
            return "Mock answer: stop, risk, code, test, compare."
        if role == "reviewer":
            return '{"score": 7, "feedback": "mock feedback: add more detail and one example"}'
        if role == "improver":
            return json.dumps({
                "target": "worker",
                "new_prompt": "You are the Worker. Do exactly the step given. Be concise, concrete, and include one example.",
                "reason": "mock proposal",
            })
        return "mock"
