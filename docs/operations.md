# Operacion (Runbook)

## Arranque local

```powershell
.\.venv\Scripts\Activate.ps1
python start.py
```

## Instalacion inicial

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Bases de datos usadas

- `project_viability.db`
- `data/projects.db`

## Backup rapido

```powershell
Copy-Item project_viability.db project_viability.db.bak
Copy-Item data\projects.db data\projects.db.bak
```

## Limpiar datos (mantener estructura)

Usar solo cuando se quiera reiniciar carga:

```powershell
@'
import os, sqlite3
for db in ['project_viability.db', os.path.join('data', 'projects.db')]:
    if not os.path.exists(db):
        continue
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in tables:
        cur.execute(f"DELETE FROM {t}")
    conn.commit()
    conn.close()
    print(f"{db}: limpio")
'@ | .\.venv\Scripts\python.exe -
```

## Migraciones de columnas (shared.py)

`shared.py` agrega columnas faltantes en `projects` al iniciar (ej. `country`, `owner`, `initial_development_cost`, `hours_saved_per_month`).

Accion recomendada si hay cambios de esquema:
1. backup de DB
2. reiniciar app
3. validar columnas via `PRAGMA table_info(projects)`

## Salud basica del entorno

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py planning.py shared.py ui\use_case_matrix.py
```

Si compila, la app esta consistente a nivel sintaxis.
