from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any

from src.tools import adb


_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def _center_from_bounds(bounds: str) -> Optional[tuple[int, int]]:
    m = _BOUNDS_RE.search(bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def locate_tap_point(
    screenshot_path: Path,
    target: str,
    hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Offline UI locator.

    Uses UIAutomator XML (adb shell uiautomator dump) to find a node whose:
    - text == target, or
    - content-desc == target

    Returns a dict compatible with your orchestrator:
      { found: bool, x: int, y: int, method: str, reason: str }
    """

    # 1) Dump current UI hierarchy to device
    dump_device_path = "/sdcard/ui.xml"
    adb.shell(f"uiautomator dump {dump_device_path}")

    # 2) Pull the XML to local artifacts folder near screenshot
    local_xml = screenshot_path.parent / (screenshot_path.stem + "_ui.xml")
    adb.pull(dump_device_path, str(local_xml))

    if not local_xml.exists():
        return {
            "found": False,
            "reason": "UI xml was not pulled successfully",
            "method": "uiautomator_xml",
        }

    # 3) Parse XML and search nodes
    try:
        tree = ET.parse(local_xml)
        root = tree.getroot()
    except Exception as e:
        return {
            "found": False,
            "reason": f"Failed to parse UI xml: {e}",
            "method": "uiautomator_xml",
        }

    # Common UIAutomator node attributes:
    # text, content-desc, resource-id, class, bounds
    candidates = []
    for node in root.iter():
        text = node.attrib.get("text", "") or ""
        desc = node.attrib.get("content-desc", "") or ""
        bounds = node.attrib.get("bounds", "") or ""

        if text.strip() == target.strip() or desc.strip() == target.strip():
            center = _center_from_bounds(bounds)
            if center:
                candidates.append((center, bounds, text, desc))

    if not candidates:
        return {
            "found": False,
            "reason": f"Target not found in UI xml: '{target}'",
            "method": "uiautomator_xml",
        }

    # If multiple matches exist, pick the first (can be improved later)
    (x, y), bounds, text, desc = candidates[0]
    return {
        "found": True,
        "x": x,
        "y": y,
        "bounds": bounds,
        "matched_text": text,
        "matched_desc": desc,
        "method": "uiautomator_xml",
        "reason": "Matched by exact text/content-desc",
    }
