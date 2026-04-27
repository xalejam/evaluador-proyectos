from ui.calculator import ProjectViabilityCalculator


def _base_inputs(**overrides) -> dict:
    base = {
        "current_time_per_task": 2.0,
        "tasks_per_month": 20,
        "staff_count": 3,
        "time_reduction_percent": 50,
        "avg_salary_per_hour": 25.0,
        "development_hours": 80,
        "development_cost_per_hour": 50.0,
        "maintenance_monthly": 100.0,
        "risk_level": 2,
        "implementation_complexity": 3,
    }
    base.update(overrides)
    return base


def test_calculate_returns_dict_with_required_keys():
    calc = ProjectViabilityCalculator()
    result = calc.calculate_viability(_base_inputs())
    assert "viability_score" in result
    assert "monthly_savings" in result
    assert "priority" in result
    assert "recommendation" in result


def test_high_impact_low_effort_is_high_priority():
    calc = ProjectViabilityCalculator()
    inputs = _base_inputs(
        time_reduction_percent=90,
        risk_level=1,
        implementation_complexity=1,
    )
    result = calc.calculate_viability(inputs)
    assert result["viability_score"] >= 80


def test_viability_score_in_valid_range():
    calc = ProjectViabilityCalculator()
    result = calc.calculate_viability(_base_inputs())
    assert 0 <= result["viability_score"] <= 100


def test_calculate_viability_with_none_fields_does_not_crash():
    """If numeric fields are None (incomplete DB data), should return zeros instead of crash."""
    calculator = ProjectViabilityCalculator()
    project_data = {
        "current_time_per_task": None,
        "tasks_per_month": None,
        "staff_count": None,
        "time_reduction_percent": None,
        "avg_salary_per_hour": None,
        "development_hours": None,
        "development_cost_per_hour": None,
        "maintenance_monthly": None,
        "risk_level": None,
        "implementation_complexity": None,
    }
    result = calculator.calculate_viability(project_data)
    assert isinstance(result, dict), "Must return dict even when fields are None"
    assert "viability_score" in result
