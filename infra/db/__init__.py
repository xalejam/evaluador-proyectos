"""Paquete de infraestructura DB.

Compatibilidad: mantiene exports historicos (`SessionLocal`, `init_db`, etc.)
que antes vivian en `infra/db.py`.
"""

from .connection import get_sqlite_conn  # noqa: F401
from .migrations import (  # noqa: F401
    ensure_evaluations_schema,
    ensure_notes_schema,
    ensure_projects_schema,
    ensure_schema,
)
from .sqlalchemy_store import (  # noqa: F401
    DATA_DIR,
    DATABASE_URL,
    DB_PATH,
    Base,
    EvaluationORM,
    ProjectORM,
    SessionLocal,
    engine,
    init_db,
)
