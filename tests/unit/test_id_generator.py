from domain.services.id_generator import build_project_id, normalize_country, normalize_owner


def test_normalize_country_owner():
    assert normalize_country("mx") == "MX"
    assert normalize_owner(" Juan Pérez ") == "JUANPREZ"


def test_build_project_id_format():
    project_id = build_project_id("mx", "ana.lopez", 7)
    assert project_id == "MX-ANALOPEZ-0007"
