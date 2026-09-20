"""Interpret Advanced API sequence trees without relying on instruction names."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SequenceSummary:
    running: bool = False
    current_item: str | None = None
    total: int = 0
    finished: int = 0


def summarize_sequence(items: list[Any], parent_name: str | None = None) -> SequenceSummary:
    """Count leaf instructions and prefer an active child over its container.

    Smart Exposure's internal exposure can have Name=null. Containers also
    remain RUNNING between instructions, so their status must be considered.
    Triggers and conditions are not sequence instructions.
    """
    result = SequenceSummary()
    for item in items:
        if not isinstance(item, dict) or "GlobalTriggers" in item:
            continue
        raw_name = item.get("Name")
        name = raw_name.removesuffix("_Container").strip() if isinstance(raw_name, str) else ""
        label = name or parent_name or "Running instruction"
        active = item.get("Status") == "RUNNING"
        children = item.get("Items")
        child = summarize_sequence(children, label) if isinstance(children, list) else None
        if child is not None:
            result.total += child.total
            result.finished += child.finished
        else:
            result.total += 1
            result.finished += item.get("Status") in ("FINISHED", "SKIPPED")
        if active or (child is not None and child.running):
            result.running = True
            if result.current_item is None:
                result.current_item = child.current_item if child is not None and child.running else label
    return result
