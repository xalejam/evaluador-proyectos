"""Status machine for project lifecycle.

Single source of truth for which status transitions are allowed.
"""

from __future__ import annotations

# Maps each status to the list of statuses it can legally transition to.
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "evaluated": ["approved", "rejected", "on_hold"],
    "approved": ["executing", "on_hold", "rejected"],
    "in_agenda": ["executing", "on_hold", "rejected"],
    "executing": ["implemented", "on_hold"],
    "on_hold": ["executing", "rejected"],
    "implemented": ["executing"],  # reopen after delivery
    "rejected": ["approved"],  # rescue / reconsider
    "backlog": ["approved", "rejected"],
    "handed_off": [],  # terminal — no transitions out
}


def can_transition(current: str, target: str) -> bool:
    """Return True if transitioning from current to target is allowed."""
    return target in ALLOWED_TRANSITIONS.get(current.lower(), [])


def allowed_targets(current: str) -> list[str]:
    """Return list of valid target statuses from the given current status."""
    return list(ALLOWED_TRANSITIONS.get(current.lower(), []))
