"""Modelos de dominio para Use Case Matrix."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Project:
    """Proyecto base para la matriz."""

    project_id: str
    country: str
    owner: str
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Evaluation:
    """Evaluacion de criterios A-H para un proyecto."""

    eval_id: int
    project_id: str
    answers: dict[str, int]
    weights: dict[str, float]
    impact_score: float
    effort_score: float
    is_current: bool
    created_at: datetime


@dataclass(frozen=True)
class MatrixPoint:
    """Punto renderizable en la matriz (vista de evaluaciones current)."""

    project_id: str
    project_name: str
    impact_score: float
    effort_score: float
    quadrant: Optional[str] = None
