"""Helpers for desktop startup flow decisions."""

from __future__ import annotations


def should_start_llama_on_startup(settings: dict) -> bool:
    """Return True when regular startup should own llama-server boot."""
    return bool(settings.get("first_run_completed"))
