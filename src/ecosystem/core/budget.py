"""Hard limits on model calls and wall-clock time. Every call goes through tick()."""
import time

from .. import config
from .killswitch import Stopped, check


class Budget:
    def __init__(self, max_calls=None, max_seconds=None):
        self.max_calls = config.max_calls() if max_calls is None else max_calls
        self.max_seconds = config.max_seconds() if max_seconds is None else max_seconds
        self.used = 0
        self.t0 = time.time()

    def tick(self):
        check()  # kill switch first
        if self.used >= self.max_calls:
            raise Stopped(f"বাজেট শেষ: {self.max_calls}টা মডেল কলের সীমা।")
        if time.time() - self.t0 > self.max_seconds:
            raise Stopped(f"বাজেট শেষ: {self.max_seconds} সেকেন্ডের সীমা।")
        self.used += 1
