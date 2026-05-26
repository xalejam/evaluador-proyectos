import bcrypt


def _make_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def test_verify_password_correct():
    from ui.login import verify_password

    h = _make_hash("mi_contraseña_123")
    assert verify_password("mi_contraseña_123", h) is True


def test_verify_password_incorrect():
    from ui.login import verify_password

    h = _make_hash("correcta")
    assert verify_password("incorrecta", h) is False


def test_verify_password_empty():
    from ui.login import verify_password

    h = _make_hash("algo")
    assert verify_password("", h) is False


def test_derive_display_name_dot_separated():
    from ui.login import _derive_display_name

    assert _derive_display_name("carlos.montiel@wp.numerator.com") == "Carlos Montiel"


def test_derive_display_name_xiomara():
    from ui.login import _derive_display_name

    assert _derive_display_name("xiomara.monroy@wp.numerator.com") == "Xiomara Monroy"


def test_derive_display_name_single_word():
    from ui.login import _derive_display_name

    assert _derive_display_name("admin@example.com") == "Admin"


def test_derive_display_name_underscore_separator():
    from ui.login import _derive_display_name

    assert _derive_display_name("juan_perez@example.com") == "Juan Perez"


def test_derive_display_name_mixed_separators():
    from ui.login import _derive_display_name

    assert _derive_display_name("ana.garcia_lopez@example.com") == "Ana Garcia Lopez"
