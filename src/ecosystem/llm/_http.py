"""Tiny stdlib HTTP helper (no pip dependencies)."""
import json
import time
import urllib.error
import urllib.request


class HttpError(RuntimeError):
    """HTTP error answer. The message is short; the full body stays available for providers
    that want to inspect it (see llm/groq.py)."""

    def __init__(self, code, body):
        super().__init__(f"HTTP {code}: {body[:300]!r}")
        self.code = code
        self.body = body


def post_json(url, body, headers=None, retries=2):
    data = json.dumps(body).encode()
    # Some providers sit behind Cloudflare, which rejects Python's default "Python-urllib/x.y"
    # User-Agent with HTTP 403 "error code: 1010". A plain client name avoids that.
    h = {"Content-Type": "application/json", "User-Agent": "iCell-AI/0.1", **(headers or {})}
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:  # free-tier rate limit
                time.sleep(5 * (attempt + 1))
                continue
            raise HttpError(e.code, e.read().decode("utf-8", "replace")[:20000])
        except (urllib.error.URLError, TimeoutError, OSError) as e:  # no internet, DNS, proxy, timeout
            raise RuntimeError(f"সংযোগ ব্যর্থ ({e.__class__.__name__}): {e}")
