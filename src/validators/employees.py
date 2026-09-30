"""Validator for employee details (Step 8)."""

from __future__ import annotations


def validate_employee_details(response: dict) -> dict:
    """Merge employee enrichment data into npcs dict, keyed by name.

    Response has {"employees": [{"name": ..., "job": ..., ...}]}
    Returns a patch like {"npcs": {"Full Name": {enriched data}, ...}}
    so that dict-based merging works across workplaces.
    """
    employees = response.get("employees", [])
    if not employees and isinstance(response, list):
        employees = response

    patch: dict = {"npcs": {}}
    for emp in employees:
        name = emp.get("name", "")
        if name:
            patch["npcs"][name] = emp
    return patch
