from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SupervisorDecision:
    action: str  # "continue" | "retry" | "stop"
    reason: str


class Supervisor:

    def __init__(self, max_retries_per_step: int = 1):
        self.max_retries_per_step = max_retries_per_step
        self._retries: Dict[str, int] = {}

    def _key(self, test_name: str, step_index: int) -> str:
        return f"{test_name}::{step_index}"

    def _classify_failure(self, step_record: Dict[str, Any]) -> str:
        """
        Lightweight reasoning to distinguish:
        - infra/tooling errors vs
        - missing / incorrect UI (assertion failures).
        """
        err = (step_record.get("error") or "").lower()

        # Typical assertion-style errors from your orchestrator/locator
        if "could not find target" in err or "target not found" in err or "element not found" in err:
            return "ASSERTION_FAILURE"

        # Typical execution-level issues: adb, screencap, timeouts, parsing, etc.
        if "adb" in err or "uiautomator" in err or "screencap" in err or "timeout" in err:
            return "EXECUTION_FAILURE"

        return "UNKNOWN_FAILURE"

    def decide(self, test_name: str, step_index: int, step_record: Dict[str, Any]) -> SupervisorDecision:
        # Step passed -> just move on
        if step_record.get("ok", False):
            return SupervisorDecision(action="continue", reason="Step passed")

        # Step failed -> reason about the failure
        failure_type = self._classify_failure(step_record)
        step_record["failure_type"] = failure_type  # this will show up in your JSON log

        key = self._key(test_name, step_index)
        count = self._retries.get(key, 0)

        # Retry once for common flaky actions
        step_type = step_record.get("type", "")
        flaky_types = {"tap", "tap_target", "input_text", "launch_app"}

        if step_type in flaky_types and count < self.max_retries_per_step:
            self._retries[key] = count + 1
            return SupervisorDecision(
                action="retry",
                reason=f"Retrying flaky step (attempt {count+1}); failure_type={failure_type}",
            )

        # No retries left: stop this test
        return SupervisorDecision(
            action="stop",
            reason=f"Step failed and no retries left; failure_type={failure_type}",
        )
