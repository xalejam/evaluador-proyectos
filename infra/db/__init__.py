"""Paquete de infraestructura DB.

Compatibilidad: mantiene exports historicos (`SessionLocal`, `init_db`, etc.)
que antes vivian en `infra/db.py`.
"""

from .sqlalchemy_store import (  # noqa: F401
    Base,
    ProjectORM,
    EvaluationORM,
    DATA_DIR,
    DB_PATH,
    DATABASE_URL,
    engine,
    SessionLocal,
    init_db,
)
from .connection import get_sqlite_conn  # noqa: F401
from .migrations import (  # noqa: F401
    ensure_schema,
    ensure_projects_schema,
    ensure_notes_schema,
    ensure_evaluations_schema,
)
