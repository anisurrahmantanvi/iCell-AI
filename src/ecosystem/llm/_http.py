"""Tiny stdlib HTTP helper (no pip dependencies)."""
import json
import time
import urllib.error
import urllib.request

from ..core import killswitch

# Worth retrying: rate limit, overloaded or temporarily broken server.
TRANSIENT = {429, 500, 502, 503, 504}


def _readable(body):
    """Prefer the API's own error message (it often names the quota that was exceeded) over raw JSON."""
    try:
        msg = json.loads(body)["error"]["message"]
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    except (ValueError, KeyError, TypeError):
        pass
    return body


class HttpError(RuntimeError):
    """HTTP error answer. The message is readable and short; the full body stays available for
    providers that want to inspect it (see llm/groq.py)."""

    def __init__(self, code, body):
        super().__init__(f"HTTP {code}: {_readable(body)[:700]}")
        self.code = code
        self.body = body


def _is_daily_limit(text):
    """A daily quota does not come back in seconds, so waiting and retrying is pointless."""
    low = text.lower()
    return any(m in low for m in ("per day", "perday", "(tpd)", "(rpd)"))


def _retry_after(value):
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _delay(attempt, retry_after=None):
    if retry_after is not None:
        return min(retry_after, 60)  # trust the server's hint, but never wait more than a minute
    return min(3 * 2 ** attempt, 30)  # 3, 6, 12, 24, 30 seconds


def post_json(url, body, headers=None, retries=4, sleep=time.sleep):
    """POST JSON, return the parsed answer.

    Temporary trouble (HTTP 429/5xx except daily quotas, timeouts, dropped connections) is retried
    with growing pauses. Client errors (400, 401, 403, 404 ...) are not: they will not fix
    themselves. The kill switch is checked before every attempt, so STOP also ends a retry loop."""
    data = json.dumps(body).encode()
    # Some providers sit behind Cloudflare, which rejects Python's default "Python-urllib/x.y"
    # User-Agent with HTTP 403 "error code: 1010". A plain client name avoids that.
    h = {"Content-Type": "application/json", "User-Agent": "iCell-AI/0.1", **(headers or {})}
    attempt = 0
    net_failures = 0
    while True:
        killswitch.check()
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:20000]
            if e.code in TRANSIENT and attempt < retries and not (e.code == 429 and _is_daily_limit(text)):
                sleep(_delay(attempt, _retry_after(e.headers.get("Retry-After"))))
                attempt += 1
                continue
            raise HttpError(e.code, text)
        except (urllib.error.URLError, TimeoutError, OSError) as e:  # no internet, DNS, proxy, timeout
            if attempt < retries and net_failures < 2:  # a dead connection rarely recovers in seconds
                sleep(_delay(attempt))
                attempt += 1
                net_failures += 1
                continue
            raise RuntimeError(f"সংযোগ ব্যর্থ ({e.__class__.__name__}): {e}")
