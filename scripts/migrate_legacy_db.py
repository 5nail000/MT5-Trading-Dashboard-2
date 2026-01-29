"""Migrate legacy sqlite data into SQLAlchemy schema."""

import sqlite3
import sys
from typing import Dict, Any

from src.utils.logger import get_logger
from src.db_sa.init_db import init_database
from src.db_sa.session import SessionLocal
from src.db_sa.models import Account, AccountInfo, Magic, MagicGroup, MagicGroupAssignment

logger = get_logger()

# Default legacy database path
DEFAULT_LEGACY_DB = "magics.db"


def _get_legacy_records(db_path: str) -> Dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account_id, account_title, leverage, server FROM account_settings")
        account_settings = cursor.fetchall()

        cursor.execute("SELECT account, magic, description FROM magic_descriptions")
        magic_descriptions = cursor.fetchall()

        cursor.execute("SELECT id, account_id, name FROM magic_groups")
        magic_groups = cursor.fetchall()

        cursor.execute("SELECT account_id, group_id, magic FROM magic_group_assignments")
        group_assignments = cursor.fetchall()

    return {
        "account_settings": account_settings,
        "magic_descriptions": magic_descriptions,
        "magic_groups": magic_groups,
        "group_assignments": group_assignments,
    }


def migrate_legacy_db(db_path: str = None) -> None:
    """
    Migrate data from legacy magics.db to new SQLAlchemy schema.
    
    Args:
        db_path: Path to legacy database file (default: magics.db)
    """
    legacy_path = db_path or DEFAULT_LEGACY_DB
    logger.info(f"Migrating legacy database: {legacy_path}")

    init_database()
    records = _get_legacy_records(legacy_path)

    with SessionLocal() as session:
        for account_id, account_title, leverage, server in records["account_settings"]:
            account = session.get(Account, account_id)
            if not account:
                account = Account(account_id=account_id, label=account_title)
                session.add(account)
            else:
                account.label = account_title or account.label

            info = session.get(AccountInfo, account_id)
            if not info:
                info = AccountInfo(
                    account_id=account_id,
                    account_number=str(account_id),
                    leverage=leverage,
                    server=server,
                )
                session.add(info)
            else:
                info.leverage = leverage or info.leverage
                info.server = server or info.server

        for account_id, magic, description in records["magic_descriptions"]:
            magic_entry = session.get(Magic, {"account_id": account_id, "id": magic})
            if not magic_entry:
                magic_entry = Magic(id=magic, account_id=account_id, label=description)
                session.add(magic_entry)
            else:
                magic_entry.label = description or magic_entry.label

        for group_id, account_id, name in records["magic_groups"]:
            group = session.get(MagicGroup, group_id)
            if not group:
                group = MagicGroup(id=group_id, account_id=account_id, name=name)
                session.add(group)
            else:
                group.name = name or group.name

        for account_id, group_id, magic in records["group_assignments"]:
            existing = session.get(
                MagicGroupAssignment,
                {"account_id": account_id, "group_id": group_id, "magic_id": magic},
            )
            if not existing:
                session.add(MagicGroupAssignment(account_id=account_id, group_id=group_id, magic_id=magic))

        session.commit()

    logger.info("Legacy migration completed")


if __name__ == "__main__":
    # Allow passing db path as command line argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    migrate_legacy_db(db_path)
