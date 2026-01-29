"""Orchestrate MT5 sync steps for UI cycle."""

from datetime import datetime
from typing import Dict, Any

from ..utils.logger import get_logger
from ..config.settings import Config
from .mt5_sync import sync_open_positions, sync_deals_history
from ..analytics.drawdown import calculate_drawdown_for_deals

logger = get_logger()


def run_initial_sync(account: Dict[str, Any] = None) -> None:
    logger.info("sync_orchestrator: starting initial open positions sync")
    sync_open_positions(account=account)


def run_history_sync(from_date: datetime, to_date: datetime, account: Dict[str, Any] = None) -> None:
    logger.info(f"sync_orchestrator: syncing history {from_date} -> {to_date}")
    updated_closed = sync_deals_history(from_date=from_date, to_date=to_date, account=account)
    if Config.DRAWNDOWN_ENABLED and updated_closed:
        processed = calculate_drawdown_for_deals(updated_closed)
        logger.info(f"sync_orchestrator: drawdown calculated for {processed} deals")
