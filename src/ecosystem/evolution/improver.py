import json

from .. import config
from ..agents.base import ask, get_prompt, jparse
from ..core import audit, proposals


def propose(results, ctx):
    """Ask the improver for one prompt change based on eval feedback. Returns proposal id or None.
    Invalid proposals (wrong target, bad length) are rejected automatically."""
    payload = {
        "current_prompts": {n: get_prompt(n) for n in config.EVOLVABLE},
        "eval_feedback": [{"task": r["task"], "final": round(r["final"], 2), "feedback": r["feedback"]}
                          for r in results],
        "allowed_targets": list(config.EVOLVABLE),
    }
    raw = ask("improver", json.dumps(payload, ensure_ascii=False), ctx)
    p = jparse(raw, {})
    if not isinstance(p, dict):
        p = {}
    try:
        return proposals.create(p.get("target"), p.get("new_prompt", ""), p.get("reason", ""))
    except ValueError as e:
        audit.log("proposal_rejected_auto", why=str(e), raw=raw[:300])
        return None
