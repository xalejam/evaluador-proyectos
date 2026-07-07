"""Tests for financial calculations."""

import pytest

from domain.scoring.financials import compute_financials


def test_payback_is_none_when_no_benefit():
    """When net_annual_benefit <= 0, payback_period_months should be None, not float('inf')."""
    result = compute_financials(
        current_time_per_task=1.0,
        tasks_per_month=10,
        staff_count=1,
        avg_salary_per_hour=50,
        time_reduction_percent=0,
        development_hours=100,
        development_cost_per_hour=100,
        maintenance_monthly=1000,
    )
    assert result["payback_period_months"] is None, "payback debe ser None (no hay payback posible), no float('inf')"


def test_payback_is_none_when_maintenance_exceeds_savings():
    """When maintenance exceeds annual savings, payback_period_months should be None."""
    result = compute_financials(
        current_time_per_task=1.0,
        tasks_per_month=10,
        staff_count=1,
        avg_salary_per_hour=10,
        time_reduction_percent=10,
        development_hours=50,
        development_cost_per_hour=100,
        maintenance_monthly=5000,
    )
    assert result["payback_period_months"] is None


def test_payback_is_positive_number_when_profitable():
    """When there's positive net_annual_benefit, payback_period_months should be a positive number."""
    result = compute_financials(
        current_time_per_task=1.0,
        tasks_per_month=100,
        staff_count=1,
        avg_salary_per_hour=100,
        time_reduction_percent=50,
        development_hours=50,
        development_cost_per_hour=100,
        maintenance_monthly=100,
    )
    assert result["payback_period_months"] is not None
    assert result["payback_period_months"] > 0
    assert isinstance(result["payback_period_months"], (int, float))


@pytest.mark.parametrize("staff_count", [1, 5, 200])
def test_hours_saved_per_month_independent_of_staff_count(staff_count):
    """hours_saved_per_month no debe depender de staff_count.

    tasks_per_month ya representa el volumen total del proceso/equipo.
    Caso base HI-DDD-0002: 0.08h x 60 tareas x 85% = 4.08 h/mes.
    """
    result = compute_financials(
        current_time_per_task=0.08,
        tasks_per_month=60,
        staff_count=staff_count,
        avg_salary_per_hour=100,
        time_reduction_percent=85,
        development_hours=100,
        development_cost_per_hour=100,
        maintenance_monthly=0,
    )
    assert result["hours_saved_per_month"] == pytest.approx(4.08, rel=1e-6)


def test_hours_saved_hi_ddd_0002_regression():
    """Regresion explicita HI-DDD-0002: el valor correcto es 4.08, no 8.16."""
    result = compute_financials(
        current_time_per_task=0.08,
        tasks_per_month=60,
        staff_count=1,
        avg_salary_per_hour=100,
        time_reduction_percent=85,
        development_hours=100,
        development_cost_per_hour=100,
        maintenance_monthly=0,
    )
    assert result["hours_saved_per_month"] == pytest.approx(4.08, rel=1e-6)
    assert result["monthly_savings"] == pytest.approx(408.0, rel=1e-6)
    assert result["annual_savings"] == pytest.approx(4896.0, rel=1e-6)
