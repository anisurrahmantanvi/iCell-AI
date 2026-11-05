"""HTTP API (standard library only). Same functions as the CLI, behind two tokens.

Tokens (environment variables, both required, >= 16 chars, must differ):
  ECOSYSTEM_API_TOKEN    "user": run, eval, improve, test, read proposals/status, kill
  ECOSYSTEM_OWNER_TOKEN  "owner": everything above, plus approve, resume, audit log

Design rules:
- Approving a change and lifting the kill switch are owner-only. Keep the owner token away from agents.
- Anyone with a valid token may ENGAGE the kill switch (the safe direction).
- One model job at a time (409 if busy), so the budget and kill switch stay meaningful.
- Binds to 127.0.0.1 by default. This server speaks plain HTTP: if you expose it beyond localhost,
  put it behind a TLS reverse proxy.
"""
import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .. import config
from ..agents.base import Context
from ..agents.orchestrator import run_task
from ..core import audit, killswitch, proposals
from ..core.killswitch import Stopped
from ..evals.runner import load_last, rescore, run_eval, save_last
from ..evolution.improver import propose
from ..llm import get_provider

MAX_BODY = 64 * 1024
MAX_TASK_CHARS = 2000
_job_lock = threading.Lock()


def _tokens():
    return os.environ.get("ECOSYSTEM_API_TOKEN", ""), os.environ.get("ECOSYSTEM_OWNER_TOKEN", "")


def _role_for(auth_header):
    if not auth_header.startswith("Bearer "):
        return None
    given = auth_header[7:].strip().encode()
    api_tok, owner_tok = _tokens()
    if owner_tok and hmac.compare_digest(given, owner_tok.encode()):
        return "owner"
    if api_tok and hmac.compare_digest(given, api_tok.encode()):
        return "user"
    return None


class _Busy(Exception):
    pass


def _run_exclusive(fn):
    if not _job_lock.acquire(blocking=False):
        raise _Busy()
    try:
        return fn()
    finally:
        _job_lock.release()


def _pid(text):
    try:
        return int(text)
    except ValueError:
        raise ValueError("প্রস্তাবের নম্বর সংখ্যা হতে হবে")


def route(method, path, query, role, body):
    """Returns (http_code, json_object)."""
    if method == "GET":
        if path == "/status":
            return 200, {"killed": killswitch.is_engaged(), "provider": get_provider().name, "role": role}
        if path == "/proposals":
            return 200, {"proposals": proposals.all_proposals()}
        if path.startswith("/proposals/"):
            try:
                return 200, proposals.get(_pid(path.split("/")[2]))
            except KeyError as e:
                return 404, {"error": str(e)}
        if path == "/audit":
            if role != "owner":
                return 403, {"error": "শুধু owner"}
            n = min(int(query.get("n", ["50"])[0]), 200)
            f = config.state_dir() / "audit.jsonl"
            lines = f.read_text(encoding="utf-8").splitlines()[-n:] if f.exists() else []
            return 200, {"entries": [json.loads(x) for x in lines]}
        return 404, {"error": "পথ নেই"}

    # POST
    if path == "/kill":
        killswitch.engage()
        audit.log("kill", via="api", role=role)
        return 200, {"killed": True}
    if path == "/resume":
        if role != "owner":
            return 403, {"error": "শুধু owner Kill switch তুলতে পারে"}
        killswitch.release()
        audit.log("resume", via="api", role=role)
        return 200, {"killed": False}
    if path == "/run":
        task = body.get("task")
        if not isinstance(task, str) or not task.strip() or len(task) > MAX_TASK_CHARS:
            raise ValueError(f"task লাগবে (১-{MAX_TASK_CHARS} অক্ষর)")
        return 200, _run_exclusive(lambda: run_task(task.strip(), Context(provider=get_provider())))
    if path == "/eval":
        def job():
            avg, results = run_eval(get_provider())
            save_last(results)
            return {"average": avg, "results": results}
        return 200, _run_exclusive(job)
    if path == "/improve":
        results = rescore(load_last())
        if results is None:
            return 409, {"error": "আগে POST /eval চালান"}
        pid = _run_exclusive(lambda: propose(results, Context(provider=get_provider())))
        if pid is None:
            return 200, {"proposal": None, "note": "প্রস্তাব অবৈধ ছিল, বাতিল"}
        return 200, {"proposal": proposals.get(pid)}
    parts = path.strip("/").split("/")
    if len(parts) == 3 and parts[0] == "proposals" and parts[2] in ("test", "approve"):
        pid = _pid(parts[1])
        try:
            prop = proposals.get(pid)
        except KeyError as e:
            return 404, {"error": str(e)}
        if parts[2] == "test":
            def job():
                base, _ = run_eval(get_provider())
                new, _ = run_eval(get_provider(), overrides={prop["target"]: prop["new_prompt"]})
                return {"before": base, "after": new}
            return 200, _run_exclusive(job)
        if role != "owner":
            return 403, {"error": "শুধু owner অনুমোদন দিতে পারে"}
        if body.get("confirm") is not True:
            raise ValueError('অনুমোদনের জন্য body-তে {"confirm": true} লাগবে')
        proposals.approve(pid, lambda p: True)  # the authenticated owner request IS the human decision
        return 200, {"proposal": proposals.get(pid)}
    return 404, {"error": "পথ নেই"}


class Handler(BaseHTTPRequestHandler):
    server_version = "ecosystem"

    def log_message(self, *args):  # access log goes to the audit log instead
        pass

    def _send(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("body অনেক বড়")
        raw = self.rfile.read(length) if length else b"{}"
        obj = json.loads(raw or b"{}")
        if not isinstance(obj, dict):
            raise ValueError("body JSON object হতে হবে")
        return obj

    def _handle(self, method):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        if method == "GET" and path == "/health":
            return self._send(200, {"ok": True})
        role = _role_for(self.headers.get("Authorization", ""))
        if role is None:
            return self._send(401, {"error": "unauthorized"})
        try:
            body = self._body() if method == "POST" else {}
            audit.log("api", method=method, path=path, role=role)
            code, obj = route(method, path, parse_qs(url.query), role, body)
        except Stopped as e:
            code, obj = 503, {"error": str(e), "stopped": True}
        except _Busy:
            code, obj = 409, {"error": "অন্য একটা কাজ চলছে, পরে চেষ্টা করুন"}
        except ValueError as e:  # includes bad JSON
            code, obj = 400, {"error": str(e)}
        except Exception as e:  # never leak internals to the client
            audit.log("api_error", path=path, error=repr(e)[:300])
            code, obj = 500, {"error": "সার্ভারে সমস্যা (বিস্তারিত audit log-এ)"}
        self._send(code, obj)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def make_server(host="127.0.0.1", port=8080):
    api_tok, owner_tok = _tokens()
    if len(api_tok) < 16 or len(owner_tok) < 16 or api_tok == owner_tok:
        raise ValueError("ECOSYSTEM_API_TOKEN ও ECOSYSTEM_OWNER_TOKEN দুটোই লাগবে: ১৬+ অক্ষর, আলাদা আলাদা")
    return ThreadingHTTPServer((host, port), Handler)


def serve(host="127.0.0.1", port=8080):
    srv = make_server(host, port)
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("সতর্কতা: এটা সাধারণ HTTP। লোকালহোস্টের বাইরে দিলে TLS reverse proxy-র পেছনে রাখুন।")
    print(f"API চলছে http://{host}:{srv.server_address[1]}  (বন্ধ: Ctrl+C)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nবন্ধ।")
    finally:
        srv.server_close()
