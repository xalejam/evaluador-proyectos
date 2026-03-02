"""Umbrales y recomendaciones para viabilidad."""

from __future__ import annotations


def score_to_priority(score: float) -> str:
    if score >= 80:
        return "Alta"
    if score >= 60:
        return "Media-Alta"
    if score >= 40:
        return "Media"
    return "Baja"


def score_to_recommendation(score: float) -> str:
    if score >= 80:
        return "Proyecto altamente factible. Excelente impacto y baja complejidad."
    if score >= 60:
        return "Proyecto factible. Buen impacto con riesgo controlado."
    if score >= 40:
        return "Proyecto marginal. Evaluar simplificacion antes de proceder."
    return "Proyecto no recomendado. Alto riesgo o complejidad excesiva."
