"""Append-only audit log (state/audit.jsonl)."""
import json
import time

from ..config import state_dir


def log(event, **fields):
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "event": event, **fields}
    with open(state_dir() / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
