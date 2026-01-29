"""SQLAlchemy engine configuration."""

from pathlib import Path
from sqlalchemy import create_engine
from ..config.settings import Config


def _default_db_path() -> str:
    project_root = Path(__file__).resolve().parents[2]
    return str(project_root / "mt5_dashboard.db")


def get_database_url() -> str:
    return getattr(Config, "SQLALCHEMY_DATABASE_URL", None) or f"sqlite:///{_default_db_path()}"


engine = create_engine(
    get_database_url(),
    future=True,
    connect_args={"check_same_thread": False},
)
