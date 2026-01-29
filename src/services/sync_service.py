"""
Sync service for MT5 data synchronization.

Handles:
- Open positions synchronization
- Deals history synchronization
- Sync summaries
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from ..db_sa.session import SessionLocal
from ..db_sa.models import Account, Deal, Magic
from ..mt5.mt5_client import MT5Connection
from ..sync.mt5_sync import sync_open_positions, sync_deals_history
from ..analytics.drawdown import calculate_drawdown_for_deals
from ..config.settings import Config
from ..utils.logger import get_logger
from .account_service import AccountService

logger = get_logger()

# Thread pool for MT5 operations (MT5 API is not async-compatible)
_mt5_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mt5_sync_")


class SyncService:
    """Service for MT5 data synchronization operations."""
    
    @staticmethod
    def _get_active_account_sync():
        """Synchronous MT5 connection for thread pool."""
        try:
            connection = MT5Connection()
            if not connection.ensure_connected():
                return None
            return connection.get_account_info()
        except Exception:
            logger.error("MT5 connection failed", exc_info=True)
            return None
    
    @staticmethod
    async def get_active_account_async(timeout_seconds: float = 3.0):
        """
        Get active MT5 terminal account info asynchronously.
        
        Args:
            timeout_seconds: Timeout for MT5 connection
            
        Returns:
            Account info or None if not connected
        """
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(_mt5_executor, SyncService._get_active_account_sync),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning("MT5 connection timeout")
            return None
    
    @staticmethod
    def build_sync_summary(account_id: str, updated: List[Tuple[str, int]]) -> Dict[str, Any]:
        """
        Build summary of synced deals.
        
        Args:
            account_id: Account identifier
            updated: List of (account_id, ticket_id) tuples
            
        Returns:
            Summary dict with new_deals_total and new_deals_by_magic
        """
        ticket_ids = {ticket_id for acc_id, ticket_id in updated if acc_id == account_id}
        if not ticket_ids:
            return {"new_deals_total": 0, "new_deals_by_magic": []}

        with SessionLocal() as session:
            deals = (
                session.query(Deal.ticket_id, Deal.magic)
                .filter(Deal.account_id == account_id, Deal.ticket_id.in_(ticket_ids))
                .all()
            )
            magic_ids = {magic or 0 for _, magic in deals}
            labels = (
                session.query(Magic.id, Magic.label)
                .filter(Magic.account_id == account_id, Magic.id.in_(magic_ids))
                .all()
            )

        label_map = {magic_id: label for magic_id, label in labels}
        counts: Dict[int, int] = {}
        for _, magic in deals:
            magic_id = magic or 0
            counts[magic_id] = counts.get(magic_id, 0) + 1

        by_magic = [
            {
                "magic": magic_id,
                "label": label_map.get(magic_id) or f"Magic {magic_id}",
                "count": count,
            }
            for magic_id, count in counts.items()
        ]
        by_magic.sort(key=lambda item: item["count"], reverse=True)
        return {"new_deals_total": len(deals), "new_deals_by_magic": by_magic}
    
    @staticmethod
    async def sync_open_positions(
        account_id: Optional[str] = None,
        use_active: bool = False
    ) -> Dict[str, Any]:
        """
        Sync open positions from MT5.
        
        Args:
            account_id: Account to sync (optional if use_active=True)
            use_active: Use currently active terminal account
            
        Returns:
            Result dict with status and account_id
        """
        loop = asyncio.get_event_loop()
        
        if use_active or not account_id:
            info = await SyncService.get_active_account_async()
            if not info:
                return {"status": "error", "detail": "Active terminal account not found"}
            
            await loop.run_in_executor(_mt5_executor, sync_open_positions)
            logger.info(f"Open positions synced for active account {info.login}")
            return {"status": "ok", "account_id": str(info.login)}

        # Use stored credentials
        account = AccountService.get_credentials(account_id)
        if not account:
            return {"status": "needs_credentials"}

        initialized = await loop.run_in_executor(
            _mt5_executor, 
            lambda: MT5Connection().initialize(account)
        )
        if not initialized:
            return {"status": "needs_credentials"}

        await loop.run_in_executor(
            _mt5_executor, 
            lambda: sync_open_positions(account=account)
        )
        logger.info(f"Open positions synced for account {account_id}")
        return {"status": "ok", "account_id": account_id}
    
    @staticmethod
    async def sync_history(
        account_id: Optional[str] = None,
        use_active: bool = False,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sync deals history from MT5.
        
        Args:
            account_id: Account to sync (optional if use_active=True)
            use_active: Use currently active terminal account
            from_date: Start date for history (default: 30 days ago or account setting)
            to_date: End date for history (default: now)
            
        Returns:
            Result dict with status, account_id, and sync summary
        """
        loop = asyncio.get_event_loop()
        
        if use_active or not account_id:
            info = await SyncService.get_active_account_async()
            if not info:
                return {"status": "error", "detail": "Active terminal account not found"}
            
            active_account_id = str(info.login)
            
            # Get history start date from account settings
            if not from_date:
                from_date = AccountService.get_history_start_date(active_account_id)
            if not from_date:
                from_date = datetime.utcnow() - timedelta(days=30)
            if not to_date:
                to_date = datetime.utcnow()
            
            # Run sync in thread pool
            updated = await loop.run_in_executor(
                _mt5_executor,
                lambda: sync_deals_history(from_date, to_date + timedelta(days=1))
            )
            
            # Calculate drawdown if enabled
            if Config.DRAWNDOWN_ENABLED and updated:
                await loop.run_in_executor(
                    _mt5_executor, 
                    lambda: calculate_drawdown_for_deals(updated)
                )
            
            summary = SyncService.build_sync_summary(active_account_id, updated)
            logger.info(f"History synced for active account {active_account_id}: {summary['new_deals_total']} new deals")
            return {"status": "ok", "account_id": active_account_id, **summary}

        # Use stored credentials
        account = AccountService.get_credentials(account_id)
        if not account:
            return {"status": "needs_credentials"}

        initialized = await loop.run_in_executor(
            _mt5_executor,
            lambda: MT5Connection().initialize(account)
        )
        if not initialized:
            return {"status": "needs_credentials"}

        # Get history start date from account settings
        if not from_date:
            from_date = AccountService.get_history_start_date(account_id)
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=30)
        if not to_date:
            to_date = datetime.utcnow()
        
        updated = await loop.run_in_executor(
            _mt5_executor,
            lambda: sync_deals_history(from_date, to_date + timedelta(days=1), account=account)
        )
        
        if Config.DRAWNDOWN_ENABLED and updated:
            await loop.run_in_executor(
                _mt5_executor, 
                lambda: calculate_drawdown_for_deals(updated)
            )
        
        summary = SyncService.build_sync_summary(account_id, updated)
        logger.info(f"History synced for account {account_id}: {summary['new_deals_total']} new deals")
        return {"status": "ok", "account_id": account_id, **summary}
