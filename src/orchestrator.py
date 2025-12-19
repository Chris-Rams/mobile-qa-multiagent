from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import yaml

from src.tools import adb
from src.tools.types import parse_suite, TestSuite, Step
from src.tools import vision


ARTIFACTS_DIR = Path("artifacts")
LOGS_DIR = ARTIFACTS_DIR / "logs"
SHOTS_DIR = ARTIFACTS_DIR / "screenshots"


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_name(name: str) -> str:
    """
    Makes a string safe to use in file names.
    Keeps letters, numbers, underscore, and hyphen.
    Replaces everything else with underscore.
    """
    base = name.replace(" ", "_")
    return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in base)


def load_suite(path: str) -> TestSuite:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return parse_suite(data)


def run_step(step: Step, test_name: str, step_index: int) -> Dict[str, Any]:
    """
    Executes one YAML step. Returns a dict record you can log.
    """
    record: Dict[str, Any] = {
        "type": step.type,
        "description": step.description,
        "ok": True,
        "error": None,
        "screenshot": None,
    }

    try:
        if step.type == "launch_app":
            if not step.app:
                raise ValueError("launch_app requires 'app'")
            adb.launch_app(step.app)
            adb.sleep(5.0)

        elif step.type == "tap":
            if step.x is None or step.y is None:
                raise ValueError("tap requires x and y")
            adb.tap(step.x, step.y)
            adb.sleep(0.7)

        elif step.type == "input_text":
            if step.text is None:
                raise ValueError("input_text requires text")
            adb.input_text(step.text)
            adb.sleep(0.5)

        elif step.type == "sleep":
            seconds = step.sleep_seconds or 1.0
            adb.sleep(seconds)

        elif step.type == "screenshot":
            if step.path:
                out_path = Path(step.path)
            else:
                out_path = SHOTS_DIR / f"{_ts()}_{test_name}_step{step_index}.png"

            out_path.parent.mkdir(parents=True, exist_ok=True)
            adb.screenshot(out_path)
            record["screenshot"] = str(out_path)

        elif step.type == "tap_target":
            if not step.target:
                raise ValueError("tap_target requires 'target'")

            locate_shot = SHOTS_DIR / f"{_ts()}_{test_name}_locate_step{step_index}.png"
            adb.screenshot(locate_shot)
            record["locate_screenshot"] = str(locate_shot)

            # Try primary target
            result = vision.locate_tap_point(
                screenshot_path=locate_shot,
                target=step.target,
                hint=step.hint,
            )
            record["vision"] = result
            used_target = step.target

            # If that failed, try alt target
            if not result.get("found") and getattr(step, "alt_target", None):
                alt_result = vision.locate_tap_point(
                    screenshot_path=locate_shot,
                    target=step.alt_target,
                    hint=step.hint,
                )
                record["vision_alt"] = alt_result
                if alt_result.get("found"):
                    result = alt_result
                    used_target = step.alt_target

            if not result.get("found"):
                raise RuntimeError(
                    f"Could not find target '{step.target}' or alt_target '{step.alt_target}'"
                )

            record["used_target"] = used_target

            x = int(result["x"])
            y = int(result["y"])
            adb.tap(x, y)
            adb.sleep(0.8)

            after_tap_path = SHOTS_DIR / f"{_ts()}_{test_name}_after_tap_target_{step_index}.png"
            adb.screenshot(after_tap_path)
            record["after_tap_screenshot"] = str(after_tap_path)
        
        elif step.type == "keyevent":
            if step.keycode is None:
                raise ValueError("keyevent requires keycode")
            adb.keyevent(step.keycode)
            adb.sleep(0.5)



        else:
            raise ValueError(f"Unknown step type: {step.type}")

    except Exception as e:
        record["ok"] = False
        record["error"] = str(e)

    return record


def run_suite(yaml_path: str) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    suite = load_suite(yaml_path)

    adb.wait_for_device()

    run_id = _ts()
    run_log_path = LOGS_DIR / f"run_{run_id}.json"

    run_log: Dict[str, Any] = {
        "run_id": run_id,
        "suite": {"name": suite.name, "description": suite.description},
        "tests": [],
    }

    for test in suite.tests:
        test_rec: Dict[str, Any] = {"name": test.name, "steps": [], "status": "PASS"}

        safe_test_name = _safe_name(test.name)

        for i, step in enumerate(test.steps, start=1):
            rec = run_step(step, safe_test_name, i)
            test_rec["steps"].append(rec)

            # Auto screenshot after action steps (including tap_target now)
            if step.type in {"launch_app", "tap", "tap_target", "input_text"}:
                auto_path = SHOTS_DIR / f"{run_id}_{safe_test_name}_after_{i}.png"
                try:
                    adb.screenshot(auto_path)
                    rec["auto_screenshot"] = str(auto_path)
                except Exception as e:
                    rec["auto_screenshot_error"] = str(e)

            if not rec["ok"]:
                test_rec["status"] = "FAIL"
                break

        run_log["tests"].append(test_rec)

    run_log_path.write_text(json.dumps(run_log, indent=2), encoding="utf-8")
    return run_log_path
