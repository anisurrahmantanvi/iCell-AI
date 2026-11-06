import json
import threading
import unittest
import urllib.error
import urllib.request

from _base import EcoTestCase

from ecosystem import config
from ecosystem.api.server import make_server

API = "a" * 20
OWNER = "o" * 20


class ApiTests(EcoTestCase):
    def setUp(self):
        super().setUp()
        import os
        os.environ["ECOSYSTEM_API_TOKEN"] = API
        os.environ["ECOSYSTEM_OWNER_TOKEN"] = OWNER
        self.srv = make_server("127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        import os
        self.srv.shutdown()
        self.srv.server_close()
        os.environ.pop("ECOSYSTEM_API_TOKEN", None)
        os.environ.pop("ECOSYSTEM_OWNER_TOKEN", None)
        super().tearDown()

    def call(self, method, path, token=None, body=None):
        data = json.dumps(body).encode() if body is not None else (b"{}" if method == "POST" else None)
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_health_is_open_but_everything_else_needs_a_token(self):
        self.assertEqual(self.call("GET", "/health")[0], 200)
        self.assertEqual(self.call("GET", "/status")[0], 401)
        self.assertEqual(self.call("GET", "/status", "wrong-token-wrong-token")[0], 401)
        self.assertEqual(self.call("GET", "/status", API)[0], 200)

    def test_chat_page_is_served_without_token_and_holds_no_secret(self):
        with urllib.request.urlopen(self.base + "/") as r:
            html = r.read().decode()
            self.assertEqual(r.status, 200)
            self.assertIn("text/html", r.headers["Content-Type"])
            self.assertIn("default-src 'none'", r.headers["Content-Security-Policy"])
        self.assertIn("iCell-AI", html)
        self.assertNotIn(API, html)
        self.assertNotIn(OWNER, html)
        self.assertNotIn("innerHTML", html)  # model output must only go in via textContent

    def test_weak_or_equal_tokens_refuse_to_start(self):
        import os
        os.environ["ECOSYSTEM_OWNER_TOKEN"] = API
        with self.assertRaises(ValueError):
            make_server("127.0.0.1", 0)
        os.environ["ECOSYSTEM_OWNER_TOKEN"] = "short"
        with self.assertRaises(ValueError):
            make_server("127.0.0.1", 0)

    def test_run_and_validation(self):
        code, res = self.call("POST", "/run", API, {"task": "hello"})
        self.assertEqual(code, 200)
        self.assertEqual(res["score"], 7.0)
        self.assertEqual(self.call("POST", "/run", API, {"task": ""})[0], 400)
        self.assertEqual(self.call("POST", "/run", API, {})[0], 400)

    def test_kill_switch_over_api(self):
        self.assertEqual(self.call("POST", "/kill", API)[0], 200)          # user may engage
        code, res = self.call("POST", "/run", API, {"task": "x"})
        self.assertEqual(code, 503)
        self.assertTrue(res["stopped"])
        self.assertEqual(self.call("POST", "/resume", API)[0], 403)        # user may NOT lift
        self.assertEqual(self.call("POST", "/resume", OWNER)[0], 200)
        self.assertEqual(self.call("POST", "/run", API, {"task": "x"})[0], 200)

    def test_only_owner_can_approve_and_needs_confirm(self):
        self.assertEqual(self.call("POST", "/eval", API)[0], 200)
        code, res = self.call("POST", "/improve", API)
        self.assertEqual(code, 200)
        pid = res["proposal"]["id"]
        before = (config.prompts_dir() / "worker.txt").read_text(encoding="utf-8")
        self.assertEqual(self.call("POST", f"/proposals/{pid}/approve", API, {"confirm": True})[0], 403)
        self.assertEqual(self.call("POST", f"/proposals/{pid}/approve", OWNER, {})[0], 400)
        self.assertEqual((config.prompts_dir() / "worker.txt").read_text(encoding="utf-8"), before)
        self.assertEqual(self.call("POST", f"/proposals/{pid}/approve", OWNER, {"confirm": True})[0], 200)
        self.assertNotEqual((config.prompts_dir() / "worker.txt").read_text(encoding="utf-8"), before)
        self.assertEqual(self.call("POST", f"/proposals/{pid}/approve", OWNER, {"confirm": True})[0], 400)  # no double apply

    def test_improve_needs_eval_first_and_unknown_proposal_404(self):
        self.assertEqual(self.call("POST", "/improve", API)[0], 409)
        self.assertEqual(self.call("GET", "/proposals/99", API)[0], 404)

    def test_audit_is_owner_only(self):
        self.call("POST", "/run", API, {"task": "x"})
        self.assertEqual(self.call("GET", "/audit", API)[0], 403)
        code, res = self.call("GET", "/audit?n=5", OWNER)
        self.assertEqual(code, 200)
        self.assertLessEqual(len(res["entries"]), 5)

    def test_proposal_test_endpoint(self):
        self.call("POST", "/eval", API)
        pid = self.call("POST", "/improve", API)[1]["proposal"]["id"]
        code, res = self.call("POST", f"/proposals/{pid}/test", API)
        self.assertEqual(code, 200)
        self.assertIn("before", res)
        self.assertIn("after", res)


if __name__ == "__main__":
    unittest.main()
