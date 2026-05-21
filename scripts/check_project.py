import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from infra.db.connection import get_sqlite_conn

PROJECT_ID = "LA-COPILOT-0001"

conn = get_sqlite_conn()

row = conn.execute("SELECT project_id, name, status FROM projects WHERE project_id = ?", (PROJECT_ID,)).fetchone()

if row:
    print("✅ Proyecto encontrado:", dict(row))
else:
    print("❌ Proyecto NO encontrado")

conn.close()
