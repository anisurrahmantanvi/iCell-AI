import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class EcoTestCase(unittest.TestCase):
    """Runs every test in a throwaway copy of prompts/locked/evals with the mock provider."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for d in ("prompts", "locked", "evals"):
            shutil.copytree(REPO / d, self.tmp / d)
        self._old = {k: os.environ.get(k) for k in ("ECOSYSTEM_HOME", "PROVIDER", "MAX_CALLS", "MAX_SECONDS")}
        os.environ["ECOSYSTEM_HOME"] = str(self.tmp)
        os.environ["PROVIDER"] = "mock"
        os.environ.pop("MAX_CALLS", None)
        os.environ.pop("MAX_SECONDS", None)

    def tearDown(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)
