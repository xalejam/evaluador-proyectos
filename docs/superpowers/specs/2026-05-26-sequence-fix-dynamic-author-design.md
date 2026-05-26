# Spec: Fix duplicate-key PostgreSQL + autor dinámico en Captura rápida

**Fecha**: 2026-05-26  
**Rama**: claude/elastic-bassi-1dce1c

---

## Contexto

Se detectaron tres bugs en producción (Supabase/SCC):

1. **`duplicate key value violates unique constraint "project_notes_pkey"`** — al guardar notas en Bitácora.  
2. **`duplicate key value violates unique constraint "project_evaluations_pkey"`** — al crear un nuevo proyecto en la hoja de viabilidad.  
3. **Autor default hardcodeado** — el campo "Autor" en Captura rápida siempre muestra `"Xiomara Monroy"` independientemente del usuario logueado.

---

## Causa raíz

### Bugs 1 & 2 — Secuencias PostgreSQL desincronizadas

Al migrar datos de SQLite → Supabase, las filas se insertaron con IDs explícitos (`note_id=1,2,3…`, `evaluation_id=1,2,3…`). Las secuencias SERIAL de PostgreSQL (`project_notes_note_id_seq`, `project_evaluations_evaluation_id_seq`) no se actualizaron y siguen apuntando a un valor bajo. Cuando PostgreSQL intenta generar el próximo ID para una nueva fila, produce un valor ya ocupado → constraint violation.

**Bug adicional (evaluation_repo.py)**: El INSERT usa `?` (SQLite) en vez de `PLACEHOLDER` (`%s` para psycopg2), y `cur.lastrowid` que no existe en psycopg2. Ambos causan error en cloud aunque el síntoma visible sea el `duplicate key`.

### Bug 3 — Autor no se deriva del usuario activo

`render_login()` guarda `st.session_state["user_email"]` pero no `"current_user"`. En `_render_capture_tab`, la lógica:
```python
default_author = str(st.session_state.get("author", st.session_state.get("current_user", "Xiomara Monroy")))
```
nunca encuentra `"current_user"` y cae al literal hardcodeado.

---

## Diseño

### Fix 1 & 2 — `fix_pg_sequences()` en `infra/db_migrations.py`

Agregar una función idempotente que sincroniza las secuencias con el `MAX(id)` actual de cada tabla. Llamarla al inicio de la app dentro de `ensure_all_operational_schema`, bloque `IS_CLOUD`.

```python
def fix_pg_sequences(conn) -> None:
    """
    Sincroniza secuencias SERIAL de PostgreSQL con el MAX actual de cada tabla.
    Solo corre en cloud (IS_CLOUD=True). Idempotente — no daña datos existentes.
    """
    if not IS_CLOUD:
        return
    pairs = [
        ("project_notes",       "note_id"),
        ("project_evaluations", "evaluation_id"),
        ("project_members",     "id"),
    ]
    for table, col in pairs:
        try:
            conn.execute(
                f"SELECT setval("
                f"  pg_get_serial_sequence('{table}', '{col}'),"
                f"  COALESCE((SELECT MAX({col}) FROM {table}), 1)"
                f")"
            )
        except Exception:
            pass  # tabla puede no existir todavía
    conn.commit()
```

Ubicación de la llamada en `ensure_all_operational_schema`:
```python
if IS_CLOUD:
    ensure_members_schema(conn)
    fix_pg_sequences(conn)   # <-- nueva línea
    return
```

### Fix adicional — `evaluation_repo.py`

Migrar todo el archivo a usar `PLACEHOLDER` y manejar el ID devuelto de forma compatible con PostgreSQL:

- Reemplazar las 14 `?` del INSERT por `PLACEHOLDER` (importado de `infra.db.adapter`).
- Reemplazar `cur.lastrowid` por:
  ```python
  if IS_CLOUD:
      row = conn.execute("SELECT MAX(evaluation_id) AS last_id FROM project_evaluations").fetchone()
      return int(row["last_id"] or 0) if row else 0
  else:
      return int(cur.lastrowid or 0)
  ```
- Migrar `list_snapshots` para usar `PLACEHOLDER` y orden compatible con PostgreSQL (ya que `datetime()` es SQLite-only).

### Fix 3 — Autor dinámico

**`ui/login.py`**

Agregar helper y setear `current_user` al autenticar:
```python
def _derive_display_name(email: str) -> str:
    """'carlos.montiel@wp.numerator.com' → 'Carlos Montiel'"""
    local = email.split("@")[0]
    parts = local.replace(".", " ").replace("_", " ").split()
    return " ".join(p.capitalize() for p in parts)

# En render_login(), tras autenticación exitosa:
st.session_state["authenticated"] = True
st.session_state["user_email"] = user["email"]
st.session_state["current_user"] = _derive_display_name(user["email"])
```

**`ui/tabs/seguimiento_operativo.py`** — función `_render_capture_tab`

Reemplazar la línea de `default_author` por búsqueda en `project_members`:
```python
_candidate = str(st.session_state.get("current_user", st.session_state.get("author", "")))
if _candidate:
    _all_members = get_all_known_members(conn)
    _lower = _candidate.lower()
    for _m in _all_members:
        if _m.lower() == _lower:
            _candidate = _m   # usar nombre exacto de la BD
            break
default_author = _candidate if _candidate else "Xiomara Monroy"
```

**`ui/state.py`** — actualizar fallback de `get_author_default()` para consistencia:
```python
def get_author_default() -> str:
    return str(st.session_state.get("author", st.session_state.get("current_user", "Xiomara Monroy")))
```

---

## Archivos modificados

| Archivo | Tipo de cambio |
|---|---|
| `infra/db_migrations.py` | Agregar `fix_pg_sequences()` + llamarla en `ensure_all_operational_schema` |
| `infra/db/repositories/evaluation_repo.py` | `?` → `PLACEHOLDER`, `lastrowid` → compatible cloud, `datetime()` → compatible cloud |
| `ui/login.py` | Agregar `_derive_display_name()` + setear `current_user` al autenticar |
| `ui/tabs/seguimiento_operativo.py` | Reemplazar `default_author` con lookup en `project_members` |
| `ui/state.py` | Consistencia en `get_author_default()` fallback |

---

## Criterios de éxito

1. Insertar una nota en Bitácora (cloud) no lanza `duplicate key` en `project_notes_pkey`.
2. Crear un nuevo proyecto en la hoja de viabilidad (cloud) no lanza `duplicate key` en `project_evaluations_pkey`.
3. Al loguearse como `xiomara.monroy@wp.numerator.com`, el campo "Autor" muestra `"Xiomara Monroy"`.
4. Al loguearse como `carlos.montiel@wp.numerator.com`, el campo "Autor" muestra `"Carlos Montiel"` (si existe en `project_members`).
5. `fix_pg_sequences()` es idempotente: correr dos veces no produce error ni daño.

---

## Consideraciones

- `fix_pg_sequences` usa `pg_get_serial_sequence()` que es nativa de PostgreSQL — no afecta SQLite.
- El `try/except` dentro del loop garantiza que una tabla no creada aún no rompa el startup.
- La búsqueda en `project_members` es case-insensitive — si el nombre en la tabla es `"xiomara monroy"` (minúsculas), también matchea.
- Si el usuario aún no está en ningún proyecto como miembro, el fallback es el nombre derivado del email (ya capitalizado).
