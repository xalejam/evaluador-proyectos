from domain.services.bitacora_sync_service import BitacoraEntry, parse_bitacora_markdown


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
    text = (
        "## 2026-08-14\n\n### Xiomara Monroy — 2h\n\n"
        "**Qué se hizo**\n- Avanzó bastante.\n\n**Avance:** 70%\n"
    )
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


from domain.services.bitacora_sync_service import (
    BitacoraDocument,
    build_entry_group_id,
    slugify_author,
)


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
    text = (
        "## 2026-08-14\n\n### Xiomara Monroy — 4h\n"
        "<!-- entry_group_id: custom-id -->\n\n**Qué se hizo**\n- a\n"
    )
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


from domain.services.bitacora_sync_service import render_entry_block


def test_render_entry_block_includes_hours_and_via_app_marker():
    entry = BitacoraEntry(
        date="2026-08-14", author="Luis Astudillo", hours=2.0, via_app=True,
        entry_group_id="gid-1", avance_override=None, sections={"general": "- b"},
    )
    block = render_entry_block(entry)
    assert block.startswith("### Luis Astudillo — 2h _(vía app)_\n")
    assert "<!-- entry_group_id: gid-1 -->" in block
    assert "- b" in block


def test_render_entry_block_omits_hours_when_none():
    entry = BitacoraEntry(
        date="2026-08-14", author="Luis Astudillo", hours=None, via_app=False,
        entry_group_id="gid-1", avance_override=None, sections={"general": "- b"},
    )
    assert render_entry_block(entry).startswith("### Luis Astudillo\n")


def test_append_pulled_entry_to_existing_date():
    doc = BitacoraDocument("## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    pulled = BitacoraEntry(
        date="2026-08-14", author="Luis Astudillo", hours=2.0, via_app=True,
        entry_group_id="gid-2", avance_override=None, sections={"general": "- b"},
    )
    doc.append_pulled_entry(pulled)
    text = doc.render()
    assert "### Luis Astudillo — 2h _(vía app)_" in text
    assert text.index("Xiomara Monroy") < text.index("Luis Astudillo")


def test_append_pulled_entry_creates_new_date_at_top():
    doc = BitacoraDocument("## 2026-08-13\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n")
    pulled = BitacoraEntry(
        date="2026-08-14", author="Luis Astudillo", hours=2.0, via_app=True,
        entry_group_id="gid-2", avance_override=None, sections={"general": "- b"},
    )
    doc.append_pulled_entry(pulled)
    text = doc.render()
    assert text.index("## 2026-08-14") < text.index("## 2026-08-13")


def test_append_pulled_entry_multi_date_preserves_spacing():
    doc = BitacoraDocument("## 2026-08-14\n\n### Xiomara Monroy — 4h\n\n**Qué se hizo**\n- a\n\n## 2026-08-13\n\n### Carlos — 2h\n\n**Qué se hizo**\n- b\n")
    pulled = BitacoraEntry(
        date="2026-08-14", author="Luis Astudillo", hours=2.0, via_app=True,
        entry_group_id="gid-2", avance_override=None, sections={"general": "- c"},
    )
    doc.append_pulled_entry(pulled)
    text = doc.render()
    assert "\n\n\n" not in text
    assert "### Luis Astudillo — 2h _(vía app)_" in text
    assert text.index("Xiomara Monroy") < text.index("Luis Astudillo")
    assert text.index("Luis Astudillo") < text.index("## 2026-08-13")
