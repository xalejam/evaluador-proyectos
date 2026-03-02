"""Funciones financieras de apoyo para evaluacion."""

from __future__ import annotations


def compute_financials(
    current_time_per_task: float,
    tasks_per_month: int,
    staff_count: int,
    avg_salary_per_hour: float,
    time_reduction_percent: float,
    development_hours: float,
    development_cost_per_hour: float,
    maintenance_monthly: float,
) -> dict[str, float]:
    time_saved = current_time_per_task * (time_reduction_percent / 100.0)
    hours_saved_per_month = time_saved * tasks_per_month * staff_count
    monthly_savings = hours_saved_per_month * avg_salary_per_hour
    annual_savings = monthly_savings * 12
    initial_development_cost = development_hours * development_cost_per_hour
    net_annual_benefit = annual_savings - (maintenance_monthly * 12)

    payback_period_months = float("inf")
    if net_annual_benefit > 0:
        payback_period_months = initial_development_cost / (net_annual_benefit / 12)

    roi_first_year = 0.0
    if initial_development_cost > 0:
        roi_first_year = ((net_annual_benefit - initial_development_cost) / initial_development_cost) * 100

    return {
        "monthly_savings": monthly_savings,
        "annual_savings": annual_savings,
        "payback_period_months": payback_period_months,
        "roi_first_year": roi_first_year,
        "initial_development_cost": initial_development_cost,
        "hours_saved_per_month": hours_saved_per_month,
    }
