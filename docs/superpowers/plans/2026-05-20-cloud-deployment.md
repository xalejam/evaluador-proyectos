# Cloud Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Desplegar el Evaluador de Proyectos en Streamlit Community Cloud con Supabase PostgreSQL y autenticación propia para que 5 miembros del equipo accedan desde cualquier navegador.

**Architecture:** La app Streamlit sigue igual; se reemplaza el driver de conexión local SQLite por psycopg2/PostgreSQL en producción usando la variable de entorno `DATABASE_URL` como switch. Se agrega una pantalla de login con bcrypt antes de mostrar la app.

**Tech Stack:** Streamlit Community Cloud, Supabase PostgreSQL, psycopg2-binary, bcrypt, SQLAlchemy, GitHub (mirror de Azure DevOps).

---

## File Map

| Acción | Archivo |
|---|---|
| Crear | `infra/db/adapter.py` — wrapper de conexión que normaliza sqlite3 vs psycopg2 |
| Modificar | `infra/db/connection.py` — detectar DATABASE_URL y devolver adaptador correcto |
| Modificar | `infra/db/sqlalchemy_store.py` — leer DATABASE_URL para motor PostgreSQL |
| Modificar | `infra/db_migrations.py` — usar adaptador en lugar de sqlite3 crudo |
| Crear | `ui/login.py` — formulario de login Streamlit |
| Crear | `scripts/create_user.py` — admin: registrar/desactivar usuarios |
| Modificar | `main.py` — guardia de sesión antes de renderizar la app |
| Modificar | `requirements.txt` — añadir psycopg2-binary y bcrypt |
| Modificar | `azure-pipelines.yml` — añadir step de mirror a GitHub |
| Crear | `.streamlit/secrets.toml.example` — plantilla de secrets (no se commitea el real) |
| Modificar | `.gitignore` — excluir `.streamlit/secrets.toml` |

---

## Fase 1: Infraestructura manual (sin código)

### Task 1: Crear cuentas y servicios externos

> Estos pasos son manuales. No hay código que escribir ni tests que correr.

- [ ] **Paso 1: Crear cuenta en GitHub**

  Ir a https://github.com/signup con tu email personal (o usar cuenta existente).
  Crear un repositorio **privado** llamado `evaluador-proyectos`.
  No añadir README ni .gitignore — el repo debe quedar vacío.

- [ ] **Paso 2: Crear Personal Access Token en GitHub**

  GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token.
  Permisos necesarios: `repo` (todos los sub-permisos).
  Copiar el token generado — solo se muestra una vez. Guardarlo en lugar seguro.

- [ ] **Paso 3: Crear proyecto en Supabase**

  Ir a https://supabase.com → Sign up → New project.
  - Name: `evaluador-proyectos`
  - Region: el más cercano (ej. `us-east-1`)
  - Password: generar uno fuerte y guardarlo.

  Una vez creado, ir a: Project Settings → Database → Connection string → URI.
  Copiar la URI completa (empieza con `postgresql://`). Se usará en Task 2 y Task 9.

- [ ] **Paso 4: Crear cuenta en Streamlit Community Cloud**

  Ir a https://share.streamlit.io → Sign up con tu cuenta de GitHub.
  No crear una app todavía — eso se hace en la Fase 5.

---

### Task 2: Crear schema en Supabase

- [ ] **Paso 1: Abrir SQL Editor en Supabase**

  En el panel de Supabase: SQL Editor → New query.

- [ ] **Paso 2: Ejecutar DDL de tablas operacionales**

  Copiar y ejecutar este SQL completo:

  ```sql
  -- Tabla principal de proyectos (de project_viability.db)
  CREATE TABLE IF NOT EXISTS projects (
      id TEXT PRIMARY KEY,
      project_id TEXT,
      name TEXT,
      description TEXT,
      created_date TEXT,
      status TEXT,
      last_tracking_update TEXT,
      country TEXT,
      owner TEXT,
      current_time_per_task DOUBLE PRECISION,
      tasks_per_month INTEGER,
      staff_count INTEGER,
      avg_salary_per_hour DOUBLE PRECISION,
      time_reduction_percent DOUBLE PRECISION,
      development_hours DOUBLE PRECISION,
      development_cost_per_hour DOUBLE PRECISION,
      maintenance_monthly DOUBLE PRECISION,
      implementation_complexity TEXT,
      risk_level TEXT,
      viability_score DOUBLE PRECISION,
      priority TEXT,
      recommendation TEXT,
      monthly_savings DOUBLE PRECISION,
      annual_savings DOUBLE PRECISION,
      payback_period_months DOUBLE PRECISION,
      roi_first_year DOUBLE PRECISION,
      initial_development_cost DOUBLE PRECISION,
      hours_saved_per_month DOUBLE PRECISION,
      actual_monthly_savings DOUBLE PRECISION,
      actual_annual_savings DOUBLE PRECISION
  );

  -- Tracking de proyectos
  CREATE TABLE IF NOT EXISTS tracking (
      id SERIAL PRIMARY KEY,
      project_id TEXT,
      tracking_date TEXT,
      months_tracked INTEGER,
      actual_time_per_task DOUBLE PRECISION,
      actual_tasks_per_month INTEGER,
      adoption_rate DOUBLE PRECISION,
      user_satisfaction_score DOUBLE PRECISION,
      unexpected_benefits TEXT,
      challenges_faced TEXT,
      lessons_learned TEXT,
      performance_score DOUBLE PRECISION,
      efficiency_ratio DOUBLE PRECISION,
      actual_time_reduction_percent DOUBLE PRECISION,
      actual_monthly_savings DOUBLE PRECISION,
      actual_annual_savings DOUBLE PRECISION
  );

  -- Notas de proyectos
  CREATE TABLE IF NOT EXISTS project_notes (
      note_id SERIAL PRIMARY KEY,
      project_id TEXT,
      note_type TEXT,
      note_text TEXT,
      author TEXT,
      effort_hours DOUBLE PRECISION,
      created_at TEXT
  );

  -- Miembros de proyectos
  CREATE TABLE IF NOT EXISTS project_members (
      id SERIAL PRIMARY KEY,
      project_id TEXT,
      member_name TEXT,
      added_at TEXT
  );

  -- Horas de esfuerzo
  CREATE TABLE IF NOT EXISTS effort_hours (
      id SERIAL PRIMARY KEY,
      project_id TEXT,
      author TEXT,
      hours DOUBLE PRECISION,
      week_start TEXT,
      created_at TEXT
  );

  -- Tabla Use Case Matrix (de data/projects.db)
  CREATE TABLE IF NOT EXISTS ucm_projects (
      project_id TEXT PRIMARY KEY,
      country TEXT NOT NULL,
      owner TEXT NOT NULL,
      name TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
  );

  CREATE TABLE IF NOT EXISTS ucm_evaluations (
      eval_id SERIAL PRIMARY KEY,
      project_id TEXT NOT NULL REFERENCES ucm_projects(project_id),
      answers_json JSONB NOT NULL,
      weights_json JSONB NOT NULL,
      impact_score DOUBLE PRECISION NOT NULL,
      effort_score DOUBLE PRECISION NOT NULL,
      is_current BOOLEAN DEFAULT TRUE NOT NULL,
      created_at TIMESTAMP DEFAULT NOW()
  );

  -- Usuarios del sistema
  CREATE TABLE IF NOT EXISTS users (
      email TEXT PRIMARY KEY,
      password_hash TEXT NOT NULL,
      is_active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMP DEFAULT NOW()
  );
  ```

- [ ] **Paso 3: Verificar que las tablas se crearon**

  En el panel de Supabase: Table Editor → verificar que aparecen todas las tablas listadas.

---

## Fase 2: Capa de conexión PostgreSQL

### Task 3: Añadir dependencias

**Files:**
- Modify: `requirements.txt`

- [ ] **Paso 1: Añadir psycopg2-binary y bcrypt a requirements.txt**

  Abrir `requirements.txt` y añadir al final:

  ```
  psycopg2-binary
  bcrypt
  ```

- [ ] **Paso 2: Instalar en entorno local**

  ```bash
  pip install psycopg2-binary bcrypt
  ```

  Expected: instalación sin errores.

- [ ] **Paso 3: Verificar importación**

  ```bash
  python -c "import psycopg2; import bcrypt; print('OK')"
  ```

  Expected: `OK`

- [ ] **Paso 4: Commit**

  ```bash
  git add requirements.txt
  git commit -m "deps: add psycopg2-binary and bcrypt for cloud deployment"
  ```

---

### Task 4: Crear adaptador de conexión

**Files:**
- Create: `infra/db/adapter.py`
- Create: `tests/infra/test_db_adapter.py`

- [ ] **Paso 1: Escribir test que verifica que el adaptador detecta el modo**

  Crear `tests/infra/test_db_adapter.py`:

  ```python
  import os
  import pytest

  def test_adapter_local_mode_uses_sqlite(monkeypatch, tmp_path):
      monkeypatch.delenv("DATABASE_URL", raising=False)
      db_file = tmp_path / "test.db"
      from infra.db.adapter import get_connection
      conn = get_connection(local_path=str(db_file))
      conn.execute("CREATE TABLE t (x INTEGER)")
      conn.execute("INSERT INTO t VALUES (1)")
      conn.commit()
      row = conn.execute("SELECT x FROM t").fetchone()
      assert row[0] == 1
      conn.close()

  def test_adapter_placeholder_local():
      import os
      os.environ.pop("DATABASE_URL", None)
      from importlib import reload
      import infra.db.adapter as mod
      reload(mod)
      assert mod.PLACEHOLDER == "?"
  ```

- [ ] **Paso 2: Correr el test y verificar que falla**

  ```bash
  pytest tests/infra/test_db_adapter.py -v
  ```

  Expected: `ImportError` o `ModuleNotFoundError` (el módulo no existe aún).

- [ ] **Paso 3: Crear `infra/db/adapter.py`**

  ```python
  """Adaptador de conexión que unifica sqlite3 y psycopg2."""
  from __future__ import annotations
  import os
  import sqlite3
  from typing import Any

  _DATABASE_URL = os.environ.get("DATABASE_URL", "")
  IS_CLOUD = bool(_DATABASE_URL)
  PLACEHOLDER = "%s" if IS_CLOUD else "?"


  class _Psycopg2Adapter:
      """Envuelve una conexión psycopg2 con la misma interfaz que sqlite3."""

      def __init__(self, url: str) -> None:
          import psycopg2
          import psycopg2.extras
          self._conn = psycopg2.connect(url)
          psycopg2.extras.register_default_jsonb(self._conn)

      def execute(self, sql: str, params: tuple = ()) -> Any:
          cur = self._conn.cursor()
          cur.execute(sql, params)
          return cur

      def commit(self) -> None:
          self._conn.commit()

      def close(self) -> None:
          self._conn.close()

      def __enter__(self):
          return self

      def __exit__(self, *args):
          self.close()


  class _Sqlite3Adapter:
      """Envuelve sqlite3.Connection con la misma interfaz."""

      def __init__(self, path: str) -> None:
          self._conn = sqlite3.connect(path)
          self._conn.row_factory = sqlite3.Row

      def execute(self, sql: str, params: tuple = ()) -> Any:
          return self._conn.execute(sql, params)

      def commit(self) -> None:
          self._conn.commit()

      def close(self) -> None:
          self._conn.close()

      def __enter__(self):
          return self

      def __exit__(self, *args):
          self.close()


  def get_connection(local_path: str = "project_viability.db") -> _Sqlite3Adapter | _Psycopg2Adapter:
      if IS_CLOUD:
          return _Psycopg2Adapter(_DATABASE_URL)
      return _Sqlite3Adapter(local_path)
  ```

- [ ] **Paso 4: Correr tests y verificar que pasan**

  ```bash
  pytest tests/infra/test_db_adapter.py -v
  ```

  Expected: 2 tests en PASS.

- [ ] **Paso 5: Commit**

  ```bash
  git add infra/db/adapter.py tests/infra/test_db_adapter.py
  git commit -m "feat: add DB adapter for sqlite3/psycopg2 compatibility"
  ```

---

### Task 5: Actualizar connection.py para usar el adaptador

**Files:**
- Modify: `infra/db/connection.py`

- [ ] **Paso 1: Reemplazar contenido de `infra/db/connection.py`**

  ```python
  """Conexión principal de base de datos — sqlite3 local o PostgreSQL en nube."""
  from __future__ import annotations
  from pathlib import Path
  from infra.db.adapter import get_connection, PLACEHOLDER, IS_CLOUD

  ROOT = Path(__file__).resolve().parents[2]
  DB_PATH = ROOT / "project_viability.db"


  def get_sqlite_conn(db_path: Path | str = DB_PATH):
      """Devuelve adaptador de conexión (sqlite3 local o psycopg2 en nube)."""
      return get_connection(local_path=str(db_path))
  ```

- [ ] **Paso 2: Verificar que la app sigue arrancando**

  ```bash
  python -c "from infra.db.connection import get_sqlite_conn, DB_PATH; c = get_sqlite_conn(); print('OK')"
  ```

  Expected: `OK`

- [ ] **Paso 3: Commit**

  ```bash
  git add infra/db/connection.py
  git commit -m "refactor: connection.py uses adapter for sqlite3/psycopg2 dual support"
  ```

---

### Task 6: Actualizar sqlalchemy_store.py para PostgreSQL

**Files:**
- Modify: `infra/db/sqlalchemy_store.py`

- [ ] **Paso 1: Reemplazar la sección de DATABASE_URL y engine en `infra/db/sqlalchemy_store.py`**

  Reemplazar las líneas 1-12 (imports + DATABASE_URL + engine) con:

  ```python
  """Infraestructura de base de datos con SQLAlchemy — soporta SQLite y PostgreSQL."""
  import os
  from pathlib import Path

  from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, create_engine
  from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
  from sqlalchemy.sql import func

  _DATABASE_URL = os.environ.get("DATABASE_URL", "")

  if _DATABASE_URL:
      DATABASE_URL = _DATABASE_URL
      _engine_kwargs: dict = {}
  else:
      DATA_DIR = Path("data")
      DB_PATH = DATA_DIR / "projects.db"
      DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
      _engine_kwargs = {"connect_args": {"check_same_thread": False}}
  ```

  Y reemplazar las líneas del `engine` y `SessionLocal` al final del archivo con:

  ```python
  engine = create_engine(DATABASE_URL, future=True, **_engine_kwargs)
  SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


  def init_db() -> None:
      """Crea estructura de base de datos si no existe (solo en modo local)."""
      if not _DATABASE_URL:
          DATA_DIR.mkdir(parents=True, exist_ok=True)
      Base.metadata.create_all(bind=engine)
  ```

  > Nota: las tablas ORM (`ProjectORM`, `EvaluationORM`) apuntan a `projects` y `evaluations`. En Supabase estas se renombraron a `ucm_projects` y `ucm_evaluations` para evitar colisión. Actualizar `__tablename__` en ambos modelos:

  ```python
  class ProjectORM(Base):
      __tablename__ = "ucm_projects"
      # ... resto sin cambios

  class EvaluationORM(Base):
      __tablename__ = "ucm_evaluations"
      # ... resto sin cambios
  ```

- [ ] **Paso 2: Correr tests existentes para verificar que no se rompe nada**

  ```bash
  pytest tests/ -q
  ```

  Expected: todos los tests existentes en PASS.

- [ ] **Paso 3: Commit**

  ```bash
  git add infra/db/sqlalchemy_store.py
  git commit -m "feat: sqlalchemy_store supports PostgreSQL via DATABASE_URL env var"
  ```

---

### Task 7: Actualizar db_migrations.py para usar el adaptador

**Files:**
- Modify: `infra/db_migrations.py`

- [ ] **Paso 1: Reemplazar las funciones de inspección de esquema en `infra/db_migrations.py`**

  Las funciones `_table_exists` y `_table_columns` usan `sqlite_master` y `PRAGMA` que son SQLite-específicos. Reemplazar esas dos funciones (y `get_conn`) con:

  ```python
  from infra.db.adapter import get_connection, IS_CLOUD, PLACEHOLDER

  def get_conn(db_path: str = DB_PATH):
      return get_connection(local_path=db_path)


  def _table_exists(conn, table_name: str) -> bool:
      if IS_CLOUD:
          row = conn.execute(
              "SELECT table_name FROM information_schema.tables "
              "WHERE table_schema='public' AND table_name=%s LIMIT 1",
              (table_name,),
          ).fetchone()
      else:
          row = conn.execute(
              "SELECT name FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
              (table_name,),
          ).fetchone()
      return row is not None


  def _table_columns(conn, table_name: str) -> set[str]:
      if not _table_exists(conn, table_name):
          return set()
      if IS_CLOUD:
          rows = conn.execute(
              "SELECT column_name FROM information_schema.columns "
              "WHERE table_schema='public' AND table_name=%s",
              (table_name,),
          ).fetchall()
          return {r[0] for r in rows}
      else:
          rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
          return {row[1] for row in rows}
  ```

  Eliminar el import de `sqlite3` al inicio del archivo ya que ya no se usa directamente.

- [ ] **Paso 2: Reemplazar todos los `?` restantes en db_migrations.py por `PLACEHOLDER`**

  Buscar en el archivo todos los `?` dentro de llamadas `.execute(...)` y reemplazarlos con el valor de `PLACEHOLDER`. Como `PLACEHOLDER` es una variable en tiempo de ejecución y los strings SQL son literales, el patrón correcto es usar f-string:

  ```python
  # Antes:
  conn.execute("SELECT ... WHERE name = ?", (value,))
  # Después:
  conn.execute(f"SELECT ... WHERE name = {PLACEHOLDER}", (value,))
  ```

  Aplicar este patrón a todas las ocurrencias en `db_migrations.py`.

- [ ] **Paso 3: Correr tests**

  ```bash
  pytest tests/ -q
  ```

  Expected: todos en PASS.

- [ ] **Paso 4: Commit**

  ```bash
  git add infra/db_migrations.py
  git commit -m "feat: db_migrations supports both SQLite and PostgreSQL dialects"
  ```

---

## Fase 3: Autenticación

### Task 8: Crear pantalla de login

**Files:**
- Create: `ui/login.py`
- Create: `tests/ui/test_login.py`

- [ ] **Paso 1: Escribir tests para la lógica de verificación de contraseña**

  Crear `tests/ui/test_login.py`:

  ```python
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
  ```

- [ ] **Paso 2: Correr tests y verificar que fallan**

  ```bash
  pytest tests/ui/test_login.py -v
  ```

  Expected: `ImportError` (módulo no existe aún).

- [ ] **Paso 3: Crear `ui/login.py`**

  ```python
  """Pantalla de login y lógica de autenticación."""
  from __future__ import annotations
  import bcrypt
  import streamlit as st
  from infra.db.connection import get_sqlite_conn, DB_PATH


  def verify_password(plain: str, hashed: str) -> bool:
      if not plain:
          return False
      return bcrypt.checkpw(plain.encode(), hashed.encode())


  def _get_user(email: str) -> dict | None:
      with get_sqlite_conn(DB_PATH) as conn:
          row = conn.execute(
              "SELECT email, password_hash, is_active FROM users WHERE email = ?",
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
  ```

  > Nota: `_get_user` usa `?` hardcodeado porque localmente siempre es SQLite. Si en la nube se necesita psycopg2, la función usará `%s`. Actualizar usando `PLACEHOLDER`:

  ```python
  from infra.db.adapter import PLACEHOLDER

  def _get_user(email: str) -> dict | None:
      with get_sqlite_conn(DB_PATH) as conn:
          row = conn.execute(
              f"SELECT email, password_hash, is_active FROM users WHERE email = {PLACEHOLDER}",
              (email.lower().strip(),),
          ).fetchone()
      ...
  ```

- [ ] **Paso 4: Correr tests y verificar que pasan**

  ```bash
  pytest tests/ui/test_login.py -v
  ```

  Expected: 3 tests en PASS.

- [ ] **Paso 5: Commit**

  ```bash
  git add ui/login.py tests/ui/test_login.py
  git commit -m "feat: add login screen with bcrypt authentication"
  ```

---

### Task 9: Crear script de administración de usuarios

**Files:**
- Create: `scripts/create_user.py`

- [ ] **Paso 1: Crear `scripts/create_user.py`**

  ```python
  #!/usr/bin/env python3
  """
  Administración de usuarios del Evaluador de Proyectos.

  Uso:
      python scripts/create_user.py --email ana@kantar.com --password temporal123
      python scripts/create_user.py --email ana@kantar.com --deactivate
      python scripts/create_user.py --list
  """

  import argparse
  import sys
  from pathlib import Path

  ROOT = Path(__file__).resolve().parent.parent
  sys.path.insert(0, str(ROOT))

  import bcrypt
  from infra.db.connection import get_sqlite_conn, DB_PATH
  from infra.db.adapter import PLACEHOLDER


  def _ensure_users_table(conn) -> None:
      conn.execute(
          """
          CREATE TABLE IF NOT EXISTS users (
              email TEXT PRIMARY KEY,
              password_hash TEXT NOT NULL,
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT DEFAULT (datetime('now'))
          )
          """
      )
      conn.commit()


  def create_user(email: str, password: str) -> None:
      hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
      with get_sqlite_conn(DB_PATH) as conn:
          _ensure_users_table(conn)
          conn.execute(
              f"INSERT INTO users (email, password_hash) VALUES ({PLACEHOLDER}, {PLACEHOLDER}) "
              f"ON CONFLICT(email) DO UPDATE SET password_hash={PLACEHOLDER}, is_active=1",
              (email.lower(), hashed, hashed),
          )
          conn.commit()
      print(f"Usuario creado/actualizado: {email}")


  def deactivate_user(email: str) -> None:
      with get_sqlite_conn(DB_PATH) as conn:
          _ensure_users_table(conn)
          conn.execute(
              f"UPDATE users SET is_active=0 WHERE email={PLACEHOLDER}",
              (email.lower(),),
          )
          conn.commit()
      print(f"Usuario desactivado: {email}")


  def list_users() -> None:
      with get_sqlite_conn(DB_PATH) as conn:
          _ensure_users_table(conn)
          rows = conn.execute("SELECT email, is_active, created_at FROM users ORDER BY email").fetchall()
      if not rows:
          print("No hay usuarios registrados.")
          return
      print(f"{'Email':<40} {'Activo':<8} {'Creado'}")
      print("-" * 70)
      for r in rows:
          activo = "Sí" if r[1] else "No"
          print(f"{r[0]:<40} {activo:<8} {r[2]}")


  def main() -> None:
      parser = argparse.ArgumentParser(description="Gestión de usuarios del Evaluador")
      parser.add_argument("--email", help="Correo del usuario")
      parser.add_argument("--password", help="Contraseña (texto plano, se hashea)")
      parser.add_argument("--deactivate", action="store_true", help="Desactivar usuario")
      parser.add_argument("--list", action="store_true", help="Listar todos los usuarios")
      args = parser.parse_args()

      if args.list:
          list_users()
      elif args.deactivate:
          if not args.email:
              parser.error("--email es requerido con --deactivate")
          deactivate_user(args.email)
      elif args.email and args.password:
          create_user(args.email, args.password)
      else:
          parser.print_help()


  if __name__ == "__main__":
      main()
  ```

- [ ] **Paso 2: Probar el script localmente**

  ```bash
  python scripts/create_user.py --email tu_email@kantar.com --password prueba123
  python scripts/create_user.py --list
  ```

  Expected: usuario creado y listado correctamente.

- [ ] **Paso 3: Commit**

  ```bash
  git add scripts/create_user.py
  git commit -m "feat: add user management script for admin use"
  ```

---

### Task 10: Añadir guardia de sesión en main.py

**Files:**
- Modify: `main.py`

- [ ] **Paso 1: Añadir guardia de login al inicio de `main.py`**

  Añadir después del `st.set_page_config(...)` y antes de la función `main()`:

  ```python
  from ui.login import render_login
  ```

  Al inicio de la función `main()`, añadir como primera línea:

  ```python
  def main():
      """Funcion principal."""
      if not render_login():
          st.stop()

      # Inicializar sistema
      init_state()
      ...
  ```

- [ ] **Paso 2: Añadir botón de cerrar sesión en el sidebar**

  En `main.py`, dentro de la función `main()`, después de `render_sidebar_stats()`:

  ```python
  # Cerrar sesión
  st.sidebar.divider()
  user_email = st.session_state.get("user_email", "")
  st.sidebar.caption(f"Sesión: {user_email}")
  if st.sidebar.button("Cerrar sesión"):
      st.session_state.clear()
      st.rerun()
  ```

- [ ] **Paso 3: Verificar que la app arranque sin errores**

  ```bash
  streamlit run main.py
  ```

  Expected: aparece pantalla de login. Al ingresar con el usuario creado en Task 9, se muestra la app.

- [ ] **Paso 4: Commit**

  ```bash
  git add main.py
  git commit -m "feat: add session guard and logout button to main app"
  ```

---

## Fase 4: Pipeline mirror y configuración de despliegue

### Task 11: Configurar secrets y .gitignore

**Files:**
- Create: `.streamlit/secrets.toml.example`
- Modify: `.gitignore`

- [ ] **Paso 1: Crear plantilla de secrets**

  Crear `.streamlit/secrets.toml.example`:

  ```toml
  # Copiar este archivo como .streamlit/secrets.toml y rellenar los valores reales.
  # NUNCA commitar secrets.toml — está en .gitignore.

  [database]
  DATABASE_URL = "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
  ```

- [ ] **Paso 2: Añadir secrets.toml al .gitignore**

  Si existe `.gitignore`, añadir al final:

  ```
  # Streamlit secrets (nunca commitear)
  .streamlit/secrets.toml
  ```

  Si no existe `.gitignore`, crearlo con ese contenido.

- [ ] **Paso 3: Commit**

  ```bash
  git add .streamlit/secrets.toml.example .gitignore
  git commit -m "chore: add secrets template and gitignore for cloud deployment"
  ```

---

### Task 12: Configurar mirror Azure DevOps → GitHub

**Files:**
- Modify: `azure-pipelines.yml`

- [ ] **Paso 1: Añadir variable secreta en Azure DevOps**

  En Azure DevOps:
  - Ir al pipeline → Edit → Variables → New variable
  - Name: `GITHUB_TOKEN`
  - Value: el Personal Access Token de GitHub (Task 1, Paso 2)
  - Marcar como secreto (candado)
  - Guardar

- [ ] **Paso 2: Añadir step de mirror en `azure-pipelines.yml`**

  Añadir al final del archivo, después del step de `pytest`:

  ```yaml
    - script: |
        git remote add github https://x-token-auth:$(GITHUB_TOKEN)@github.com/TU_USUARIO_GITHUB/evaluador-proyectos.git || true
        git push github HEAD:main --force
      displayName: "Mirror to GitHub"
      condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  ```

  > Reemplazar `TU_USUARIO_GITHUB` con tu nombre de usuario real de GitHub.

- [ ] **Paso 3: Hacer un push a DevOps para activar el pipeline**

  ```bash
  git push
  ```

  Verificar en Azure DevOps → Pipelines que el step "Mirror to GitHub" aparece y termina en verde.
  Verificar en GitHub que el repo tiene el código.

- [ ] **Paso 4: Commit de azure-pipelines.yml**

  ```bash
  git add azure-pipelines.yml
  git commit -m "ci: add GitHub mirror step to pipeline for Streamlit deployment"
  git push
  ```

---

### Task 13: Desplegar en Streamlit Community Cloud

> Este task es manual. No hay código que escribir.

- [ ] **Paso 1: Conectar SCC a GitHub**

  En https://share.streamlit.io:
  - New app
  - Repository: `TU_USUARIO/evaluador-proyectos`
  - Branch: `main`
  - Main file path: `main.py`

- [ ] **Paso 2: Configurar secrets en SCC**

  En la pantalla de configuración de la app (antes de desplegar):
  - Advanced settings → Secrets
  - Pegar el contenido de `.streamlit/secrets.toml` con la URL real de Supabase:

  ```toml
  [database]
  DATABASE_URL = "postgresql://postgres:TU_PASSWORD@db.TU_REF.supabase.co:5432/postgres"
  ```

- [ ] **Paso 3: Desplegar**

  Click en "Deploy". La app tarda ~2 minutos en estar disponible.
  Verificar que la URL `https://TU_APP.streamlit.app` muestra la pantalla de login.

- [ ] **Paso 4: Crear usuarios del equipo**

  Con la DB de Supabase activa, correr el script localmente con `DATABASE_URL` exportada:

  ```bash
  # PowerShell
  $env:DATABASE_URL = "postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres"
  python scripts/create_user.py --email persona1@kantar.com --password temporal_seguro_1
  python scripts/create_user.py --email persona2@kantar.com --password temporal_seguro_2
  # ... repetir para cada miembro del equipo
  ```

  Compartir la URL de la app y las contraseñas temporales con cada persona.
  Pedirles que cambien su contraseña en el primer acceso (o hacerlo tú con `--password`).

---

## Fase 5: Migración de datos existentes

### Task 14: Migrar datos de SQLite a Supabase

- [ ] **Paso 1: Exportar datos de project_viability.db a SQL**

  Correr en PowerShell:

  ```powershell
  & python -c "
  import sqlite3, json
  conn = sqlite3.connect('project_viability.db')
  conn.row_factory = sqlite3.Row
  tables = ['projects', 'tracking', 'project_notes', 'project_members', 'effort_hours']
  for t in tables:
      try:
          rows = conn.execute(f'SELECT * FROM {t}').fetchall()
          print(f'{t}: {len(rows)} filas')
      except Exception as e:
          print(f'{t}: {e}')
  conn.close()
  "
  ```

  Expected: número de filas por tabla.

- [ ] **Paso 2: Usar el SQL Editor de Supabase para insertar datos**

  Para cada tabla, generar INSERTs desde SQLite y ejecutarlos en Supabase.
  Si hay pocas filas (< 100), se pueden copiar manualmente desde el Table Editor de Supabase.
  Si hay muchas filas, usar `pg_dump`-compatible export o la API REST de Supabase.

- [ ] **Paso 3: Verificar en la app desplegada**

  Abrir la app en Streamlit Community Cloud, iniciar sesión, y verificar que los proyectos existentes aparecen correctamente.

---

## Verificación final

- [ ] Pantalla de login aparece al abrir la URL
- [ ] Login correcto lleva a la app; login incorrecto muestra error
- [ ] Botón "Cerrar sesión" borra la sesión
- [ ] Un miembro del equipo puede ingresar notas de proyecto
- [ ] Los datos persisten después de cerrar el navegador
- [ ] Un push a Azure DevOps actualiza automáticamente la app en SCC
