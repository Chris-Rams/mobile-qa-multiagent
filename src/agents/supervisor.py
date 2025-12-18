from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SupervisorDecision:
    action: str  # "continue" | "retry" | "stop"
    reason: str


class Supervisor:
    """
    Minimal Supervisor:
    - If a step fails, retry once for flaky UI steps
    - Otherwise stop that test
    """

    def __init__(self, max_retries_per_step: int = 1):
        self.max_retries_per_step = max_retries_per_step
        self._retries: Dict[str, int] = {}

    def _key(self, test_name: str, step_index: int) -> str:
        return f"{test_name}::{step_index}"

    def decide(self, test_name: str, step_index: int, step_record: Dict[str, Any]) -> SupervisorDecision:
        if step_record.get("ok", False):
            return SupervisorDecision(action="continue", reason="Step passed")

        # Step failed
        key = self._key(test_name, step_index)
        count = self._retries.get(key, 0)

        # Retry once for common flaky actions
        step_type = step_record.get("type", "")
        flaky_types = {"tap", "tap_target", "input_text", "launch_app"}

        if step_type in flaky_types and count < self.max_retries_per_step:
            self._retries[key] = count + 1
            return SupervisorDecision(action="retry", reason=f"Retrying flaky step (attempt {count+1})")

        return SupervisorDecision(action="stop", reason="Step failed and no retries left")
