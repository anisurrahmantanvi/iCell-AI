"""Kill switch: a STOP file in the state directory. Checked before every model call."""
from ..config import state_dir


class Stopped(Exception):
    """Raised when the kill switch is engaged or a budget limit is reached."""


def _file():
    return state_dir() / "STOP"


def engage():
    _file().write_text("stop\n")


def release():
    _file().unlink(missing_ok=True)


def is_engaged() -> bool:
    return _file().exists()


def check():
    if is_engaged():
        raise Stopped("KILL SWITCH: STOP ফাইল আছে, সব বন্ধ।")
