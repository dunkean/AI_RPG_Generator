"""JSON parser with comment stripping and fallback."""

from __future__ import annotations

import ast
import json
import re


class ParseError(Exception):
    """Raised when JSON parsing fails after all fallbacks."""


def strip_json_comments(json_text: str) -> str:
    """Remove ``//`` and ``/* */`` comments from JSON-like text."""
    pattern = r"""("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(/\*.*?\*/|//[^\r\n]*$)"""
    return re.sub(
        pattern,
        lambda m: m.group(1) if m.group(1) else "",
        json_text,
        flags=re.MULTILINE | re.DOTALL,
    )


def parse_json(raw_data: str) -> dict:
    """Extract and parse a JSON object from raw LLM output.

    1. Strip comments.
    2. Find the outermost ``{...}`` block.
    3. Try ``json.loads``, fallback to ``ast.literal_eval``.

    Raises ``ParseError`` on failure (never returns ``None``).
    """
    cleaned = strip_json_comments(raw_data)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ParseError(f"No JSON object found in response (len={len(raw_data)})")

    json_str = cleaned[start : end + 1]

    # Attempt 1: standard JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Attempt 2: fix stray escaped quotes (LLMs sometimes produce \"value\"
    # instead of "value" outside of strings)
    try:
        fixed = json_str.replace('\\"', '"')
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Attempt 3: Python literal eval (handles single-quotes, trailing commas)
    try:
        obj = ast.literal_eval(json_str)
        # Round-trip to ensure JSON-compatible types
        return json.loads(json.dumps(obj))
    except Exception as exc:
        raise ParseError(f"Failed to parse JSON: {exc}") from exc
