"""Tests para _resolve_default_author en seguimiento_operativo."""


def test_resolve_finds_exact_match():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Carlos Montiel", "Xiomara Monroy"]
    assert _resolve_default_author("Carlos Montiel", members) == "Carlos Montiel"


def test_resolve_is_case_insensitive():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Xiomara Monroy"]
    assert _resolve_default_author("xiomara monroy", members) == "Xiomara Monroy"


def test_resolve_preserves_db_casing():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    # El miembro en BD tiene capitalización propia — se usa la de la BD
    members = ["CARLOS MONTIEL"]
    assert _resolve_default_author("carlos montiel", members) == "CARLOS MONTIEL"


def test_resolve_returns_candidate_when_not_in_members():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Carlos Montiel"]
    assert _resolve_default_author("Nuevo Usuario", members) == "Nuevo Usuario"


def test_resolve_returns_fallback_when_candidate_is_empty():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Carlos Montiel"]
    assert _resolve_default_author("", members) == "Xiomara Monroy"


def test_resolve_returns_fallback_when_candidate_is_whitespace():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Carlos Montiel"]
    assert _resolve_default_author("   ", members) == "Xiomara Monroy"


def test_resolve_custom_fallback():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    assert _resolve_default_author("", [], fallback="Admin") == "Admin"
