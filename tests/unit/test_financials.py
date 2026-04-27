"""Tests for financial calculations."""

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
    assert result["payback_period_months"] is None, \
        "payback debe ser None (no hay payback posible), no float('inf')"


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
