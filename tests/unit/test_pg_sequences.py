"""Tests para fix_pg_sequences en db_migrations."""


def test_fix_pg_sequences_skips_when_not_cloud(monkeypatch):
    """Cuando IS_CLOUD=False la función no ejecuta nada."""
    import infra.db_migrations as mig

    monkeypatch.setattr(mig, "IS_CLOUD", False)

    executed = []

    class _Conn:
        def execute(self, sql, params=()):
            executed.append(sql)

        def commit(self):
            pass

    mig.fix_pg_sequences(_Conn())
    assert executed == [], "No debe ejecutar SQL en modo SQLite"


def test_fix_pg_sequences_calls_setval_for_three_tables(monkeypatch):
    """Cuando IS_CLOUD=True llama setval para las tres tablas."""
    import infra.db_migrations as mig

    monkeypatch.setattr(mig, "IS_CLOUD", True)

    executed = []

    class _Conn:
        def execute(self, sql, params=()):
            executed.append(sql)
            return self

        def fetchone(self):
            return None

        def commit(self):
            pass

    mig.fix_pg_sequences(_Conn())

    assert any("project_notes" in s for s in executed), "Debe sincronizar project_notes"
    assert any("project_evaluations" in s for s in executed), "Debe sincronizar project_evaluations"
    assert any("project_members" in s for s in executed), "Debe sincronizar project_members"


def test_fix_pg_sequences_tolerates_table_error(monkeypatch):
    """Si una tabla lanza excepción, las demás siguen ejecutándose."""
    import infra.db_migrations as mig

    monkeypatch.setattr(mig, "IS_CLOUD", True)

    call_count = [0]

    class _Conn:
        def execute(self, sql, params=()):
            call_count[0] += 1
            if "project_notes" in sql:
                raise Exception("tabla no existe")
            return self

        def fetchone(self):
            return None

        def commit(self):
            pass

    # No debe propagar la excepción
    mig.fix_pg_sequences(_Conn())
    # project_evaluations y project_members deben haberse intentado
    assert call_count[0] >= 2


def test_ensure_all_operational_schema_calls_fix_sequences_in_cloud(monkeypatch):
    """ensure_all_operational_schema llama fix_pg_sequences cuando IS_CLOUD=True."""
    import infra.db_migrations as mig

    monkeypatch.setattr(mig, "IS_CLOUD", True)

    called = []

    def _fake_fix(conn):
        called.append(True)

    def _fake_ensure_members(conn):
        pass

    monkeypatch.setattr(mig, "fix_pg_sequences", _fake_fix)
    monkeypatch.setattr(mig, "ensure_members_schema", _fake_ensure_members)

    class _Conn:
        pass

    mig.ensure_all_operational_schema(_Conn())
    assert called == [True], "fix_pg_sequences debe llamarse en modo cloud"
