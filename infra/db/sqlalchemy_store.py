"""Infraestructura de base de datos SQLite con SQLAlchemy."""

from pathlib import Path

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.sql import func


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "projects.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"


class Base(DeclarativeBase):
    """Base declarativa ORM."""


class ProjectORM(Base):
    """Tabla projects."""

    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    country: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    evaluations = relationship("EvaluationORM", back_populates="project", cascade="all, delete-orphan")


class EvaluationORM(Base):
    """Tabla evaluations."""

    __tablename__ = "evaluations"

    eval_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.project_id"), nullable=False, index=True)
    answers_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    weights_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    effort_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project = relationship("ProjectORM", back_populates="evaluations")


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Crea estructura de base de datos si no existe."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
