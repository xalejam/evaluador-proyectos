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
