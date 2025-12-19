from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class Step:
    type: str
    description: str
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    app: Optional[str] = None
    # File path (for screenshot)
    path: Optional[str] = None
    sleep_seconds: Optional[float] = None
    # Vision based tapping
    target: Optional[str] = None          # primary UI target text/id
    alt_target: Optional[str] = None      # fallback target text ("Create new vault")
    hint: Optional[str] = None            # extra hint for locator if needed
    keycode: Optional[int] = None


@dataclass
class TestCase:
    name: str
    steps: List[Step]


@dataclass
class TestSuite:
    name: str
    description: str
    tests: List[TestCase]


def _req(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        raise ValueError(f"Missing required key '{key}' in: {d}")
    return d[key]


def parse_suite(data: Dict[str, Any]) -> TestSuite:
    suite_meta = _req(data, "test_suite")
    tests_data = _req(data, "tests")

    suite_name = _req(suite_meta, "name")
    suite_desc = _req(suite_meta, "description")

    tests: List[TestCase] = []
    for t in tests_data:
        tname = _req(t, "name")
        steps_list = _req(t, "steps")
        steps: List[Step] = []
        for s in steps_list:
            stype = _req(s, "type")
            sdesc = _req(s, "description")

            steps.append(
                Step(
                    type=stype,
                    description=sdesc,
                    x=s.get("x"),
                    y=s.get("y"),
                    text=s.get("text"),
                    app=s.get("app"),
                    path=s.get("path"),
                    sleep_seconds=s.get("sleep_seconds"),
                    target=s.get("target"),
                    alt_target=s.get("alt_target"),
                    hint=s.get("hint"),
                    keycode=s.get("keycode"),
                )
            )
        tests.append(TestCase(name=tname, steps=steps))

    return TestSuite(name=suite_name, description=suite_desc, tests=tests)
