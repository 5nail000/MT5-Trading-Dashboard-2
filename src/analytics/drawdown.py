"""Max drawdown calculation for closed deals."""

from datetime import timedelta
from typing import Optional, Iterable, Tuple

import MetaTrader5 as mt5

from ..utils.logger import get_logger
from ..db_sa.session import SessionLocal
from ..db_sa.models import Deal, DealDrawdown, AccountInfo
from ..mt5.tick_data import MT5TickProvider
from ..mt5.mt5_client import MT5Connection
from ..config.settings import Config

logger = get_logger()


def _to_local_time(dt):
    return dt + timedelta(hours=Config.LOCAL_TIMESHIFT)


def _get_point_and_tick_value(symbol: str) -> Tuple[float, Optional[float], Optional[float]]:
    connection = MT5Connection()
    if not connection.ensure_connected():
        return 1.0, None, None

    info = mt5.symbol_info(symbol)
    if not info:
        return 1.0, None, None
    point = float(getattr(info, "point", 1.0) or 1.0)
    tick_size = float(getattr(info, "trade_tick_size", 0.0) or 0.0)
    tick_value = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
    return point, tick_size if tick_size > 0 else None, tick_value if tick_value > 0 else None


def _calculate_drawdown_prices(direction: str, entry_price: float, ticks) -> Optional[float]:
    if direction == "buy":
        min_bid = min((t["bid"] for t in ticks), default=None)
        if min_bid is None:
            return None
        return min_bid - entry_price
    if direction == "sell":
        max_ask = max((t["ask"] for t in ticks), default=None)
        if max_ask is None:
            return None
        return entry_price - max_ask
    return None


def calculate_drawdown_for_deal(account_id: str, ticket_id: int) -> bool:
    with SessionLocal() as session:
        deal = session.get(Deal, {"account_id": account_id, "ticket_id": ticket_id})
        if not deal or not deal.is_closed:
            logger.debug("drawdown: deal not found or not closed")
            return False

        if not deal.entry_time or not deal.exit_time:
            logger.warning("drawdown: missing entry/exit time")
            return False

        account_info = session.get(AccountInfo, account_id)
        server = account_info.server if account_info else None

    provider = MT5TickProvider()
    ticks = provider.get_ticks_from_db(
        deal.symbol,
        _to_local_time(deal.entry_time),
        _to_local_time(deal.exit_time),
        server=server,
    )

    if not ticks:
        logger.warning(f"drawdown: no ticks for {deal.symbol} {ticket_id}")
        return False

    dd_price = _calculate_drawdown_prices(deal.direction, deal.entry_price or 0.0, ticks)
    if dd_price is None:
        logger.warning("drawdown: unable to compute drawdown price")
        return False

    point, tick_size, tick_value = _get_point_and_tick_value(deal.symbol)
    drawdown_points = dd_price / point if point else dd_price

    if tick_size and tick_value:
        drawdown_currency = (dd_price / tick_size) * tick_value * (deal.volume or 0.0)
    else:
        drawdown_currency = dd_price * (deal.volume or 0.0)

    with SessionLocal() as session:
        existing = session.get(DealDrawdown, {"account_id": account_id, "ticket_id": ticket_id})
        if not existing:
            session.add(
                DealDrawdown(
                    account_id=account_id,
                    ticket_id=ticket_id,
                    max_drawdown_points=drawdown_points,
                    max_drawdown_currency=drawdown_currency,
                )
            )
        else:
            existing.max_drawdown_points = drawdown_points
            existing.max_drawdown_currency = drawdown_currency
        session.commit()

    logger.info(f"drawdown: calculated for deal {ticket_id} on account {account_id}")
    return True


def calculate_drawdown_for_deals(deal_keys: Iterable[Tuple[str, int]]) -> int:
    processed = 0
    for account_id, ticket_id in deal_keys:
        if calculate_drawdown_for_deal(account_id, ticket_id):
            processed += 1
    return processed
