import os
import pytest
from importlib import reload


def _reload_adapter(monkeypatch, url: str | None):
    """Recarga infra.db.adapter con DATABASE_URL configurada o eliminada."""
    if url:
        monkeypatch.setenv("DATABASE_URL", url)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    import infra.db.adapter as mod

    reload(mod)
    return mod


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
    mod = _reload_adapter(monkeypatch, url=None)
    assert mod.PLACEHOLDER == "?"
    assert mod.IS_CLOUD is False


def test_adapter_placeholder_cloud(monkeypatch):
    mod = _reload_adapter(monkeypatch, url="postgresql://fake:fake@localhost/fake")
    assert mod.PLACEHOLDER == "%s"
    assert mod.IS_CLOUD is True
    # monkeypatch restaura DATABASE_URL al salir del test automáticamente
    # pero el módulo necesita ser recargado en estado limpio para los tests siguientes
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reload(mod)
