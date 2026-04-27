from infra.integrations.use_case_matrix_sync import _derive_matrix_answers


def test_derive_matrix_answers_maps_all_criteria():
    sample_project_data = {
        "staff_count": 3,
        "tasks_per_month": 30,
        "time_reduction_percent": 30,
        "development_hours": 100,
        "implementation_complexity": 2,
        "risk_level": 2,
    }
    sample_results = {
        "annual_savings": 10000,
    }
    result = _derive_matrix_answers(sample_project_data, sample_results)
    for key in ("A", "B", "C", "D", "E", "F", "G", "H"):
        assert key in result, f"Key '{key}' missing from _derive_matrix_answers result"
        assert 1 <= result[key] <= 5, f"Value out of range [1,5] for key '{key}': {result[key]}"
