from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI


LOCATE_PROMPT = """
You are a mobile UI locator.

You will be given:
1) A screenshot of an Android app
2) A target element description (what the user wants to click)
3) Optional hint text (extra context)

Your job:
Return the BEST tap point (x, y) in screen pixel coordinates for the target element.

Rules:
- Output ONLY valid JSON. No extra text.
- If you cannot find the target, output {"found": false, "reason": "..."}.
- If you can find it, output:
  {
    "found": true,
    "x": <int>,
    "y": <int>,
    "confidence": 0.0-1.0,
    "reason": "<short>"
  }
"""


def _b64_image(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def locate_tap_point(
    screenshot_path: str | Path,
    target: str,
    hint: Optional[str] = None,
    model: str = "gpt-4.1-mini",
) -> Dict[str, Any]:
    """
    Returns dict like:
    - found True: {"found": True, "x": int, "y": int, "confidence": float, "reason": str}
    - found False: {"found": False, "reason": str}
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in your environment.")

    client = OpenAI(api_key=api_key)

    screenshot_path = Path(screenshot_path)
    if not screenshot_path.exists():
        raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

    b64 = _b64_image(screenshot_path)

    user_text = f"TARGET: {target}\n"
    if hint:
        user_text += f"HINT: {hint}\n"

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": LOCATE_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            },
        ],
        temperature=0,
    )

    content = resp.choices[0].message.content or ""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise RuntimeError(f"Model did not return valid JSON.\nReturned:\n{content}")

    return data
