"""Proposals and the human approval gate.

Agents may only call create(). approve() needs a `confirm` callback that the CLI backs with a
real terminal question, so no agent code path can apply a change by itself.
"""
import json
import time

from .. import config
from . import audit


def _dir():
    d = config.state_dir() / "proposals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create(target, new_prompt, reason=""):
    new_prompt = (new_prompt or "").strip()
    if target not in config.EVOLVABLE:
        raise ValueError(f"target '{target}' বদলানো যায় না (শুধু {config.EVOLVABLE})")
    if not (20 <= len(new_prompt) <= 2000):
        raise ValueError("প্রম্পটের দৈর্ঘ্য ২০-২০০০ অক্ষরের মধ্যে হতে হবে")
    pid = len(list(_dir().glob("*.json"))) + 1
    prop = {"id": pid, "target": target, "new_prompt": new_prompt, "reason": str(reason), "status": "pending"}
    (_dir() / f"{pid:03d}.json").write_text(json.dumps(prop, ensure_ascii=False, indent=2), encoding="utf-8")
    audit.log("proposal_created", id=pid, target=target)
    return pid


def get(pid):
    f = _dir() / f"{int(pid):03d}.json"
    if not f.exists():
        raise KeyError(f"প্রস্তাব #{pid} নেই")
    return json.loads(f.read_text(encoding="utf-8"))


def all_proposals():
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(_dir().glob("*.json"))]


def approve(pid, confirm):
    """Apply a pending proposal only if confirm(proposal) returns True. Old prompt is kept in history."""
    p = get(pid)
    if p["status"] != "pending":
        raise ValueError(f"প্রস্তাব #{pid} এখন '{p['status']}'")
    if not confirm(p):
        audit.log("proposal_declined", id=p["id"])
        return False
    target = config.prompts_dir() / f"{p['target']}.txt"
    hist = config.state_dir() / "history"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / f"{p['target']}-{time.strftime('%Y%m%d-%H%M%S')}-p{p['id']}.txt").write_text(
        target.read_text(encoding="utf-8"), encoding="utf-8")
    target.write_text(p["new_prompt"] + "\n", encoding="utf-8")
    p["status"] = "approved"
    (_dir() / f"{p['id']:03d}.json").write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    audit.log("proposal_approved", id=p["id"], target=p["target"])
    return True
