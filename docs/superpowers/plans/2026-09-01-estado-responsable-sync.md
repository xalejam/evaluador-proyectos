# Estado/Responsable Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extender `/sync-bitacora` para que, además de horas/avance (ya
implementado), también empuje `estado` y `responsable` del frontmatter de
`index.md` de cada proyecto del vault hacia `projects.status` y
`project_members` en Supabase.

**Architecture:** `sync_bitacora_file()` en `bitacora_sync_service.py` ya
resuelve `project_id` a partir de `bitacora.md` y confirma que existe en
Supabase antes de tocar nada. Este plan la extiende para, en ese mismo punto,
leer el `index.md` hermano (misma carpeta) y llamar a dos helpers nuevos:
`push_estado` (UPDATE directo a `projects.status`, solo si difiere — el vault
gana, no hay lectura en la dirección inversa) y `push_responsable` (reusa
`add_project_member`, ya existente e idempotente, para agregar a
`project_members` sin nunca borrar). Ninguno de los dos toca la lógica de
notas/horas/avance que ya funciona; ambos se activan solo cuando `index.md`
existe y su `project_id` coincide con el de `bitacora.md`.

**Tech Stack:** Python 3.12, SQLite3 (tests) / PostgreSQL (Supabase, cloud),
pytest. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-09-01-estado-responsable-sync-design.md`
en el vault de Obsidian (repo separado — ver `<vault>` más abajo).
Depende de `docs/superpowers/specs/2026-08-14-bitacora-supabase-sync-design.md`,
ya implementado.

## Global Constraints

- **Push-only, vault gana.** `estado`/`responsable` nunca se leen desde
  Supabase hacia el vault. Si `estado` (vault) ≠ `status` (Supabase), se
  sobrescribe Supabase. Nunca al revés.
- **`responsable → project_members` es aditivo.** Nunca se borra una fila de
  `project_members` aunque `responsable` cambie a otra persona.
- **Sin autocorrección de `project_id`.** Si `index.md` no existe, o su
  `project_id` no coincide con el de `bitacora.md`, se omite el push de
  estado/responsable para ese proyecto y se reporta — el push/pull de notas
  (ya implementado) sigue funcionando igual, sin verse afectado.
- **No se toca el esquema de Supabase.** `projects.status`, `projects.updated_at`
  y `project_members` ya existen (creados por `infra/db_migrations.py`); este
  plan no agrega columnas ni tablas.
- **`<vault>`** en este plan se refiere a la raíz del repo del vault de
  Obsidian (repo separado de éste), donde vive la documentación del equipo
  DDD y el spec referenciado arriba.

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `domain/services/bitacora_sync_service.py` | Modificar | Lectores de frontmatter `estado`/`responsable`, helpers `get_project_status`/`push_estado`/`push_responsable`, wiring en `sync_bitacora_file` |
| `tests/unit/test_bitacora_sync_service.py` | Modificar | Tests de los lectores nuevos, los helpers de push, y el wiring end-to-end |
| `scripts/sync_bitacora_from_vault.py` | Modificar | Imprime cambios de estado/responsable y sus totales en el reporte final |
| `<vault>/_meta/convenciones.md` | Modificar | Documenta que `/sync-bitacora` también empuja estado/responsable |
| `<vault>/AGENTS.md` | Modificar | Actualiza la mención de `/sync-bitacora` en "Qué NO va aquí" |
| `<vault>/CLAUDE.md` | Modificar | Actualiza la descripción de `/sync-bitacora` en "Comandos disponibles" |
| `<vault>/.claude/commands/sync-bitacora.md` | Modificar | Descripción del comando y paso "Al correr" mencionan estado/responsable |

---

## Task 1: Lectores de frontmatter para `estado` y `responsable`

**Files:**
- Modify: `domain/services/bitacora_sync_service.py` (bloque de
  `FRONTMATTER_PROJECT_ID_RE` / `read_frontmatter_project_id`, cerca del
  final del archivo — buscar por nombre, no por número de línea: los tasks
  anteriores desplazan las líneas originales)
- Test: `tests/unit/test_bitacora_sync_service.py`

**Interfaces:**
- Produces: `read_frontmatter_estado(text: str) -> str | None`,
  `read_frontmatter_responsable(text: str) -> str | None`. Mismo contrato que
  el ya existente `read_frontmatter_project_id(text: str) -> str | None`
  (que queda con el mismo nombre y comportamiento, solo se refactoriza por
  dentro para compartir el helper de extracción de frontmatter).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/unit/test_bitacora_sync_service.py`, extendiendo el import
del encabezado (agregar `read_frontmatter_estado` y
`read_frontmatter_responsable` a la tupla que ya importa
`read_frontmatter_project_id`), y al final del archivo:

```python
def test_read_frontmatter_estado():
    text = "---\nproject_id: MX-DDD-0005\nestado: executing\n---\n\n# Index\n"
    assert read_frontmatter_estado(text) == "executing"


def test_read_frontmatter_estado_missing_returns_none():
    assert read_frontmatter_estado("---\nproject_id: MX-DDD-0005\n---\n") is None


def test_read_frontmatter_responsable_with_spaces():
    text = "---\nproject_id: MX-DDD-0005\nresponsable: Xiomara Monroy\n---\n\n# Index\n"
    assert read_frontmatter_responsable(text) == "Xiomara Monroy"


def test_read_frontmatter_responsable_missing_returns_none():
    assert read_frontmatter_responsable("---\nproject_id: MX-DDD-0005\n---\n") is None
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_bitacora_sync_service.py -k "read_frontmatter_estado or read_frontmatter_responsable" -v`
Expected: FAIL con `ImportError` (los nombres todavía no existen en el módulo).

- [ ] **Step 3: Implementar**

En `domain/services/bitacora_sync_service.py`, reemplazar (líneas 364-374):

```python
FRONTMATTER_PROJECT_ID_RE = re.compile(r"^project_id:\s*(\S+)\s*$", re.MULTILINE)


def read_frontmatter_project_id(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    m = FRONTMATTER_PROJECT_ID_RE.search(text[3:end])
    return m.group(1) if m else None
```

por:

```python
FRONTMATTER_PROJECT_ID_RE = re.compile(r"^project_id:\s*(\S+)\s*$", re.MULTILINE)
FRONTMATTER_ESTADO_RE = re.compile(r"^estado:\s*(\S+)\s*$", re.MULTILINE)
FRONTMATTER_RESPONSABLE_RE = re.compile(r"^responsable:\s*(.+?)\s*$", re.MULTILINE)


def _frontmatter_field(text: str, pattern: re.Pattern[str]) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    m = pattern.search(text[3:end])
    return m.group(1) if m else None


def read_frontmatter_project_id(text: str) -> str | None:
    return _frontmatter_field(text, FRONTMATTER_PROJECT_ID_RE)


def read_frontmatter_estado(text: str) -> str | None:
    return _frontmatter_field(text, FRONTMATTER_ESTADO_RE)


def read_frontmatter_responsable(text: str) -> str | None:
    return _frontmatter_field(text, FRONTMATTER_RESPONSABLE_RE)
```

Nota: `responsable` usa `(.+?)` (no `\S+`) porque el nombre tiene espacios
(`Xiomara Monroy`); `estado` usa `\S+` porque los valores del enum
(`executing`, `approved`, ...) son una sola palabra, igual que `project_id`.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_bitacora_sync_service.py -v`
Expected: PASS — incluyendo los tests existentes `test_read_frontmatter_project_id`
y `test_read_frontmatter_project_id_missing_returns_none`, que no deben
romperse por el refactor.

- [ ] **Step 5: Commit**

```bash
git add domain/services/bitacora_sync_service.py tests/unit/test_bitacora_sync_service.py
git commit -m "feat: agregar lectores de frontmatter para estado y responsable"
```

---

## Task 2: Helpers de escritura — `get_project_status`, `push_estado`, `push_responsable`

**Files:**
- Modify: `domain/services/bitacora_sync_service.py` (imports + nuevas funciones después de `project_exists`)
- Test: `tests/unit/test_bitacora_sync_service.py`

**Interfaces:**
- Consumes: `PLACEHOLDER`, `db_now` de `infra.db.adapter`; `add_project_member`,
  `get_project_members` de `infra.db_migrations` (este último ya estaba
  importado en el archivo).
- Produces: `get_project_status(conn, project_id: str) -> str | None`;
  `push_estado(conn, project_id: str, estado: str) -> dict[str, str] | None`
  (devuelve `{"anterior": ..., "nuevo": estado}` si escribió, `None` si el
  estado ya coincidía); `push_responsable(conn, project_id: str, responsable: str) -> str | None`
  (devuelve `responsable` si lo agregó, `None` si ya era miembro).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/unit/test_bitacora_sync_service.py` (agregar
`get_project_status`, `push_estado`, `push_responsable` al import del
encabezado):

```python
def test_get_project_status_returns_none_when_missing(temp_db_conn):
    assert get_project_status(temp_db_conn, "NO-EXISTE-0001") is None


def test_push_estado_updates_when_different(temp_db_conn):
    temp_db_conn.execute(
        "INSERT INTO projects (id, project_id, status) VALUES ('P1','MX-DDD-0005','approved')"
    )
    temp_db_conn.commit()
    change = push_estado(temp_db_conn, "MX-DDD-0005", "executing")
    assert change == {"anterior": "approved", "nuevo": "executing"}
    assert get_project_status(temp_db_conn, "MX-DDD-0005") == "executing"


def test_push_estado_noop_when_same(temp_db_conn):
    temp_db_conn.execute(
        "INSERT INTO projects (id, project_id, status) VALUES ('P1','MX-DDD-0005','executing')"
    )
    temp_db_conn.commit()
    assert push_estado(temp_db_conn, "MX-DDD-0005", "executing") is None


def test_push_responsable_adds_when_missing(temp_db_conn):
    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    added = push_responsable(temp_db_conn, "MX-DDD-0005", "Xiomara Monroy")
    assert added == "Xiomara Monroy"
    assert get_project_members(temp_db_conn, "MX-DDD-0005") == ["Xiomara Monroy"]


def test_push_responsable_noop_when_already_member(temp_db_conn):
    from infra.db_migrations import add_project_member

    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    add_project_member(temp_db_conn, "MX-DDD-0005", "Xiomara Monroy")
    assert push_responsable(temp_db_conn, "MX-DDD-0005", "Xiomara Monroy") is None
    assert get_project_members(temp_db_conn, "MX-DDD-0005") == ["Xiomara Monroy"]
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_bitacora_sync_service.py -k "get_project_status or push_estado or push_responsable" -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementar**

En `domain/services/bitacora_sync_service.py`, cambiar el import de la parte
superior del archivo de:

```python
from infra.db.adapter import IS_CLOUD, PLACEHOLDER
from infra.db_migrations import get_project_members
```

a:

```python
from infra.db.adapter import IS_CLOUD, PLACEHOLDER, db_now
from infra.db_migrations import add_project_member, get_project_members
```

Y agregar estas tres funciones inmediatamente después de `project_exists`
(que queda sin cambios):

```python
def get_project_status(conn, project_id: str) -> str | None:
    row = conn.execute(f"SELECT status FROM projects WHERE project_id = {PLACEHOLDER}", (project_id,)).fetchone()
    if row is None:
        return None
    return row["status"] if isinstance(row, dict) else row[0]


def push_estado(conn, project_id: str, estado: str) -> dict[str, str] | None:
    """Actualiza projects.status si difiere del estado del vault (el vault gana).
    Devuelve {'anterior': ..., 'nuevo': estado} si escribió, None si ya coincidía."""
    current = get_project_status(conn, project_id)
    if current == estado:
        return None
    conn.execute(
        f"UPDATE projects SET status = {PLACEHOLDER}, updated_at = {PLACEHOLDER} WHERE project_id = {PLACEHOLDER}",
        (estado, db_now(), project_id),
    )
    conn.commit()
    return {"anterior": current, "nuevo": estado}


def push_responsable(conn, project_id: str, responsable: str) -> str | None:
    """Agrega el responsable del vault a project_members si todavía no está.
    Devuelve el nombre si lo agregó, None si ya era miembro."""
    if responsable in get_project_members(conn, project_id):
        return None
    add_project_member(conn, project_id, responsable)
    return responsable
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_bitacora_sync_service.py -v`
Expected: PASS, todos los tests del archivo (incluidos los preexistentes).

- [ ] **Step 5: Commit**

```bash
git add domain/services/bitacora_sync_service.py tests/unit/test_bitacora_sync_service.py
git commit -m "feat: agregar push_estado y push_responsable a projects/project_members"
```

---

## Task 3: Wiring en `sync_bitacora_file`

**Files:**
- Modify: `domain/services/bitacora_sync_service.py` (función
  `sync_bitacora_file` — buscar por nombre, no por número de línea: los
  tasks anteriores desplazan las líneas originales)
- Test: `tests/unit/test_bitacora_sync_service.py`

**Interfaces:**
- Consumes: `read_frontmatter_estado`, `read_frontmatter_responsable` (Task 1);
  `push_estado`, `push_responsable` (Task 2).
- Produces: `sync_bitacora_file(conn, vault_path: Path) -> dict` — el dict de
  retorno gana tres claves nuevas: `estado_change: dict[str, str] | None`,
  `responsable_agregado: str | None`, `metadata_warning: str | None`. Las
  claves ya existentes (`pushed`, `pulled`, `skipped`, `project_id`,
  `unknown_authors`) no cambian de tipo ni de significado.

- [ ] **Step 1: Actualizar el test existente que compara el dict completo**

En `tests/unit/test_bitacora_sync_service.py`, la función
`test_sync_bitacora_file_pushes_new_local_entry` compara `result` contra un
dict exacto — hay que agregarle las tres claves nuevas. Reemplazar:

```python
    result = sync_bitacora_file(temp_db_conn, bitacora)
    assert result == {
        "pushed": 1,
        "pulled": 0,
        "skipped": False,
        "project_id": "MX-DDD-0005",
        "unknown_authors": [],
    }
```

por:

```python
    result = sync_bitacora_file(temp_db_conn, bitacora)
    assert result == {
        "pushed": 1,
        "pulled": 0,
        "skipped": False,
        "project_id": "MX-DDD-0005",
        "unknown_authors": [],
        "estado_change": None,
        "responsable_agregado": None,
        "metadata_warning": "no existe index.md junto a bitacora.md; no se sincronizó estado/responsable",
    }
```

(Ese fixture solo crea `bitacora.md` en `tmp_path`, sin `index.md` — el
warning es el comportamiento correcto y esperado para ese caso.)

- [ ] **Step 2: Escribir los tests nuevos que fallan**

Agregar al final de `tests/unit/test_bitacora_sync_service.py`:

```python
def test_sync_bitacora_file_pushes_estado_and_responsable_from_index(tmp_path, temp_db_conn):
    temp_db_conn.execute(
        "INSERT INTO projects (id, project_id, status) VALUES ('P1','MX-DDD-0005','approved')"
    )
    temp_db_conn.commit()
    (tmp_path / "index.md").write_text(
        "---\nproject_id: MX-DDD-0005\nestado: executing\nresponsable: Xiomara Monroy\n---\n\n# Index\n",
        encoding="utf-8",
    )
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text("---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n", encoding="utf-8")

    result = sync_bitacora_file(temp_db_conn, bitacora)

    assert result["estado_change"] == {"anterior": "approved", "nuevo": "executing"}
    assert result["responsable_agregado"] == "Xiomara Monroy"
    assert result["metadata_warning"] is None
    assert get_project_status(temp_db_conn, "MX-DDD-0005") == "executing"
    assert get_project_members(temp_db_conn, "MX-DDD-0005") == ["Xiomara Monroy"]


def test_sync_bitacora_file_metadata_noop_when_estado_already_matches(tmp_path, temp_db_conn):
    from infra.db_migrations import add_project_member

    temp_db_conn.execute(
        "INSERT INTO projects (id, project_id, status) VALUES ('P1','MX-DDD-0005','executing')"
    )
    temp_db_conn.commit()
    add_project_member(temp_db_conn, "MX-DDD-0005", "Xiomara Monroy")
    (tmp_path / "index.md").write_text(
        "---\nproject_id: MX-DDD-0005\nestado: executing\nresponsable: Xiomara Monroy\n---\n\n# Index\n",
        encoding="utf-8",
    )
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text("---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n", encoding="utf-8")

    result = sync_bitacora_file(temp_db_conn, bitacora)

    assert result["estado_change"] is None
    assert result["responsable_agregado"] is None
    assert result["metadata_warning"] is None


def test_sync_bitacora_file_warns_when_index_project_id_mismatches(tmp_path, temp_db_conn):
    temp_db_conn.execute(
        "INSERT INTO projects (id, project_id, status) VALUES ('P1','MX-DDD-0005','approved')"
    )
    temp_db_conn.commit()
    (tmp_path / "index.md").write_text(
        "---\nproject_id: MX-DDD-0099\nestado: executing\n---\n\n# Index\n",
        encoding="utf-8",
    )
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text("---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n", encoding="utf-8")

    result = sync_bitacora_file(temp_db_conn, bitacora)

    assert result["estado_change"] is None
    assert result["responsable_agregado"] is None
    assert "distinto al de bitacora.md" in result["metadata_warning"]
    assert get_project_status(temp_db_conn, "MX-DDD-0005") == "approved"
```

- [ ] **Step 3: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_bitacora_sync_service.py -k "pushes_estado_and_responsable or metadata_noop or index_project_id_mismatches or pushes_new_local_entry" -v`
Expected: FAIL — el dict que devuelve `sync_bitacora_file` todavía no tiene
las claves nuevas.

- [ ] **Step 4: Implementar**

En `domain/services/bitacora_sync_service.py`, reemplazar el cuerpo de
`sync_bitacora_file` (líneas 377-424) por:

```python
def sync_bitacora_file(conn, vault_path: Path) -> dict:
    text = vault_path.read_text(encoding="utf-8")
    project_id = read_frontmatter_project_id(text)
    if not project_id or not project_exists(conn, project_id):
        return {"pushed": 0, "pulled": 0, "skipped": True, "project_id": project_id}

    doc = BitacoraDocument(text)
    new_local_entries = doc.assign_missing_entry_group_ids(project_id)

    # Fix 1: no confiar solo en los <!-- entry_group_id --> del archivo local
    # (git checkout/reset, merge conflicts o clones viejos pueden perder ese
    # comentario). Antes de insertar, verificar contra lo que ya existe en
    # Supabase para evitar duplicar filas inmutables.
    existing_supabase_ids = find_existing_entry_group_ids(conn, project_id)
    entries_to_push = [e for e in new_local_entries if e.entry_group_id not in existing_supabase_ids]
    for entry in entries_to_push:
        push_entry(conn, project_id, entry)

    known_ids = doc.known_entry_group_ids()
    pulled_entries = pull_new_entries(conn, project_id, known_ids)
    for entry in pulled_entries:
        doc.append_pulled_entry(entry)

    touched_dates = {e.date for e in entries_to_push} | {e.date for e in pulled_entries}
    if touched_dates:
        total_hours, progress_percent = compute_rollup(conn, project_id)
        doc.set_rollup(max(touched_dates), total_hours, progress_percent)

    # Fix 4: avisar de autores que no están dados de alta como miembro del
    # proyecto (typos silenciosos que "Carga del equipo" nunca mostraría).
    # Si el proyecto no tiene miembros registrados todavía no se avisa: es
    # un hueco preexistente distinto al de este fix.
    unknown_authors: list[str] = []
    members = get_project_members(conn, project_id)
    if members:
        member_set = set(members)
        unknown_authors = sorted({e.author for e in new_local_entries + pulled_entries if e.author not in member_set})

    if new_local_entries or pulled_entries:
        vault_path.write_text(doc.render(), encoding="utf-8")

    # estado/responsable viven en index.md, no en bitacora.md: se leen y
    # sincronizan por separado, del archivo hermano en la misma carpeta.
    estado_change: dict[str, str] | None = None
    responsable_agregado: str | None = None
    metadata_warning: str | None = None

    index_path = vault_path.parent / "index.md"
    if not index_path.exists():
        metadata_warning = "no existe index.md junto a bitacora.md; no se sincronizó estado/responsable"
    else:
        index_text = index_path.read_text(encoding="utf-8")
        index_project_id = read_frontmatter_project_id(index_text)
        if index_project_id != project_id:
            metadata_warning = (
                f"index.md tiene project_id={index_project_id!r}, distinto al de bitacora.md "
                f"({project_id!r}); no se sincronizó estado/responsable"
            )
        else:
            estado = read_frontmatter_estado(index_text)
            if estado:
                estado_change = push_estado(conn, project_id, estado)
            responsable = read_frontmatter_responsable(index_text)
            if responsable:
                responsable_agregado = push_responsable(conn, project_id, responsable)

    return {
        "pushed": len(entries_to_push),
        "pulled": len(pulled_entries),
        "skipped": False,
        "project_id": project_id,
        "unknown_authors": unknown_authors,
        "estado_change": estado_change,
        "responsable_agregado": responsable_agregado,
        "metadata_warning": metadata_warning,
    }
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_bitacora_sync_service.py -v`
Expected: PASS, todos los tests del archivo.

- [ ] **Step 6: Commit**

```bash
git add domain/services/bitacora_sync_service.py tests/unit/test_bitacora_sync_service.py
git commit -m "feat: sync_bitacora_file empuja estado y responsable desde index.md"
```

---

## Task 4: Reporte extendido en `scripts/sync_bitacora_from_vault.py`

**Files:**
- Modify: `scripts/sync_bitacora_from_vault.py`

**Interfaces:**
- Consumes: `result["estado_change"]`, `result["responsable_agregado"]`,
  `result["metadata_warning"]` del dict devuelto por `sync_bitacora_file`
  (Task 3).

- [ ] **Step 1: Implementar**

Reemplazar el cuerpo de `main()` completo por:

```python
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, help="Ruta al repo del vault de Obsidian")
    args = parser.parse_args()

    vault_root = Path(args.vault)
    bitacora_files = sorted(vault_root.glob("proyectos/*/bitacora.md"))
    if not bitacora_files:
        print(f"No se encontraron bitacora.md bajo {vault_root / 'proyectos'}")
        return 1

    conn = get_connection()
    total_pushed = total_pulled = total_estados = total_miembros = 0
    skipped: list[str] = []
    failed: list[str] = []
    try:
        for path in bitacora_files:
            rel = path.relative_to(vault_root)
            try:
                result = sync_bitacora_file(conn, path)
            except Exception as e:
                print(f"{rel}: ERROR - {e}")
                failed.append(f"{rel}: {e}")
                continue
            if result["skipped"]:
                skipped.append(f"{rel} (project_id={result['project_id']!r} no existe en Supabase)")
                continue
            total_pushed += result["pushed"]
            total_pulled += result["pulled"]
            if result["pushed"] or result["pulled"]:
                print(f"{rel}: +{result['pushed']} subidas, +{result['pulled']} bajadas")
            if result.get("unknown_authors"):
                print(f"  ⚠ autor(es) no registrados en project_members: {', '.join(result['unknown_authors'])}")
            estado_change = result.get("estado_change")
            if estado_change:
                total_estados += 1
                print(f"  estado: {estado_change['anterior']}→{estado_change['nuevo']} actualizado")
            if result.get("responsable_agregado"):
                total_miembros += 1
                print(f"  {result['responsable_agregado']} agregado a project_members")
            if result.get("metadata_warning"):
                print(f"  ⚠ {result['metadata_warning']}")
    finally:
        conn.close()

    print(
        f"\nTotal: {total_pushed} subidas, {total_pulled} bajadas, "
        f"{total_estados} estado(s) actualizado(s), {total_miembros} miembro(s) agregado(s)."
    )
    if skipped:
        print(f"\n{len(skipped)} archivo(s) sin sincronizar (proyecto no dado de alta en Supabase):")
        for line in skipped:
            print(f"  - {line}")
    if failed:
        print(f"\n{len(failed)} archivo(s) con error durante la sincronización:")
        for line in failed:
            print(f"  - {line}")
    return 0
```

- [ ] **Step 2: Verificación manual**

No hay test automatizado para este script (es un wrapper CLI delgado — igual
que hoy, antes de este plan). Verificar a mano:

```bash
.venv/Scripts/python.exe -c "
import ast, pathlib
ast.parse(pathlib.Path('scripts/sync_bitacora_from_vault.py').read_text(encoding='utf-8'))
print('sintaxis OK')
"
```

Expected: `sintaxis OK`. Si se quiere una verificación end-to-end real, correr
`/sync-bitacora` desde el vault contra un proyecto cuyo `estado` en `index.md`
difiera a propósito del `status` en Supabase, y confirmar que la línea
`estado: X→Y actualizado` aparece en la salida.

- [ ] **Step 3: Commit**

```bash
git add scripts/sync_bitacora_from_vault.py
git commit -m "feat: reportar cambios de estado y responsable en sync_bitacora_from_vault"
```

---

## Task 5: Documentación del vault

**Files:**
- Modify: `<vault>/_meta/convenciones.md`
- Modify: `<vault>/AGENTS.md`
- Modify: `<vault>/CLAUDE.md`
- Modify: `<vault>/.claude/commands/sync-bitacora.md`

**Interfaces:** N/A (solo documentación, sin código).

- [ ] **Step 1: `_meta/convenciones.md`**

Después del párrafo que termina en "`bitacora.md` es, ahora, una manera más
cómoda de escribir ahí." (dentro de la sección "Qué vive en cada sistema"),
agregar:

```markdown

Desde 2026-09, `/sync-bitacora` también empuja `estado` y `responsable` del
frontmatter de `index.md` hacia `projects.status` y `project_members` en
Supabase (ver
[docs/superpowers/specs/2026-09-01-estado-responsable-sync-design.md](../docs/superpowers/specs/2026-09-01-estado-responsable-sync-design.md)).
A diferencia de horas/avance, acá el vault es la fuente de verdad: si
difieren, gana lo que dice `index.md`, sin lectura en la dirección inversa.
```

- [ ] **Step 2: `AGENTS.md`**

En el párrafo que empieza con "**Qué NO va aquí:**", reemplazar:

```markdown
La bitácora
narrativa sí vive aquí (`proyectos/{slug}/bitacora.md`) y desde 2026-08
también alimenta el registro cuantitativo de la app vía `/sync-bitacora` —
ver [_meta/convenciones.md](_meta/convenciones.md).
```

por:

```markdown
La bitácora
narrativa sí vive aquí (`proyectos/{slug}/bitacora.md`) y desde 2026-08
también alimenta el registro cuantitativo de la app vía `/sync-bitacora`,
que desde 2026-09 también sincroniza `estado` y `responsable` de `index.md`
hacia la app — ver [_meta/convenciones.md](_meta/convenciones.md).
```

- [ ] **Step 3: `CLAUDE.md`**

En la lista "Comandos disponibles", reemplazar:

```markdown
  - `/sync-bitacora` — sincroniza `proyectos/{slug}/bitacora.md` con el
    registro cuantitativo (horas, % avance) de la app de portafolio en
    Supabase, en ambos sentidos.
```

por:

```markdown
  - `/sync-bitacora` — sincroniza `proyectos/{slug}/bitacora.md` con el
    registro cuantitativo (horas, % avance) de la app de portafolio en
    Supabase, en ambos sentidos; también empuja `estado` y `responsable`
    de `index.md` hacia Supabase (push-only, el vault gana).
```

- [ ] **Step 4: `.claude/commands/sync-bitacora.md`**

Reemplazar la línea de `description` del frontmatter:

```yaml
description: Sincroniza bitacora.md de proyectos/ con Supabase (horas, avance, notas)
```

por:

```yaml
description: Sincroniza bitacora.md e index.md de proyectos/ con Supabase (horas, avance, notas, estado, responsable)
```

Reemplazar el párrafo de apertura (debajo del `# Sincronizar bitácora con
Supabase`):

```markdown
Sube a Supabase las entradas nuevas de `proyectos/*/bitacora.md` y trae las
que se hayan capturado desde la app Streamlit, según el diseño en
[docs/superpowers/specs/2026-08-14-bitacora-supabase-sync-design.md](../../docs/superpowers/specs/2026-08-14-bitacora-supabase-sync-design.md).
```

por:

```markdown
Sube a Supabase las entradas nuevas de `proyectos/*/bitacora.md`, trae las
que se hayan capturado desde la app Streamlit, y empuja `estado`/`responsable`
del `index.md` de cada proyecto, según el diseño en
[docs/superpowers/specs/2026-08-14-bitacora-supabase-sync-design.md](../../docs/superpowers/specs/2026-08-14-bitacora-supabase-sync-design.md)
y [docs/superpowers/specs/2026-09-01-estado-responsable-sync-design.md](../../docs/superpowers/specs/2026-09-01-estado-responsable-sync-design.md).
```

Y en la sección "Al correr", reemplazar el paso 3:

```markdown
3. Reportá al usuario tal cual lo imprime el script: cuántas entradas se
   subieron, cuántas se bajaron, y qué proyectos quedaron sin sincronizar
   por no existir todavía en Supabase.
```

por:

```markdown
3. Reportá al usuario tal cual lo imprime el script: cuántas entradas se
   subieron, cuántas se bajaron, cuántos `estado` se actualizaron, cuántos
   `responsable` se agregaron a `project_members`, y qué proyectos quedaron
   sin sincronizar por no existir todavía en Supabase.
```

- [ ] **Step 5: Commit (en el repo del vault, no en éste)**

```bash
git add _meta/convenciones.md AGENTS.md CLAUDE.md .claude/commands/sync-bitacora.md
git commit -m "docs: documentar sync de estado y responsable en /sync-bitacora"
```
