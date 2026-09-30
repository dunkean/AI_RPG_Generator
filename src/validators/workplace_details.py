"""Validator for workplace details (Step 9)."""

from __future__ import annotations


def validate_workplace_details(response: dict) -> dict:
    """Merge workplace detail data into content activity groups.

    Response contains: name, new_name, description, customs, goals_keywords,
    history, relationship, timeline, anecdotes, sites, plot.
    """
    return {"_workplace_details": response}
