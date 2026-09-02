from domain.services.bitacora_sync_service import (
    BitacoraDocument,
    BitacoraEntry,
    build_entry_group_id,
    compute_rollup,
    find_existing_entry_group_ids,
    get_project_status,
    parse_bitacora_markdown,
    project_exists,
    pull_new_entries,
    push_estado,
    push_entry,
    push_responsable,
    read_frontmatter_estado,
    read_frontmatter_project_id,
    read_frontmatter_responsable,
    render_entry_block,
    slugify_author,
    sync_bitacora_file,
)
from infra.db_migrations import get_project_members


def test_parses_single_entry_with_all_fields():
    text = (
        "## 2026-08-14\n"
        "\n"
        "_Acumulado del proyecto: 172.5h · Avance: 65%_\n"
        "\n"
        "### Xiomara Monroy — 4.5h\n"
        "<!-- entry_group_id: MX-DDD-0005-2026-08-14-xiomara-monroy -->\n"
        "\n"
        "**Qué se hizo**\n"
        "- Se corrigió el project_id.\n"
        "\n"
        "**Bloqueador**\n"
        "- Falta acceso a X.\n"
        "\n"
        "**Por dónde seguir**\n"
        "- Pedir el acceso.\n"
    )
    entries = parse_bitacora_markdown(text)
    assert len(entries) == 1
    e = entries[0]
    assert e.date == "2026-08-14"
    assert e.author == "Xiomara Monroy"
    assert e.hours == 4.5
    assert e.via_app is False
    assert e.entry_group_id == "MX-DDD-0005-2026-08-14-xiomara-monroy"
    assert "Se corrigió el project_id." in e.sections["general"]
    assert "Falta acceso a X." in e.sections["bloqueador"]
    assert "Pedir el acceso." in e.sections["proximo_paso"]
    assert "riesgo" not in e.sections


def test_parses_entry_without_hours_or_entry_group_id():
    text = "## 2026-08-14\n\n### Luis Astudillo\n\n**Qué se hizo**\n- Algo.\n"
    entries = parse_bitacora_markdown(text)
    assert entries[0].hours is None
    assert entries[0].entry_group_id is None


def test_parses_avance_override():
    text = "## 2026-08-14\n\n### Xiomara Monroy — 2h\n\n" "**Qué se hizo**\n- Avanzó bastante.\n\n**Avance:** 70%\n"
    entries = parse_bitacora_markdown(text)
    assert entries[0].avance_override == 70


def test_parses_via_app_marker():
    text = "## 2026-08-14\n\n### Luis Astudillo — 2h _(vía app)_\n\n**Qué se hizo**\n- x\n"
    entries = parse_bitacora_markdown(text)
    assert entries[0].via_app is True


def test_multiple_entries_same_date_and_two_dates():
    text = (
        "## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n\n"
        "### Luis Astudillo — 2h\n\n**Qué se hizo**\n- b\n\n"
        "## 2026-08-13\n\n### Xiomara Monroy — 3h\n\n**Qué se hizo**\n- c\n"
    )
    entries = parse_bitacora_markdown(text)
    assert [(e.date, e.author) for e in entries] == [
        ("2026-08-14", "Xiomara Monroy"),
        ("2026-08-14", "Luis Astudillo"),
        ("2026-08-13", "Xiomara Monroy"),
    ]


def test_no_entries_returns_empty_list():
    assert parse_bitacora_markdown("# Bitácora\n\nSin entradas todavía.\n") == []


def test_slugify_author_strips_accents_and_spaces():
    assert slugify_author("Xiomara Monroy") == "xiomara-monroy"
    assert slugify_author("Luis Astudillo") == "luis-astudillo"


def test_build_entry_group_id_disambiguates_collision():
    existing = {"MX-DDD-0005-2026-08-14-xiomara-monroy"}
    new_id = build_entry_group_id("MX-DDD-0005", "2026-08-14", "Xiomara Monroy", existing)
    assert new_id == "MX-DDD-0005-2026-08-14-xiomara-monroy-2"


def test_assigns_id_to_entry_missing_one():
    doc = BitacoraDocument("## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    new_entries = doc.assign_missing_entry_group_ids("MX-DDD-0005")
    assert len(new_entries) == 1
    assert new_entries[0].entry_group_id == "MX-DDD-0005-2026-08-14-xiomara-monroy"
    assert "<!-- entry_group_id: MX-DDD-0005-2026-08-14-xiomara-monroy -->" in doc.lines


def test_does_not_reassign_existing_id():
    text = "## 2026-08-14\n\n### Xiomara Monroy — 4h\n" "<!-- entry_group_id: custom-id -->\n\n**Qué se hizo**\n- a\n"
    doc = BitacoraDocument(text)
    new_entries = doc.assign_missing_entry_group_ids("MX-DDD-0005")
    assert new_entries == []
    assert doc.entries()[0].entry_group_id == "custom-id"


def test_disambiguates_two_entries_same_author_same_day():
    text = (
        "## 2026-08-14\n\n### Xiomara Monroy — 2h\n\n**Qué se hizo**\n- mañana\n\n"
        "### Xiomara Monroy — 3h\n\n**Qué se hizo**\n- tarde\n"
    )
    doc = BitacoraDocument(text)
    new_entries = doc.assign_missing_entry_group_ids("MX-DDD-0005")
    ids = [e.entry_group_id for e in new_entries]
    assert ids == [
        "MX-DDD-0005-2026-08-14-xiomara-monroy",
        "MX-DDD-0005-2026-08-14-xiomara-monroy-2",
    ]


def test_render_entry_block_includes_hours_and_via_app_marker():
    entry = BitacoraEntry(
        date="2026-08-14",
        author="Luis Astudillo",
        hours=2.0,
        via_app=True,
        entry_group_id="gid-1",
        avance_override=None,
        sections={"general": "- b"},
    )
    block = render_entry_block(entry)
    assert block.startswith("### Luis Astudillo — 2h _(vía app)_\n")
    assert "<!-- entry_group_id: gid-1 -->" in block
    assert "- b" in block


def test_render_entry_block_omits_hours_when_none():
    entry = BitacoraEntry(
        date="2026-08-14",
        author="Luis Astudillo",
        hours=None,
        via_app=False,
        entry_group_id="gid-1",
        avance_override=None,
        sections={"general": "- b"},
    )
    assert render_entry_block(entry).startswith("### Luis Astudillo\n")


def test_append_pulled_entry_to_existing_date():
    doc = BitacoraDocument("## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    pulled = BitacoraEntry(
        date="2026-08-14",
        author="Luis Astudillo",
        hours=2.0,
        via_app=True,
        entry_group_id="gid-2",
        avance_override=None,
        sections={"general": "- b"},
    )
    doc.append_pulled_entry(pulled)
    text = doc.render()
    assert "### Luis Astudillo — 2h _(vía app)_" in text
    assert text.index("Xiomara Monroy") < text.index("Luis Astudillo")


def test_append_pulled_entry_creates_new_date_at_top():
    doc = BitacoraDocument("## 2026-08-13\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    pulled = BitacoraEntry(
        date="2026-08-14",
        author="Luis Astudillo",
        hours=2.0,
        via_app=True,
        entry_group_id="gid-2",
        avance_override=None,
        sections={"general": "- b"},
    )
    doc.append_pulled_entry(pulled)
    text = doc.render()
    assert text.index("## 2026-08-14") < text.index("## 2026-08-13")


def test_append_pulled_entry_older_date_goes_after_existing_newer_dates():
    doc = BitacoraDocument("## 2026-08-13\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    pulled = BitacoraEntry(
        date="2026-07-01",
        author="Luis Astudillo",
        hours=2.0,
        via_app=True,
        entry_group_id="gid-old",
        avance_override=None,
        sections={"general": "- vieja"},
    )
    doc.append_pulled_entry(pulled)
    text = doc.render()
    assert text.index("## 2026-08-13") < text.index("## 2026-07-01")


def test_append_pulled_entry_inserts_between_existing_dates():
    doc = BitacoraDocument(
        "## 2026-08-17\n\n### X — 1h\n\n**Qué se hizo**\n- a\n\n"
        "## 2026-07-17\n\n### X — 1h\n\n**Qué se hizo**\n- b\n"
    )
    pulled = BitacoraEntry(
        date="2026-07-29",
        author="Y",
        hours=1.0,
        via_app=True,
        entry_group_id="gid-mid",
        avance_override=None,
        sections={"general": "- c"},
    )
    doc.append_pulled_entry(pulled)
    text = doc.render()
    assert text.index("## 2026-08-17") < text.index("## 2026-07-29") < text.index("## 2026-07-17")


def test_append_pulled_entry_multi_date_preserves_spacing():
    doc = BitacoraDocument(
        "## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n\n## 2026-08-13\n\n### Carlos — 2h\n\n**Qué se hizo**\n- b\n"
    )
    pulled = BitacoraEntry(
        date="2026-08-14",
        author="Luis Astudillo",
        hours=2.0,
        via_app=True,
        entry_group_id="gid-2",
        avance_override=None,
        sections={"general": "- c"},
    )
    doc.append_pulled_entry(pulled)
    text = doc.render()
    assert "\n\n\n" not in text
    assert "### Luis Astudillo — 2h _(vía app)_" in text
    assert text.index("Xiomara Monroy") < text.index("Luis Astudillo")
    assert text.index("Luis Astudillo") < text.index("## 2026-08-13")


def test_set_rollup_inserts_new_line():
    doc = BitacoraDocument("## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    doc.set_rollup("2026-08-14", 172.5, 65)
    text = doc.render()
    assert "_Acumulado del proyecto: 172.5h · Avance: 65%_" in text
    assert text.index("Acumulado") < text.index("Xiomara Monroy")


def test_set_rollup_replaces_existing_line():
    text = (
        "## 2026-08-14\n\n_Acumulado del proyecto: 100h · Avance: 50%_\n\n"
        "### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n"
    )
    doc = BitacoraDocument(text)
    doc.set_rollup("2026-08-14", 104.5, 55)
    rendered = doc.render()
    assert rendered.count("_Acumulado") == 1
    assert "_Acumulado del proyecto: 104.5h · Avance: 55%_" in rendered


def test_set_rollup_without_progress_shows_sin_dato():
    doc = BitacoraDocument("## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    doc.set_rollup("2026-08-14", 4.0, None)
    assert "_Acumulado del proyecto: 4h · Avance: sin dato_" in doc.render()


def test_set_rollup_raises_for_unknown_date():
    import pytest as _pytest

    doc = BitacoraDocument("## 2026-08-13\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    with _pytest.raises(ValueError):
        doc.set_rollup("2026-08-14", 4.0, None)


def test_project_exists_true_and_false(temp_db_conn):
    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    assert project_exists(temp_db_conn, "MX-DDD-0005") is True
    assert project_exists(temp_db_conn, "NO-EXISTE-0001") is False


def test_push_entry_inserts_one_row_per_section_with_hours_only_on_general(temp_db_conn):
    entry = BitacoraEntry(
        date="2026-08-14",
        author="Xiomara Monroy",
        hours=4.5,
        via_app=False,
        entry_group_id="MX-DDD-0005-2026-08-14-xiomara-monroy",
        avance_override=65,
        sections={"general": "Se hizo x", "bloqueador": "Falta y"},
    )
    inserted = push_entry(temp_db_conn, "MX-DDD-0005", entry)
    assert inserted == 2
    rows = temp_db_conn.execute(
        "SELECT note_type, effort_hours, progress_percent FROM project_notes ORDER BY note_type"
    ).fetchall()
    by_type = {r["note_type"]: dict(r) for r in rows}
    assert by_type["general"]["effort_hours"] == 4.5
    assert by_type["bloqueador"]["effort_hours"] is None
    assert by_type["general"]["progress_percent"] == 65


def test_find_existing_entry_group_ids(temp_db_conn):
    entry = BitacoraEntry(
        date="2026-08-14",
        author="X",
        hours=1.0,
        via_app=False,
        entry_group_id="gid-1",
        avance_override=None,
        sections={"general": "x"},
    )
    push_entry(temp_db_conn, "MX-DDD-0005", entry)
    assert find_existing_entry_group_ids(temp_db_conn, "MX-DDD-0005") == {"gid-1"}


def test_compute_rollup_sums_hours_and_gets_latest_progress(temp_db_conn):
    e1 = BitacoraEntry(
        date="2026-08-13",
        author="X",
        hours=3.0,
        via_app=False,
        entry_group_id="gid-1",
        avance_override=50,
        sections={"general": "a"},
    )
    e2 = BitacoraEntry(
        date="2026-08-14",
        author="X",
        hours=4.5,
        via_app=False,
        entry_group_id="gid-2",
        avance_override=65,
        sections={"general": "b"},
    )
    push_entry(temp_db_conn, "MX-DDD-0005", e1)
    push_entry(temp_db_conn, "MX-DDD-0005", e2)
    total_hours, progress = compute_rollup(temp_db_conn, "MX-DDD-0005")
    assert total_hours == 7.5
    assert progress == 65


def test_pull_new_entries_excludes_known_ids(temp_db_conn):
    e1 = BitacoraEntry(
        date="2026-08-14",
        author="Luis Astudillo",
        hours=2.0,
        via_app=False,
        entry_group_id="gid-1",
        avance_override=None,
        sections={"general": "a"},
    )
    push_entry(temp_db_conn, "MX-DDD-0005", e1)
    pulled = pull_new_entries(temp_db_conn, "MX-DDD-0005", known_ids=set())
    assert len(pulled) == 1
    assert pulled[0].entry_group_id == "gid-1"
    assert pulled[0].via_app is True

    assert pull_new_entries(temp_db_conn, "MX-DDD-0005", known_ids={"gid-1"}) == []


def test_read_frontmatter_project_id():
    text = "---\nproject_id: MX-DDD-0005\ntitulo: X\n---\n\n# Bitácora\n"
    assert read_frontmatter_project_id(text) == "MX-DDD-0005"


def test_read_frontmatter_project_id_missing_returns_none():
    assert read_frontmatter_project_id("# Sin frontmatter\n") is None


def test_sync_bitacora_file_pushes_new_local_entry(tmp_path, temp_db_conn):
    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text(
        "---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n"
        "## 2026-08-14\n\n### Xiomara Monroy — 4.5h\n\n**Qué se hizo**\n- a\n",
        encoding="utf-8",
    )
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

    rows = temp_db_conn.execute("SELECT * FROM project_notes").fetchall()
    assert len(rows) == 1
    updated_text = bitacora.read_text(encoding="utf-8")
    assert "entry_group_id: MX-DDD-0005-2026-08-14-xiomara-monroy" in updated_text
    assert "_Acumulado del proyecto: 4.5h · Avance: sin dato_" in updated_text


def test_sync_bitacora_file_pulls_app_entry(tmp_path, temp_db_conn):
    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    push_entry(
        temp_db_conn,
        "MX-DDD-0005",
        BitacoraEntry(
            date="2026-08-14",
            author="Luis Astudillo",
            hours=2.0,
            via_app=False,
            entry_group_id="app-gid-1",
            avance_override=70,
            sections={"general": "Capturado en la app"},
        ),
    )
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text("---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n", encoding="utf-8")
    result = sync_bitacora_file(temp_db_conn, bitacora)
    assert result["pulled"] == 1
    text = bitacora.read_text(encoding="utf-8")
    assert "### Luis Astudillo — 2h _(vía app)_" in text
    assert "Capturado en la app" in text


def test_sync_bitacora_file_skips_project_not_in_supabase(tmp_path, temp_db_conn):
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text(
        "---\nproject_id: NO-EXISTE-0001\n---\n\n## 2026-08-14\n\n### X — 1h\n\n**Qué se hizo**\n- a\n",
        encoding="utf-8",
    )
    original = bitacora.read_text(encoding="utf-8")
    result = sync_bitacora_file(temp_db_conn, bitacora)
    assert result["skipped"] is True
    assert bitacora.read_text(encoding="utf-8") == original


# --- Fix 1: idempotencia contra Supabase cuando se pierde el comentario local ---


def test_sync_bitacora_file_does_not_duplicate_when_supabase_already_has_the_group_id(tmp_path, temp_db_conn):
    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    gid = "MX-DDD-0005-2026-08-14-xiomara-monroy"
    # Simula que la fila ya existe en Supabase (p.ej. de una corrida anterior
    # cuyo <!-- entry_group_id --> local se perdió por un git checkout/merge).
    push_entry(
        temp_db_conn,
        "MX-DDD-0005",
        BitacoraEntry(
            date="2026-08-14",
            author="Xiomara Monroy",
            hours=4.5,
            via_app=False,
            entry_group_id=gid,
            avance_override=None,
            sections={"general": "Ya existe en Supabase"},
        ),
    )
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text(
        "---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n"
        "## 2026-08-14\n\n### Xiomara Monroy — 4.5h\n\n**Qué se hizo**\n- comentario local perdido\n",
        encoding="utf-8",
    )
    result = sync_bitacora_file(temp_db_conn, bitacora)
    assert result["pushed"] == 0

    rows = temp_db_conn.execute("SELECT COUNT(*) AS n FROM project_notes WHERE entry_group_id = ?", (gid,)).fetchall()
    count = rows[0]["n"] if isinstance(rows[0], dict) else rows[0][0]
    assert count == 1

    updated_text = bitacora.read_text(encoding="utf-8")
    assert f"<!-- entry_group_id: {gid} -->" in updated_text


# --- Fix 2: set_rollup solo se reescribe para la fecha más nueva tocada ---


def test_sync_bitacora_file_only_rewrites_rollup_for_newest_touched_date(tmp_path, temp_db_conn):
    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    # Entrada ya existente en Supabase con fecha 2026-08-14 (se "baja" al archivo).
    push_entry(
        temp_db_conn,
        "MX-DDD-0005",
        BitacoraEntry(
            date="2026-08-14",
            author="Luis Astudillo",
            hours=2.0,
            via_app=False,
            entry_group_id="app-gid-1",
            avance_override=None,
            sections={"general": "Capturado en la app"},
        ),
    )
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text(
        "---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n"
        "## 2026-08-13\n\n_Acumulado del proyecto: 100h · Avance: 50%_\n\n"
        "### Xiomara Monroy — 3h\n\n**Qué se hizo**\n- entrada previa del 2026-08-13\n",
        encoding="utf-8",
    )
    result = sync_bitacora_file(temp_db_conn, bitacora)
    assert result["pushed"] == 1
    assert result["pulled"] == 1

    text = bitacora.read_text(encoding="utf-8")
    # La entrada bajada tiene fecha 2026-08-14, que no existía en el archivo:
    # append_pulled_entry crea esa sección nueva antes de las existentes.
    date_14 = text.index("## 2026-08-14")
    date_13 = text.index("## 2026-08-13")
    assert date_14 < date_13
    # La fecha más nueva (2026-08-14) sí tiene línea de acumulado nueva.
    section_14 = text[date_14:date_13]
    assert "_Acumulado del proyecto:" in section_14
    # La fecha más antigua (2026-08-13) conserva su línea original sin cambios.
    section_13 = text[date_13:]
    assert "_Acumulado del proyecto: 100h · Avance: 50%_" in section_13


# --- Fix 3a: **Avance:** fuera de 0-100 debe rechazarse ---


def test_parse_bitacora_markdown_rejects_avance_out_of_range():
    import pytest as _pytest

    text = "## 2026-08-14\n\n### Xiomara Monroy — 2h\n\n" "**Qué se hizo**\n- Avanzó demasiado.\n\n**Avance:** 250%\n"
    with _pytest.raises(ValueError):
        parse_bitacora_markdown(text)


# --- Fix 3b: horas mal escritas no deben tumbar el parseo con float() ---


def test_parse_bitacora_markdown_handles_malformed_hours_without_crashing():
    text = "## 2026-08-14\n\n### Xiomara Monroy — 4.5.3h\n\n**Qué se hizo**\n- typo en las horas.\n"
    entries = parse_bitacora_markdown(text)
    assert len(entries) == 1
    assert entries[0].author == "Xiomara Monroy — 4.5.3h"
    assert entries[0].hours is None


# --- Fix 4: aviso de autor no registrado en project_members ---


def test_sync_bitacora_file_reports_unknown_authors(tmp_path, temp_db_conn):
    from infra.db_migrations import add_project_member

    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    add_project_member(temp_db_conn, "MX-DDD-0005", "Xiomara Monroy")
    add_project_member(temp_db_conn, "MX-DDD-0005", "Luis Astudillo")

    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text(
        "---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n"
        "## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n\n"
        "### Xiomara Monro — 2h\n\n**Qué se hizo**\n- typo en el nombre\n",
        encoding="utf-8",
    )
    result = sync_bitacora_file(temp_db_conn, bitacora)
    assert result["unknown_authors"] == ["Xiomara Monro"]
    assert result["pushed"] == 2

    rows = temp_db_conn.execute("SELECT DISTINCT author FROM project_notes").fetchall()
    authors = {r["author"] if isinstance(r, dict) else r[0] for r in rows}
    assert authors == {"Xiomara Monroy", "Xiomara Monro"}


def test_sync_bitacora_file_no_unknown_authors_when_no_members_registered(tmp_path, temp_db_conn):
    temp_db_conn.execute("INSERT INTO projects (id, project_id) VALUES ('P1','MX-DDD-0005')")
    temp_db_conn.commit()
    bitacora = tmp_path / "bitacora.md"
    bitacora.write_text(
        "---\nproject_id: MX-DDD-0005\n---\n\n# Bitácora\n\n"
        "## 2026-08-14\n\n### Cualquiera — 1h\n\n**Qué se hizo**\n- a\n",
        encoding="utf-8",
    )
    result = sync_bitacora_file(temp_db_conn, bitacora)
    assert result["unknown_authors"] == []


# --- Fix 5: avance_override sobrevive el round-trip render -> parse ---


def test_render_entry_block_round_trips_avance_override():
    entry = BitacoraEntry(
        date="2026-08-14",
        author="Luis Astudillo",
        hours=2.0,
        via_app=True,
        entry_group_id="gid-1",
        avance_override=70,
        sections={"general": "- b"},
    )
    block = render_entry_block(entry)
    assert "**Avance:** 70%" in block

    text = "## 2026-08-14\n\n" + block
    reparsed = parse_bitacora_markdown(text)
    assert len(reparsed) == 1
    assert reparsed[0].avance_override == 70


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
