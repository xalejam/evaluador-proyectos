"""Repositorios para acceso a datos de Use Case Matrix."""

from datetime import datetime
import re

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from domain.models import Evaluation, MatrixPoint, Project
from infra.db import EvaluationORM, ProjectORM


class ProjectRepository:
    """Repositorio CRUD de proyectos."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def get(self, project_id: str) -> Project | None:
        with self.session_factory() as session:
            row = session.get(ProjectORM, project_id)
            return self._to_model(row) if row else None

    def list_all(self) -> list[Project]:
        with self.session_factory() as session:
            rows = session.scalars(select(ProjectORM).order_by(ProjectORM.updated_at.desc())).all()
            return [self._to_model(row) for row in rows]

    def exists(self, project_id: str) -> bool:
        with self.session_factory() as session:
            return session.get(ProjectORM, project_id) is not None

    def create(self, project_id: str, country: str, owner: str, name: str) -> Project:
        with self.session_factory() as session:
            now = datetime.utcnow()
            row = ProjectORM(
                project_id=project_id, country=country, owner=owner, name=name, created_at=now, updated_at=now
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_model(row)

    def update_metadata(self, project_id: str, country: str, owner: str, name: str) -> Project:
        with self.session_factory() as session:
            row = session.get(ProjectORM, project_id)
            if row is None:
                raise ValueError(f"Proyecto no encontrado: {project_id}")
            row.country = country
            row.owner = owner
            row.name = name
            row.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(row)
            return self._to_model(row)

    def next_project_id(
        self, country: str, owner: str, n_digits: int, id_format: str = "{country}-{owner}-{sequence}"
    ) -> str:
        """Genera siguiente consecutivo por combinacion (country, owner)."""
        with self.session_factory() as session:
            rows = session.scalars(
                select(ProjectORM.project_id).where(ProjectORM.country == country, ProjectORM.owner == owner)
            ).all()

        max_sequence = 0
        suffix_pattern = re.compile(rf"^{re.escape(country)}-{re.escape(owner)}-(\d{{{n_digits}}})$")
        for project_id in rows:
            match = suffix_pattern.match(project_id)
            if match:
                max_sequence = max(max_sequence, int(match.group(1)))

        next_value = max_sequence + 1
        return id_format.format(country=country, owner=owner, sequence=f"{next_value:0{n_digits}d}")

    @staticmethod
    def _to_model(row: ProjectORM) -> Project:
        return Project(
            project_id=row.project_id,
            country=row.country,
            owner=row.owner,
            name=row.name,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class EvaluationRepository:
    """Repositorio de evaluaciones con regla de current unica por proyecto."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def get_current(self, project_id: str) -> Evaluation | None:
        with self.session_factory() as session:
            row = session.scalars(
                select(EvaluationORM)
                .where(EvaluationORM.project_id == project_id, EvaluationORM.is_current.is_(True))
                .order_by(EvaluationORM.created_at.desc())
            ).first()
            return self._to_model(row) if row else None

    def save_current(
        self,
        project_id: str,
        answers: dict[str, int],
        weights: dict[str, float],
        impact_score: float,
        effort_score: float,
    ) -> Evaluation:
        with self.session_factory() as session:
            session.execute(
                update(EvaluationORM)
                .where(EvaluationORM.project_id == project_id, EvaluationORM.is_current.is_(True))
                .values(is_current=False)
            )
            row = EvaluationORM(
                project_id=project_id,
                answers_json=answers,
                weights_json=weights,
                impact_score=float(impact_score),
                effort_score=float(effort_score),
                is_current=True,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_model(row)

    def list_current_matrix_points(self) -> list[MatrixPoint]:
        with self.session_factory() as session:
            stmt = (
                select(ProjectORM.project_id, ProjectORM.name, EvaluationORM.impact_score, EvaluationORM.effort_score)
                .join(EvaluationORM, EvaluationORM.project_id == ProjectORM.project_id)
                .where(EvaluationORM.is_current.is_(True))
                .order_by(ProjectORM.project_id.asc())
            )
            rows = session.execute(stmt).all()

        return [
            MatrixPoint(
                project_id=row.project_id,
                project_name=row.name,
                impact_score=float(row.impact_score),
                effort_score=float(row.effort_score),
            )
            for row in rows
        ]

    @staticmethod
    def _to_model(row: EvaluationORM) -> Evaluation:
        return Evaluation(
            eval_id=row.eval_id,
            project_id=row.project_id,
            answers=dict(row.answers_json or {}),
            weights=dict(row.weights_json or {}),
            impact_score=float(row.impact_score),
            effort_score=float(row.effort_score),
            is_current=bool(row.is_current),
            created_at=row.created_at,
        )
