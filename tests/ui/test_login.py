import bcrypt
import pytest


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
