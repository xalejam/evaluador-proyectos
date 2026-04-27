"""Pure calculation logic for project viability — no Streamlit or Excel dependencies."""
from __future__ import annotations


def _t(key: str) -> str:
    try:
        from ui.tabs.shared import t  # type: ignore[import]
        return t(key)
    except Exception:
        return key


class ProjectViabilityCalculator:
    """Calculates project viability score and financial projections."""

    def calculate_viability(self, project_data: dict) -> dict:
        total_hours_per_month = (
            project_data["current_time_per_task"]
            * project_data["tasks_per_month"]
            * project_data["staff_count"]
        )
        time_saved = (
            project_data["current_time_per_task"]
            * project_data["time_reduction_percent"]
            / 100
        )
        hours_saved_per_month = (
            time_saved
            * project_data["tasks_per_month"]
            * project_data["staff_count"]
        )
        monthly_savings = hours_saved_per_month * project_data["avg_salary_per_hour"]
        annual_savings = monthly_savings * 12
        initial_development_cost = (
            project_data["development_hours"] * project_data["development_cost_per_hour"]
        )
        annual_maintenance_cost = project_data["maintenance_monthly"] * 12
        net_annual_benefit = annual_savings - annual_maintenance_cost

        if net_annual_benefit > 0:
            payback_period_months = initial_development_cost / (net_annual_benefit / 12)
        else:
            payback_period_months = None

        if initial_development_cost > 0:
            roi_first_year = (
                (net_annual_benefit - initial_development_cost) / initial_development_cost
            ) * 100
        else:
            roi_first_year = 0

        viability_score = 0

        time_reduction = project_data["time_reduction_percent"]
        if time_reduction >= 70:
            viability_score += 35
        elif time_reduction >= 50:
            viability_score += 30
        elif time_reduction >= 30:
            viability_score += 25
        elif time_reduction >= 15:
            viability_score += 20
        elif time_reduction >= 5:
            viability_score += 15
        else:
            viability_score += max(0, time_reduction * 0.5)

        risk_level = project_data["risk_level"]
        risk_points = {1: 30, 2: 24, 3: 18, 4: 12, 5: 6}
        viability_score += risk_points.get(risk_level, 6)

        complexity_level = project_data["implementation_complexity"]
        complexity_points = {1: 35, 2: 28, 3: 21, 4: 14, 5: 7}
        viability_score += complexity_points.get(complexity_level, 7)

        if viability_score >= 80:
            recommendation = _t("recommendation_80_100")
            priority = _t("priority_high")
        elif viability_score >= 60:
            recommendation = _t("recommendation_60_79")
            priority = _t("priority_medium_high")
        elif viability_score >= 40:
            recommendation = _t("recommendation_40_59")
            priority = _t("priority_medium")
        else:
            recommendation = _t("recommendation_0_39")
            priority = _t("priority_low")

        return {
            "monthly_savings": monthly_savings,
            "annual_savings": annual_savings,
            "payback_period_months": payback_period_months,
            "roi_first_year": roi_first_year,
            "initial_development_cost": initial_development_cost,
            "hours_saved_per_month": hours_saved_per_month,
            "viability_score": round(viability_score),
            "recommendation": recommendation,
            "priority": priority,
        }

    def calculate_tracking_results(self, project_data: dict, tracking_data: dict) -> dict:
        expected_time_after = project_data["current_time_per_task"] * (
            1 - project_data["time_reduction_percent"] / 100
        )
        expected_savings_per_task = project_data["current_time_per_task"] - expected_time_after
        actual_savings_per_task = (
            project_data["current_time_per_task"] - tracking_data["actual_time_per_task"]
        )

        if expected_savings_per_task > 0:
            efficiency_ratio = actual_savings_per_task / expected_savings_per_task
        else:
            efficiency_ratio = 0

        if project_data["current_time_per_task"] > 0:
            actual_time_reduction_percent = (
                (project_data["current_time_per_task"] - tracking_data["actual_time_per_task"])
                / project_data["current_time_per_task"]
            ) * 100
        else:
            actual_time_reduction_percent = 0

        actual_monthly_savings = (
            actual_savings_per_task
            * tracking_data["actual_tasks_per_month"]
            * project_data["staff_count"]
            * project_data["avg_salary_per_hour"]
        )
        actual_annual_savings = actual_monthly_savings * 12

        if efficiency_ratio >= 1.2:
            performance_score = 100
        elif efficiency_ratio >= 1:
            performance_score = 90
        elif efficiency_ratio >= 0.8:
            performance_score = 75
        elif efficiency_ratio >= 0.6:
            performance_score = 60
        elif efficiency_ratio >= 0.4:
            performance_score = 40
        else:
            performance_score = 20

        adoption_adjustment = (tracking_data["adoption_rate"] / 100) * 0.3
        satisfaction_adjustment = (tracking_data["user_satisfaction_score"] / 10) * 0.2
        performance_score = min(
            100, performance_score * (1 + adoption_adjustment + satisfaction_adjustment)
        )

        return {
            "efficiency_ratio": round(efficiency_ratio, 2),
            "actual_time_reduction_percent": round(actual_time_reduction_percent),
            "actual_monthly_savings": actual_monthly_savings,
            "actual_annual_savings": actual_annual_savings,
            "performance_score": round(performance_score),
        }
