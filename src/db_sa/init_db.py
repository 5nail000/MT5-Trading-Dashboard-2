"""Database initialization for SQLAlchemy models."""

from sqlalchemy import text
from ..utils.logger import get_logger
from .engine import engine
from .models import Base

logger = get_logger()


def _ensure_deals_comment_column() -> None:
    try:
        with engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(deals)")).fetchall()
            columns = {row[1] for row in result}
            if "comment" not in columns:
                logger.info("init_database: adding deals.comment column")
                conn.execute(text("ALTER TABLE deals ADD COLUMN comment VARCHAR"))
    except Exception:
        logger.warning("init_database: failed to ensure deals.comment column", exc_info=True)


def _ensure_magic_groups_label2_column() -> None:
    try:
        with engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(magic_groups)")).fetchall()
            columns = {row[1] for row in result}
            if "label2" not in columns:
                logger.info("init_database: adding magic_groups.label2 column")
                conn.execute(text("ALTER TABLE magic_groups ADD COLUMN label2 VARCHAR"))
    except Exception:
        logger.warning("init_database: failed to ensure magic_groups.label2 column", exc_info=True)


def _ensure_magic_groups_color_columns() -> None:
    try:
        with engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(magic_groups)")).fetchall()
            columns = {row[1] for row in result}
            if "font_color" not in columns:
                logger.info("init_database: adding magic_groups.font_color column")
                conn.execute(text("ALTER TABLE magic_groups ADD COLUMN font_color VARCHAR"))
            if "fill_color" not in columns:
                logger.info("init_database: adding magic_groups.fill_color column")
                conn.execute(text("ALTER TABLE magic_groups ADD COLUMN fill_color VARCHAR"))
    except Exception:
        logger.warning("init_database: failed to ensure magic_groups color columns", exc_info=True)


def _ensure_accounts_history_start_date() -> None:
    try:
        with engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(accounts)")).fetchall()
            columns = {row[1] for row in result}
            if "history_start_date" not in columns:
                logger.info("init_database: adding accounts.history_start_date column")
                conn.execute(text("ALTER TABLE accounts ADD COLUMN history_start_date DATETIME"))
    except Exception:
        logger.warning("init_database: failed to ensure accounts.history_start_date", exc_info=True)


def init_database() -> None:
    logger.info("Initializing SQLAlchemy database schema")
    Base.metadata.create_all(bind=engine)
    _ensure_deals_comment_column()
    _ensure_magic_groups_label2_column()
    _ensure_magic_groups_color_columns()
    _ensure_accounts_history_start_date()