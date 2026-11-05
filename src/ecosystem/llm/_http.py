"""Tiny stdlib HTTP helper (no pip dependencies)."""
import json
import time
import urllib.error
import urllib.request


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
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:  # no internet, DNS, proxy, timeout
            raise RuntimeError(f"সংযোগ ব্যর্থ ({e.__class__.__name__}): {e}")
