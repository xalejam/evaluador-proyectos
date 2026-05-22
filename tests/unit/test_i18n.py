from ui.i18n import TRANSLATIONS, get_language, set_language, t


def test_default_language_is_spanish():
    assert get_language() == "es"


def test_translate_known_key_spanish():
    set_language("es")
    result = t("project_name")
    assert isinstance(result, str)
    assert len(result) > 0


def test_translate_known_key_portuguese():
    set_language("pt")
    result = t("project_name")
    assert isinstance(result, str)


def test_translate_unknown_key_returns_key():
    set_language("es")
    result = t("__nonexistent_key_xyz__")
    assert result == "__nonexistent_key_xyz__"


def test_all_es_keys_exist_in_pt():
    es_keys = set(TRANSLATIONS.get("es", {}).keys())
    pt_keys = set(TRANSLATIONS.get("pt", {}).keys())
    missing = es_keys - pt_keys
    assert not missing, f"Keys missing in PT: {missing}"
