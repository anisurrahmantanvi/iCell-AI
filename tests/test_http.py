import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from ecosystem.llm._http import post_json


class _Recorder(BaseHTTPRequestHandler):
    seen = {}

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        _Recorder.seen = dict(self.headers)
        data = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class HttpHeaderTests(unittest.TestCase):
    def test_sends_custom_user_agent_not_python_urllib(self):
        srv = HTTPServer(("127.0.0.1", 0), _Recorder)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            r = post_json(f"http://127.0.0.1:{srv.server_address[1]}/", {"a": 1},
                          headers={"Authorization": "Bearer x"})
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(r, {"ok": True})
        self.assertFalse(_Recorder.seen["User-Agent"].startswith("Python-urllib"))
        self.assertEqual(_Recorder.seen["Authorization"], "Bearer x")  # caller headers still pass through


if __name__ == "__main__":
    unittest.main()
