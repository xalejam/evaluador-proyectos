"""Motor de scoring de matriz y utilitarios de viabilidad."""

from __future__ import annotations

from typing import Iterable

IMPACT_CODES = ("A", "B", "C", "D")
EFFORT_CODES = ("E", "F", "G", "H")


def weighted_average(codes: Iterable[str], answers: dict[str, int], weights: dict[str, float]) -> float:
    numerator = 0.0
    denominator = 0.0
    for code in codes:
        score = float(answers[code])
        weight = float(weights[code])
        numerator += score * weight
        denominator += weight
    return 0.0 if denominator == 0 else numerator / denominator


def calculate_impact_score(answers: dict[str, int], weights: dict[str, float]) -> float:
    return weighted_average(IMPACT_CODES, answers, weights)


def calculate_effort_score(answers: dict[str, int], weights: dict[str, float]) -> float:
    return weighted_average(EFFORT_CODES, answers, weights)


def calculate_scores(answers: dict[str, int], weights: dict[str, float]) -> tuple[float, float]:
    return calculate_impact_score(answers, weights), calculate_effort_score(answers, weights)


def viability_component_scores(
    time_reduction_percent: float, risk_level: int, complexity_level: int
) -> dict[str, float]:
    if time_reduction_percent >= 70:
        impact = 35.0
    elif time_reduction_percent >= 50:
        impact = 30.0
    elif time_reduction_percent >= 30:
        impact = 25.0
    elif time_reduction_percent >= 15:
        impact = 20.0
    elif time_reduction_percent >= 5:
        impact = 15.0
    else:
        impact = max(0.0, time_reduction_percent * 0.5)

    risk = {1: 30.0, 2: 24.0, 3: 18.0, 4: 12.0, 5: 6.0}.get(int(risk_level), 6.0)
    complexity = {1: 35.0, 2: 28.0, 3: 21.0, 4: 14.0, 5: 7.0}.get(int(complexity_level), 7.0)

    return {
        "score_impact": impact,
        "score_risk": risk,
        "score_complexity": complexity,
        "score_total": impact + risk + complexity,
    }
