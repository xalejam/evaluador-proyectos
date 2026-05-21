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

def test_adapter_placeholder_local(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from importlib import reload
    import infra.db.adapter as mod
    reload(mod)
    assert mod.PLACEHOLDER == "?"

def test_adapter_placeholder_cloud(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:fake@localhost/fake")
    from importlib import reload
    import infra.db.adapter as mod
    reload(mod)
    assert mod.PLACEHOLDER == "%s"
    assert mod.IS_CLOUD is True
    reload(mod)  # restaurar estado original
