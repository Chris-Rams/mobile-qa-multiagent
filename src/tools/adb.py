from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional


def _run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Runs a command and returns the CompletedProcess.
    Raises a RuntimeError if the command fails.
    """
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to run command: {cmd}\n{e}") from e

    if p.returncode != 0:
        raise RuntimeError(
            f"Command failed ({p.returncode}): {' '.join(cmd)}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
        )
    return p


def devices() -> str:
    return _run(["adb", "devices"]).stdout


def wait_for_device(timeout_sec: int = 60) -> None:
    start = time.time()
    while time.time() - start < timeout_sec:
        out = devices()
        # naive but works: look for "device" line that is not "List of devices"
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        ok = any(("device" in ln and "List of devices" not in ln and "offline" not in ln) for ln in lines)
        if ok:
            return
        time.sleep(1)
    raise RuntimeError("No adb device detected. Is the emulator running?")


def launch_app(package: str) -> None:
    # Most reliable launch method
    _run(["adb", "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])


def tap(x: int, y: int) -> None:
    _run(["adb", "shell", "input", "tap", str(x), str(y)])


def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
    _run(["adb", "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])


def input_text(text: str) -> None:
    # Android "input text" needs spaces encoded as %s
    safe = text.replace(" ", "%s")
    _run(["adb", "shell", "input", "text", safe])


def keyevent(keycode: int) -> None:
    _run(["adb", "shell", "input", "keyevent", str(keycode)])


def screenshot(local_path: str | Path, device_tmp_path: str = "/sdcard/__qa_tmp.png") -> Path:
    """
    Screenshot in a Windows safe way:
    1) screencap to device
    2) adb pull to local_path
    """
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    _run(["adb", "shell", "screencap", "-p", device_tmp_path])
    _run(["adb", "pull", device_tmp_path, str(local_path)])
    return local_path


def sleep(seconds: float) -> None:
    time.sleep(seconds)
