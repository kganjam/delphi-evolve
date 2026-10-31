import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def system_python_with_playwright():
    for exe in ("python3", sys.executable):
        w = shutil.which(exe) or exe
        r = subprocess.run([w, "-c", "import playwright"], capture_output=True)
        if r.returncode == 0:
            return w
    return None


def test_browser_smoke():
    py = system_python_with_playwright()
    if py is None:
        pytest.skip("playwright not installed")
    r = subprocess.run([py, str(ROOT / "tests" / "browser_smoke.py")], capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, r.stdout + r.stderr
