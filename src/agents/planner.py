from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from src.tools.types import TestSuite, TestCase, Step


@dataclass
class PlanItem:
    test_name: str
    step_index: int
    step: Step


class Planner:
    """
    Minimal Planner:
    Runs tests in order, steps in order.
    Later you can make this smarter (conditional paths, dynamic test generation, etc).
    """

    def __init__(self, suite: TestSuite):
        self.suite = suite
        self._test_i = 0
        self._step_i = 0

    def next_item(self) -> Optional[PlanItem]:
        # Move through tests sequentially
        while self._test_i < len(self.suite.tests):
            test: TestCase = self.suite.tests[self._test_i]

            if self._step_i < len(test.steps):
                item = PlanItem(
                    test_name=test.name,
                    step_index=self._step_i + 1,
                    step=test.steps[self._step_i],
                )
                self._step_i += 1
                return item

            # finished this test, move to next
            self._test_i += 1
            self._step_i = 0

        return None
