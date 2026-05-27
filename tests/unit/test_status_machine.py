from infra.status_machine import ALLOWED_TRANSITIONS, allowed_targets, can_transition


def test_approved_to_executing_allowed():
    assert can_transition("approved", "executing") is True


def test_in_agenda_to_executing_allowed():
    assert can_transition("in_agenda", "executing") is True


def test_executing_to_implemented_allowed():
    assert can_transition("executing", "implemented") is True


def test_implemented_to_executing_allowed_reopen():
    """Implemented projects must be re-openable."""
    assert can_transition("implemented", "executing") is True


def test_executing_to_approved_not_allowed():
    assert can_transition("executing", "approved") is False


def test_implemented_to_approved_not_allowed():
    assert can_transition("implemented", "approved") is False


def test_handed_off_has_no_targets():
    assert can_transition("handed_off", "executing") is False
    assert allowed_targets("handed_off") == []


def test_unknown_status_returns_false():
    assert can_transition("nonexistent", "executing") is False


def test_case_insensitive_current():
    assert can_transition("APPROVED", "executing") is True
    assert can_transition("Executing", "implemented") is True


def test_allowed_targets_executing_contains_expected():
    targets = allowed_targets("executing")
    assert "implemented" in targets
    assert "on_hold" in targets
    assert "approved" not in targets


def test_all_transition_targets_are_known_statuses():
    """Every transition target must itself be a key in ALLOWED_TRANSITIONS."""
    known = set(ALLOWED_TRANSITIONS.keys())
    for src, targets in ALLOWED_TRANSITIONS.items():
        for tgt in targets:
            assert tgt in known, f"Transition {src!r} → {tgt!r}: target {tgt!r} is not a key in ALLOWED_TRANSITIONS"
