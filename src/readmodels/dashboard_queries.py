"""Aggregated queries for dashboard UI."""

from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy import func

from ..db_sa.session import SessionLocal
from ..db_sa.models import Deal, DealDrawdown, MagicGroupAssignment, MagicGroup, Position, AccountInfo, Magic


def get_period_aggregates(account_id: str, from_dt: datetime, to_dt: datetime) -> Dict[str, Any]:
    with SessionLocal() as session:
        total_profit = session.query(func.coalesce(func.sum(Deal.profit), 0.0)).filter(
            Deal.account_id == account_id,
            Deal.is_closed.is_(True),
            Deal.exit_time >= from_dt,
            Deal.exit_time <= to_dt,
        ).scalar()

        magic_expr = func.coalesce(Deal.magic, 0)
        by_magic = (
            session.query(magic_expr, func.coalesce(func.sum(Deal.profit), 0.0))
            .filter(
                Deal.account_id == account_id,
                Deal.is_closed.is_(True),
                Deal.exit_time >= from_dt,
                Deal.exit_time <= to_dt,
            )
            .group_by(magic_expr)
            .all()
        )

        by_group = (
            session.query(
                MagicGroup.id,
                func.coalesce(func.sum(Deal.profit), 0.0),
            )
            .join(
                MagicGroupAssignment,
                (MagicGroupAssignment.group_id == MagicGroup.id)
                & (MagicGroupAssignment.account_id == account_id),
            )
            .join(
                Deal,
                (Deal.magic == MagicGroupAssignment.magic_id)
                & (Deal.account_id == account_id),
            )
            .filter(
                Deal.is_closed.is_(True),
                Deal.exit_time >= from_dt,
                Deal.exit_time <= to_dt,
            )
            .group_by(MagicGroup.id)
            .all()
        )

        balance = session.query(AccountInfo.balance).filter(AccountInfo.account_id == account_id).scalar() or 0.0
        period_percent = (total_profit / balance * 100.0) if balance else 0.0

    return {
        "period_profit": total_profit or 0.0,
        "period_percent": period_percent,
        "by_magic": [{"magic": magic, "profit": profit} for magic, profit in by_magic],
        "by_group": [{"group_id": group_id, "profit": profit} for group_id, profit in by_group],
    }


def get_open_positions_summary(account_id: str) -> Dict[str, Any]:
    with SessionLocal() as session:
        positions = (
            session.query(Position)
            .filter(Position.account_id == account_id, Position.is_open.is_(True))
            .all()
        )

        balance = session.query(AccountInfo.balance).filter(AccountInfo.account_id == account_id).scalar() or 0.0

        by_magic: Dict[int, float] = {}
        for pos in positions:
            magic = pos.magic or 0
            by_magic[magic] = by_magic.get(magic, 0.0) + float(pos.profit or 0.0)

        floating_total = sum(by_magic.values())
        floating_percent = (floating_total / balance * 100.0) if balance else 0.0

        return {
            "account_id": account_id,
            "balance": balance,
            "floating_total": floating_total,
            "floating_percent": floating_percent,
            "by_magic": [
                {
                    "magic": magic,
                    "floating": floating,
                    "percent": (floating / balance * 100.0) if balance else 0.0,
                }
                for magic, floating in by_magic.items()
            ],
        }


def get_magics_with_groups(account_id: str) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        magics = session.query(Magic).filter(Magic.account_id == account_id).all()
        deal_magics = (
            session.query(func.coalesce(Deal.magic, 0))
            .filter(Deal.account_id == account_id)
            .distinct()
            .all()
        )
        position_magics = (
            session.query(func.coalesce(Position.magic, 0))
            .filter(Position.account_id == account_id)
            .distinct()
            .all()
        )
        assignments = (
            session.query(MagicGroupAssignment)
            .filter(MagicGroupAssignment.account_id == account_id)
            .all()
        )

    group_map: Dict[int, List[int]] = {}
    for assignment in assignments:
        group_map.setdefault(assignment.magic_id, []).append(assignment.group_id)

    entries: List[Dict[str, Any]] = []
    existing_ids = set()
    for magic in magics:
        existing_ids.add(magic.id)
        entries.append(
            {
                "account_id": magic.account_id,
                "magic": magic.id,
                "label": magic.label or f"Magic {magic.id}",
                "description": "",
                "group_ids": group_map.get(magic.id, []),
            }
        )

    extra_ids = {row[0] for row in deal_magics + position_magics}
    for magic_id in sorted(extra_ids):
        if magic_id in existing_ids:
            continue
        entries.append(
            {
                "account_id": account_id,
                "magic": magic_id,
                "label": f"Magic {magic_id}",
                "description": "",
                "group_ids": group_map.get(magic_id, []),
            }
        )

    return entries


def get_groups(account_id: str) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        groups = session.query(MagicGroup).filter(MagicGroup.account_id == account_id).all()
    return [
        {
            "group_id": g.id,
            "account_id": g.account_id,
            "name": g.name,
            "label2": g.label2,
            "font_color": g.font_color,
            "fill_color": g.fill_color,
        }
        for g in groups
    ]


def get_deals(account_id: str, from_dt: datetime, to_dt: datetime) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = (
            session.query(Deal, DealDrawdown)
            .outerjoin(
                DealDrawdown,
                (DealDrawdown.account_id == Deal.account_id)
                & (DealDrawdown.ticket_id == Deal.ticket_id),
            )
            .filter(
                Deal.account_id == account_id,
                Deal.is_closed.is_(True),
                Deal.exit_time.isnot(None),
                Deal.exit_time >= from_dt,
                Deal.exit_time <= to_dt,
            )
            .all()
        )

    result = []
    for deal, drawdown in rows:
        result.append(
            {
                "position_id": deal.position_id,
                "account_id": deal.account_id,
                "magic": deal.magic or 0,
                "symbol": deal.symbol,
                "direction": deal.direction or "buy",
                "volume": deal.volume or 0.0,
                "entry_time": deal.entry_time.isoformat() if deal.entry_time else None,
                "entry_price": deal.entry_price,
                "exit_time": deal.exit_time.isoformat() if deal.exit_time else None,
                "exit_price": deal.exit_price,
                "profit": deal.profit or 0.0,
                "comment": deal.comment,
                "max_drawdown_points": drawdown.max_drawdown_points if drawdown else None,
                "max_drawdown_currency": drawdown.max_drawdown_currency if drawdown else None,
                "status": "closed" if deal.is_closed else "open",
            }
        )
    return result
