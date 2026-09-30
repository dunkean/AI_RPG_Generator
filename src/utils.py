"""Shared utilities: deep merge helpers."""

from __future__ import annotations


def update_dict(original: dict, update: dict) -> dict:
    """Recursively deep-merge *update* into *original* (mutates original)."""
    for key, value in update.items():
        if key not in original:
            original[key] = value
            continue

        if isinstance(value, dict) and isinstance(original[key], dict):
            update_dict(original[key], value)
        elif isinstance(value, list) and isinstance(original[key], list):
            update_list(original[key], value)
        else:
            original[key] = value
    return original


def update_list(original: list, update: list) -> list:
    """Merge two lists element-wise (mutates original).

    If the lists differ in length the update list wins outright — this
    handles cases where an LLM step returns a different number of items
    than the existing content.
    """
    if len(original) != len(update):
        original.clear()
        original.extend(update)
        return original

    for idx, (val_original, val_update) in enumerate(zip(original, update)):
        if isinstance(val_original, dict) and isinstance(val_update, dict):
            original[idx] = update_dict(original[idx], update[idx])
        elif isinstance(val_original, (tuple, list)) and isinstance(val_update, (tuple, list)):
            original[idx] = update_list(list(original[idx]), list(update[idx]))
        else:
            original[idx] = val_update
    return original
