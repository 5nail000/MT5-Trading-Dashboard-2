"""Sync MT5 deals and positions into SQLAlchemy."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

import MetaTrader5 as mt5

from ..utils.logger import get_logger
from ..db_sa.session import SessionLocal
from ..db_sa.models import Account, AccountInfo, Deal, Position, Magic
from ..mt5.mt5_client import MT5DataProvider
logger = get_logger()


def _mt5_time_to_utc_dt(timestamp: Optional[float]) -> Optional[datetime]:
    if not timestamp:
        return None
    return datetime.utcfromtimestamp(timestamp)


def _direction_from_type(type_value: Optional[int]) -> Optional[str]:
    if type_value == 0:
        return "buy"
    if type_value == 1:
        return "sell"
    return None


def _resolve_magic(deal_events: List[Any]) -> int:
    for event in deal_events:
        magic = getattr(event, "magic", 0) or 0
        if magic != 0:
            return int(magic)
    return int(getattr(deal_events[0], "magic", 0) or 0)


def _clean_comment(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_comment(deal_events: List[Any], entry_event: Any, exit_event: Any) -> Optional[str]:
    entry_comment = _clean_comment(getattr(entry_event, "comment", None))
    exit_comment = _clean_comment(getattr(exit_event, "comment", None)) if exit_event else None

    if entry_comment and exit_comment:
        if entry_comment == exit_comment:
            return entry_comment
        return f"{entry_comment} | {exit_comment}"
    if entry_comment:
        return entry_comment
    if exit_comment:
        return exit_comment

    for event in reversed(deal_events):
        comment = _clean_comment(getattr(event, "comment", None))
        if comment:
            return comment
    return None


def _aggregate_deals(deals: List[Any]) -> List[Dict[str, Any]]:
    by_position: Dict[int, List[Any]] = {}
    for deal in deals:
        position_id = int(getattr(deal, "position_id", 0) or 0)
        if position_id == 0:
            position_id = int(getattr(deal, "ticket", 0) or 0)
        by_position.setdefault(position_id, []).append(deal)

    aggregated = []
    for position_id, events in by_position.items():
        events_sorted = sorted(events, key=lambda d: getattr(d, "time", 0))

        entry_events = [
            e
            for e in events_sorted
            if getattr(e, "entry", None) in {
                getattr(mt5, "DEAL_ENTRY_IN", 0),
                getattr(mt5, "DEAL_ENTRY_INOUT", 2),
            }
        ]
        exit_events = [
            e
            for e in events_sorted
            if getattr(e, "entry", None) in {
                getattr(mt5, "DEAL_ENTRY_OUT", 1),
                getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
                getattr(mt5, "DEAL_ENTRY_INOUT", 2),
            }
        ]

        entry_event = entry_events[0] if entry_events else events_sorted[0]
        exit_event = exit_events[-1] if exit_events else None

        ticket_id = int(getattr(exit_event, "ticket", 0) or getattr(entry_event, "ticket", 0) or 0)
        symbol = getattr(entry_event, "symbol", "") or getattr(exit_event, "symbol", "")

        profit_total = 0.0
        commission_total = 0.0
        swap_total = 0.0
        for event in events_sorted:
            profit_total += float(getattr(event, "profit", 0.0) or 0.0)
            commission_total += float(getattr(event, "commission", 0.0) or 0.0)
            swap_total += float(getattr(event, "swap", 0.0) or 0.0)

        aggregated.append(
            {
                "ticket_id": ticket_id,
                "position_id": position_id,
                "magic": _resolve_magic(events_sorted),
                "comment": _resolve_comment(events_sorted, entry_event, exit_event),
                "symbol": symbol,
                "direction": _direction_from_type(getattr(entry_event, "type", None)),
                "volume": float(getattr(entry_event, "volume", 0.0) or 0.0),
                "entry_time": _mt5_time_to_utc_dt(getattr(entry_event, "time", None)),
                "entry_price": float(getattr(entry_event, "price", 0.0) or 0.0),
                "exit_time": _mt5_time_to_utc_dt(getattr(exit_event, "time", None)) if exit_event else None,
                "exit_price": float(getattr(exit_event, "price", 0.0) or 0.0) if exit_event else None,
                "profit": profit_total + commission_total + swap_total,
                "commission": commission_total,
                "swap": swap_total,
                "is_closed": exit_event is not None,
            }
        )

    return aggregated


def _ensure_account(session, account_info) -> str:
    account_id = str(account_info.login)
    account = session.get(Account, account_id)
    if not account:
        account = Account(account_id=account_id)
        session.add(account)

    info = session.get(AccountInfo, account_id)
    if not info:
        info = AccountInfo(
            account_id=account_id,
            account_number=str(account_info.login),
            leverage=getattr(account_info, "leverage", None),
            server=getattr(account_info, "server", None),
            currency=getattr(account_info, "currency", None),
            balance=getattr(account_info, "balance", None),
            equity=getattr(account_info, "equity", None),
        )
        session.add(info)
    else:
        info.leverage = getattr(account_info, "leverage", info.leverage)
        info.server = getattr(account_info, "server", info.server)
        info.currency = getattr(account_info, "currency", info.currency)
        info.balance = getattr(account_info, "balance", info.balance)
        info.equity = getattr(account_info, "equity", info.equity)

    return account_id


def sync_open_positions(account: Dict[str, Any] = None) -> None:
    provider = MT5DataProvider()
    positions, account_info = provider.get_open_positions(account)
    if positions is None or account_info is None:
        logger.warning("sync_open_positions: no positions or account info")
        return

    with SessionLocal() as session:
        account_id = _ensure_account(session, account_info)
        active_ids = set()

        for pos in positions:
            position_id = int(getattr(pos, "ticket", 0) or 0)
            active_ids.add(position_id)

            direction = _direction_from_type(getattr(pos, "type", None))
            entry_time = _mt5_time_to_utc_dt(getattr(pos, "time", None))

            entry = session.get(Position, {"account_id": account_id, "position_id": position_id})
            if not entry:
                entry = Position(
                    account_id=account_id,
                    position_id=position_id,
                    magic=int(getattr(pos, "magic", 0) or 0),
                    symbol=getattr(pos, "symbol", ""),
                    direction=direction,
                    volume=float(getattr(pos, "volume", 0.0) or 0.0),
                    entry_time=entry_time,
                    entry_price=float(getattr(pos, "price_open", 0.0) or 0.0),
                    current_price=float(getattr(pos, "price_current", 0.0) or 0.0),
                    profit=float(getattr(pos, "profit", 0.0) or 0.0),
                    swap=float(getattr(pos, "swap", 0.0) or 0.0),
                    is_open=True,
                )
                session.add(entry)
            else:
                entry.direction = direction
                entry.volume = float(getattr(pos, "volume", entry.volume or 0.0) or 0.0)
                entry.current_price = float(getattr(pos, "price_current", entry.current_price or 0.0) or 0.0)
                entry.profit = float(getattr(pos, "profit", entry.profit or 0.0) or 0.0)
                entry.swap = float(getattr(pos, "swap", entry.swap or 0.0) or 0.0)
                entry.is_open = True

        existing_positions = (
            session.query(Position)
            .filter(Position.account_id == account_id, Position.is_open.is_(True))
            .all()
        )
        for existing in existing_positions:
            if existing.position_id not in active_ids:
                existing.is_open = False

        session.commit()

    logger.info(f"sync_open_positions: synced {len(positions)} positions for account {account_info.login}")


def sync_deals_history(
    from_date: datetime,
    to_date: datetime,
    account: Dict[str, Any] = None,
) -> List[Tuple[str, int]]:
    provider = MT5DataProvider()
    deals, account_info = provider.get_history(account, from_date, to_date)
    if deals is None or account_info is None:
        logger.warning("sync_deals_history: no deals or account info")
        return []

    aggregated = _aggregate_deals(list(deals))

    updated_closed: List[Tuple[str, int]] = []

    with SessionLocal() as session:
        account_id = _ensure_account(session, account_info)
        seen_magics = set()
        for item in aggregated:
            if not item["ticket_id"]:
                logger.debug("sync_deals_history: skipped deal without ticket_id")
                continue

            deal = session.get(Deal, {"account_id": account_id, "ticket_id": item["ticket_id"]})
            was_closed = bool(deal.is_closed) if deal else False
            magic_id = item["magic"]
            if not magic_id:
                if deal and deal.magic:
                    magic_id = deal.magic
                elif item["position_id"]:
                    position = session.get(
                        Position,
                        {"account_id": account_id, "position_id": item["position_id"]},
                    )
                    if position and position.magic:
                        magic_id = position.magic
                if magic_id is None:
                    magic_id = 0
            if not deal:
                deal_data = dict(item)
                deal_data["magic"] = magic_id
                deal = Deal(account_id=account_id, **deal_data)
                session.add(deal)
            else:
                deal.position_id = item["position_id"]
                if magic_id != 0 or not deal.magic:
                    deal.magic = magic_id
                deal.symbol = item["symbol"]
                deal.direction = item["direction"]
                deal.volume = item["volume"]
                deal.entry_time = item["entry_time"]
                deal.entry_price = item["entry_price"]
                deal.exit_time = item["exit_time"]
                deal.exit_price = item["exit_price"]
                deal.profit = item["profit"]
                deal.commission = item["commission"]
                deal.swap = item["swap"]
                deal.comment = item.get("comment")
                deal.is_closed = item["is_closed"]

            if magic_id is not None and magic_id != 0 and magic_id not in seen_magics:
                seen_magics.add(magic_id)
                magic_entry = session.get(Magic, {"account_id": account_id, "id": magic_id})
                if not magic_entry:
                    session.add(Magic(id=magic_id, account_id=account_id))

            if item["is_closed"] and (not was_closed):
                updated_closed.append((account_id, item["ticket_id"]))

        session.commit()

    logger.info(f"sync_deals_history: synced {len(aggregated)} deals for account {account_info.login}")
    return updated_closed
