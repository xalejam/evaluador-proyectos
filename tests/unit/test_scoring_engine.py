from domain.scoring import calculate_scores, viability_component_scores
from domain.scoring.financials import compute_financials


def test_calculate_scores_weighted_average():
    answers = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 2, "G": 3, "H": 4}
    weights = {k: 1.0 for k in answers}
    impact, effort = calculate_scores(answers, weights)
    assert round(impact, 2) == 3.5
    assert round(effort, 2) == 2.5


def test_viability_component_scores_ranges():
    scores = viability_component_scores(time_reduction_percent=75, risk_level=2, complexity_level=2)
    assert scores["score_impact"] == 35.0
    assert scores["score_risk"] == 24.0
    assert scores["score_complexity"] == 28.0
    assert scores["score_total"] == 87.0


def test_compute_financials_positive_values():
    result = compute_financials(
        current_time_per_task=2.0,
        tasks_per_month=100,
        staff_count=2,
        avg_salary_per_hour=25.0,
        time_reduction_percent=50,
        development_hours=80,
        development_cost_per_hour=50,
        maintenance_monthly=100,
    )
    assert result["monthly_savings"] > 0
    assert result["annual_savings"] == result["monthly_savings"] * 12
    assert "payback_period_months" in result
