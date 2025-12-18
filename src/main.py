from __future__ import annotations

from src.orchestrator import load_suite, _safe_name, LOGS_DIR, SHOTS_DIR
from src.tools import adb

from src.agents.planner import Planner
from src.agents.executor import Executor
from src.agents.supervisor import Supervisor

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main() -> None:
    suite = load_suite("src/testsuites/obsidian_suite.yaml")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    adb.wait_for_device()

    planner = Planner(suite)
    executor = Executor()
    supervisor = Supervisor(max_retries_per_step=1)

    run_id = _ts()
    run_log_path = Path("artifacts/logs") / f"run_{run_id}.json"

    run_log: Dict[str, Any] = {
        "run_id": run_id,
        "suite": {"name": suite.name, "description": suite.description},
        "tests": [],
    }

    current_test_name = None
    current_test_rec = None

    while True:
        item = planner.next_item()
        if item is None:
            break

        # start new test record when test changes
        if current_test_name != item.test_name:
            if current_test_rec is not None:
                run_log["tests"].append(current_test_rec)
            current_test_name = item.test_name
            current_test_rec = {"name": item.test_name, "steps": [], "status": "PASS"}

        safe_test = _safe_name(item.test_name)

        # Execute step, let supervisor decide
        while True:
            rec = executor.execute(item.step, safe_test, item.step_index)
            current_test_rec["steps"].append(rec)

            decision = supervisor.decide(item.test_name, item.step_index, rec)
            rec["supervisor_action"] = decision.action
            rec["supervisor_reason"] = decision.reason

            if decision.action == "continue":
                break

            if decision.action == "retry":
                continue

            if decision.action == "stop":
                current_test_rec["status"] = "FAIL"
                # skip remaining steps in this test by advancing planner until test changes
                # simplest: just mark fail; planner will still output remaining steps unless you add skip logic
                break

        if current_test_rec["status"] == "FAIL":
            # Optional: stop entire run on first test failure
            # break
            pass

    # append last test
    if current_test_rec is not None:
        run_log["tests"].append(current_test_rec)

    run_log_path.write_text(json.dumps(run_log, indent=2), encoding="utf-8")
    print(f"Done. Run log saved to: {run_log_path}")


if __name__ == "__main__":
    main()
