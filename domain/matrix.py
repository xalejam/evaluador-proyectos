"""Clasificacion de cuadrantes para Use Case Matrix."""


def classify_quadrant(impact_score: float, effort_score: float, threshold_impact: float, threshold_effort: float) -> str:
    """Clasifica un caso en cuadrantes con umbrales fijos."""
    high_impact = impact_score >= threshold_impact
    high_effort = effort_score >= threshold_effort

    if high_impact and not high_effort:
        return "Quick Wins"
    if high_impact and high_effort:
        return "Strategic Bets"
    if not high_impact and not high_effort:
        return "Tactical Improvements"
    return "Future Consideration"
