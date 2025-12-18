from __future__ import annotations
from typing import Dict, Any

from src.tools.types import Step
from src import orchestrator


class Executor:
    """
    Minimal Executor:
    Delegates actual device work to orchestrator.run_step
    """

    def execute(self, step: Step, safe_test_name: str, step_index: int) -> Dict[str, Any]:
        return orchestrator.run_step(step, safe_test_name, step_index)
