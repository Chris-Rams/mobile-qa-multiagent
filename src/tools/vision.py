from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from src.tools import adb

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def _center_from_bounds(bounds: str) -> Optional[tuple[int, int]]:
    m = _BOUNDS_RE.search(bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def _rect_from_bounds(bounds: str) -> Optional[Tuple[int, int, int, int]]:
    m = _BOUNDS_RE.search(bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return x1, y1, x2, y2


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _node_matches_target(node: ET.Element, target: str) -> bool:
    """
    Try multiple UIAutomator attributes, not just text/content-desc.
    """
    t = _norm(target)

    # common attributes
    text = _norm(node.attrib.get("text", ""))
    desc = _norm(node.attrib.get("content-desc", ""))
    resid = _norm(node.attrib.get("resource-id", ""))

    if text == t or desc == t or resid == t:
        return True

    # sometimes dumps include hint-like attributes (varies by device/version)
    for k, v in node.attrib.items():
        if "hint" in k.lower() and _norm(v) == t:
            return True

    return False


def _find_exact_matches(root: ET.Element, target: str) -> List[Tuple[int, int, str, Dict[str, str]]]:
    matches: List[Tuple[int, int, str, Dict[str, str]]] = []
    for node in root.iter():
        if _node_matches_target(node, target):
            bounds = node.attrib.get("bounds", "")
            center = _center_from_bounds(bounds)
            if center:
                x, y = center
                matches.append((x, y, bounds, dict(node.attrib)))
    return matches


def _find_edittext_below_label(root: ET.Element, label: str) -> Optional[Tuple[int, int, str, Dict[str, str]]]:
    """
    Fallback: if a label like "Vault name" exists, tap the nearest EditText below it.
    This solves the case where the input field has empty text/hint not exposed.
    """
    label_norm = _norm(label)

    label_rect = None
    label_info = None

    # Find label node by text/content-desc/resource-id
    for node in root.iter():
        text = _norm(node.attrib.get("text", ""))
        desc = _norm(node.attrib.get("content-desc", ""))
        resid = _norm(node.attrib.get("resource-id", ""))

        if text == label_norm or desc == label_norm or resid == label_norm:
            bounds = node.attrib.get("bounds", "")
            rect = _rect_from_bounds(bounds)
            if rect:
                label_rect = rect
                label_info = dict(node.attrib)
                break

    if not label_rect:
        return None

    lx1, ly1, lx2, ly2 = label_rect

    # Among EditTexts, pick one with top edge below label's bottom edge, and minimal vertical distance
    best = None
    best_dy = None

    for node in root.iter():
        if node.attrib.get("class", "") != "android.widget.EditText":
            continue
        rect = _rect_from_bounds(node.attrib.get("bounds", ""))
        if not rect:
            continue
        x1, y1, x2, y2 = rect

        if y1 >= ly2:  # below label
            dy = y1 - ly2
            if best is None or dy < best_dy:
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                best = (center[0], center[1], node.attrib.get("bounds", ""), dict(node.attrib))
                best_dy = dy

    return best


def locate_tap_point(
    screenshot_path: Path,
    target: str,
    hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Offline locator using UIAutomator XML.
    1) exact match on common attributes (text/content-desc/resource-id/hint-like)
    2) fallback: if target looks like a label, tap nearest EditText below it
    3) fallback: if hint is provided, try matching hint too
    """

    dump_device_path = "/sdcard/ui.xml"
    adb.shell(f"uiautomator dump {dump_device_path}")

    local_xml = screenshot_path.parent / (screenshot_path.stem + "_ui.xml")
    adb.pull(dump_device_path, local_xml)

    if not local_xml.exists():
        return {
            "found": False,
            "reason": "UI xml was not pulled successfully",
            "method": "uiautomator_xml",
        }

    try:
        tree = ET.parse(local_xml)
        root = tree.getroot()
    except Exception as e:
        return {
            "found": False,
            "reason": f"Failed to parse UI xml: {e}",
            "method": "uiautomator_xml",
        }

    # 1) Exact match on target
    matches = _find_exact_matches(root, target)
    if matches:
        x, y, bounds, attrs = matches[0]
        return {
            "found": True,
            "x": x,
            "y": y,
            "bounds": bounds,
            "matched_on": "exact_attribute_match",
            "matched_attrs": attrs,
            "method": "uiautomator_xml",
            "reason": f"Matched '{target}' by exact attribute",
        }

    # 2) If hint is provided, try matching hint directly
    if hint:
        hint_matches = _find_exact_matches(root, hint)
        if hint_matches:
            x, y, bounds, attrs = hint_matches[0]
            return {
                "found": True,
                "x": x,
                "y": y,
                "bounds": bounds,
                "matched_on": "hint_exact_attribute_match",
                "matched_attrs": attrs,
                "method": "uiautomator_xml",
                "reason": f"Matched hint '{hint}' by exact attribute",
            }

    # 3) Fallback: label -> nearest EditText below
    # This is the key fix for your vault name field.
    fallback = _find_edittext_below_label(root, target)
    if fallback:
        x, y, bounds, attrs = fallback
        return {
            "found": True,
            "x": x,
            "y": y,
            "bounds": bounds,
            "matched_on": "label_to_edittext_fallback",
            "matched_attrs": attrs,
            "method": "uiautomator_xml",
            "reason": f"Found EditText below label '{target}'",
        }

    return {
        "found": False,
        "reason": f"Target not found in UI xml: '{target}' (hint={hint})",
        "method": "uiautomator_xml",
    }
