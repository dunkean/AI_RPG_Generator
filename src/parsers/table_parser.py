"""Markdown table parser for LLM responses."""

from __future__ import annotations

from .json_parser import parse_json, ParseError


class TableParseError(Exception):
    """Raised when markdown table parsing fails."""


def parse_table(raw_data: str) -> list[dict]:
    """Parse a markdown table into a list of dicts.

    Handles:
    - Leading/trailing pipes
    - Separator rows (``---``)
    - Inline JSON/list values (delegates to ``parse_json``)
    - Numeric type coercion
    """
    lines = [line.strip() for line in raw_data.split("\n")]
    lines = [line for line in lines if line and "|" in line]

    if len(lines) < 3:
        raise TableParseError(
            f"Table needs at least 3 rows (header + separator + data), got {len(lines)}"
        )

    # Extract headers
    headers = [h.strip() for h in lines[0].split("|")]
    headers = [h for h in headers if h]  # remove empty from leading/trailing |

    # Skip separator row (line 1), parse data rows (lines 2+)
    rows: list[dict] = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells[0] == "" else cells  # strip leading/trailing empties

        if len(cells) < len(headers):
            # Incomplete row — skip
            continue

        item: dict = {}
        for j, header in enumerate(headers):
            val: str | int | float | dict | list = cells[j] if j < len(cells) else ""

            if isinstance(val, str) and val and val[0] in ("{", "["):
                try:
                    val = parse_json(val) if val[0] == "{" else _parse_list(val)
                except (ParseError, Exception):
                    pass  # keep as string
            else:
                val = _coerce_number(val)

            item[header.lower()] = val
        rows.append(item)

    return rows


def _coerce_number(val: str) -> str | int | float:
    """Try to convert a string to int or float."""
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return val


def _parse_list(val: str) -> list:
    """Parse a bracketed list, handling both JSON and Python-style."""
    import ast
    import json

    try:
        return json.loads(val)
    except json.JSONDecodeError:
        pass
    try:
        result = ast.literal_eval(val)
        if isinstance(result, list):
            return result
    except Exception:
        pass
    # Fallback: split by comma
    inner = val.strip("[]")
    return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
