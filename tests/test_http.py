import json
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

from _base import EcoTestCase

from ecosystem.core import killswitch
from ecosystem.core.killswitch import Stopped
from ecosystem.llm._http import HttpError, post_json


class _Scripted(BaseHTTPRequestHandler):
    """Answers with the statuses in `script` (in order), then 200. Records headers and call count."""
    script = []
    calls = 0
    extra_headers = {}
    error_text = "x"
    seen = {}

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        cls = type(self)
        cls.calls += 1
        cls.seen = dict(self.headers)
        status = cls.script.pop(0) if cls.script else 200
        data = b'{"ok": true}' if status == 200 else json.dumps({"error": {"message": cls.error_text}}).encode()
        self.send_response(status)
        for k, v in cls.extra_headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@contextmanager
def server(script=None, extra_headers=None, error_text="x"):
    _Scripted.script = list(script or [])
    _Scripted.calls = 0
    _Scripted.extra_headers = extra_headers or {}
    _Scripted.error_text = error_text
    _Scripted.seen = {}
    srv = HTTPServer(("127.0.0.1", 0), _Scripted)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/"
    finally:
        srv.shutdown()
        srv.server_close()


class HttpHeaderTests(EcoTestCase):
    def test_sends_custom_user_agent_not_python_urllib(self):
        with server() as url:
            r = post_json(url, {"a": 1}, headers={"Authorization": "Bearer x"})
        self.assertEqual(r, {"ok": True})
        self.assertFalse(_Scripted.seen["User-Agent"].startswith("Python-urllib"))
        self.assertEqual(_Scripted.seen["Authorization"], "Bearer x")  # caller headers still pass through


class HttpRetryTests(EcoTestCase):
    def test_retries_503_then_succeeds(self):
        sleeps = []
        with server([503, 503]) as url:
            r = post_json(url, {}, sleep=sleeps.append)
        self.assertEqual(r, {"ok": True})
        self.assertEqual(_Scripted.calls, 3)
        self.assertEqual(sleeps, [3, 6])  # growing pauses

    def test_gives_up_after_the_retry_limit(self):
        with server([503] * 10) as url:
            with self.assertRaises(HttpError) as cm:
                post_json(url, {}, retries=2, sleep=lambda s: None)
        self.assertEqual(cm.exception.code, 503)
        self.assertEqual(_Scripted.calls, 3)  # first try + 2 retries

    def test_client_errors_are_not_retried(self):
        for code in (400, 401, 403, 404):
            with server([code]) as url:
                with self.assertRaises(HttpError) as cm:
                    post_json(url, {}, sleep=lambda s: None)
            self.assertEqual(cm.exception.code, code)
            self.assertEqual(_Scripted.calls, 1, code)

    def test_retry_after_header_is_used(self):
        sleeps = []
        with server([429], extra_headers={"Retry-After": "7"}) as url:
            post_json(url, {}, sleep=sleeps.append)
        self.assertEqual(sleeps, [7.0])

    def test_daily_quota_429_is_not_retried(self):
        with server([429], error_text="Rate limit reached ... on tokens per day (TPD): Limit 200000") as url:
            with self.assertRaises(HttpError) as cm:
                post_json(url, {}, sleep=lambda s: None)
        self.assertEqual(cm.exception.code, 429)
        self.assertEqual(_Scripted.calls, 1)

    def test_kill_switch_ends_a_retry_loop(self):
        with server([503] * 10) as url:
            with self.assertRaises(Stopped):
                post_json(url, {}, sleep=lambda s: killswitch.engage())  # STOP arrives during the pause
        self.assertEqual(_Scripted.calls, 1)  # no second attempt after STOP

    def test_connection_failure_becomes_runtime_error(self):
        # nothing listens on port 1: must be a clean RuntimeError, not a raw URLError traceback
        with self.assertRaises(RuntimeError):
            post_json("http://127.0.0.1:1/", {"a": 1}, retries=0)

    def test_dead_connection_is_retried_only_twice(self):
        sleeps = []
        with self.assertRaises(RuntimeError):
            post_json("http://127.0.0.1:1/", {}, retries=4, sleep=sleeps.append)
        self.assertEqual(len(sleeps), 2)


if __name__ == "__main__":
    unittest.main()
