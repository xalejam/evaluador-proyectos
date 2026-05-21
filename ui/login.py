"""Pantalla de login y lógica de autenticación."""
from __future__ import annotations
import bcrypt
import streamlit as st
from infra.db.connection import get_sqlite_conn, DB_PATH
from infra.db.adapter import PLACEHOLDER


def verify_password(plain: str, hashed: str) -> bool:
    if not plain:
        return False
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _get_user(email: str) -> dict | None:
    with get_sqlite_conn(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT email, password_hash, is_active FROM users WHERE email = {PLACEHOLDER}",
            (email.lower().strip(),),
        ).fetchone()
    if row is None:
        return None
    return {"email": row[0], "password_hash": row[1], "is_active": row[2]}


def render_login() -> bool:
    """Renderiza el formulario de login. Devuelve True si la sesión está activa."""
    if st.session_state.get("authenticated"):
        return True

    st.title("Evaluador de Proyectos")
    st.subheader("Iniciar sesión")

    with st.form("login_form"):
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")

    if submitted:
        user = _get_user(email)
        if user and user["is_active"] and verify_password(password, user["password_hash"]):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = user["email"]
            st.rerun()
        else:
            st.error("Correo o contraseña incorrectos.")

    return False
