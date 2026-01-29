"""FastAPI service for MT5 Trading Dashboard."""

import os
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..utils.logger import get_logger
from ..db_sa.init_db import init_database
from ..config.settings import Config
from ..readmodels.dashboard_queries import (
    get_period_aggregates,
    get_open_positions_summary,
    get_deals,
)
from ..security.ip_filter import IPFilterMiddleware
from ..services import AccountService, SyncService, GroupService

logger = get_logger()

app = FastAPI(title="MT5 Trading Dashboard API")

# CORS configuration from environment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IP whitelist middleware
app.add_middleware(IPFilterMiddleware)


@app.on_event("startup")
def _startup_init_db() -> None:
    """Initialize database and validate configuration on startup."""
    logger.info("Starting MT5 Trading Dashboard API...")
    
    init_database()
    logger.info("Database initialized")
    
    logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")
    
    if not Config.MT5_CRED_KEY:
        logger.warning("MT5_CRED_KEY not configured - credential encryption disabled")
    else:
        logger.info("MT5 credential encryption enabled")
    
    if Config.DRAWNDOWN_ENABLED:
        logger.info("Drawdown calculation enabled (requires tick data)")
    
    logger.info("API startup complete")


# ============== Request Models ==============

class SyncRequest(BaseModel):
    account_id: Optional[str] = None
    use_active: bool = False


class HistorySyncRequest(BaseModel):
    account_id: Optional[str] = None
    use_active: bool = False
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class CredentialsRequest(BaseModel):
    login: str
    server: str
    password: str


class LabelRequest(BaseModel):
    label: str


class HistoryStartRequest(BaseModel):
    history_start_date: Optional[datetime] = None


class MagicLabelItem(BaseModel):
    magic: int
    label: str


class MagicLabelsRequest(BaseModel):
    account_id: str
    labels: List[MagicLabelItem]


class GroupCreateRequest(BaseModel):
    account_id: str
    name: str
    label2: Optional[str] = None
    font_color: Optional[str] = None
    fill_color: Optional[str] = None


class GroupRenameRequest(BaseModel):
    name: Optional[str] = None
    label2: Optional[str] = None
    font_color: Optional[str] = None
    fill_color: Optional[str] = None


class GroupAssignmentsRequest(BaseModel):
    account_id: str
    magic_ids: List[int]


# ============== Health & Accounts ==============

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/accounts")
def list_accounts():
    """List all accounts with their info."""
    return AccountService.list_accounts()


@app.get("/terminal/active")
async def terminal_active_account():
    """Get active MT5 terminal account."""
    info = await SyncService.get_active_account_async()
    if not info:
        return {"active": False}
    return {
        "active": True,
        "account_id": str(info.login),
        "server": getattr(info, "server", None),
    }


@app.post("/accounts/{account_id}/credentials")
def save_credentials(account_id: str, payload: CredentialsRequest):
    """Save encrypted credentials for an account."""
    success = AccountService.save_credentials(
        account_id=account_id,
        login=payload.login,
        server=payload.server,
        password=payload.password
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save credentials")
    return {"status": "ok"}


@app.post("/accounts/{account_id}/label")
def update_account_label(account_id: str, payload: LabelRequest):
    """Update account label."""
    success = AccountService.update_label(account_id, payload.label)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "ok"}


@app.post("/accounts/{account_id}/history-start")
def update_history_start(account_id: str, payload: HistoryStartRequest):
    """Update account history start date."""
    success = AccountService.update_history_start(account_id, payload.history_start_date)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "ok"}


# ============== Magics & Groups ==============

@app.get("/magics")
def list_magics(account_id: str):
    """List all magics with group assignments."""
    return GroupService.list_magics(account_id)


@app.post("/magics/labels")
def update_magic_labels(payload: MagicLabelsRequest):
    """Update labels for multiple magic numbers."""
    labels = [{"magic": item.magic, "label": item.label} for item in payload.labels]
    GroupService.update_magic_labels(payload.account_id, labels)
    return {"status": "ok"}


@app.get("/groups")
def list_groups(account_id: str):
    """List all groups for an account."""
    return GroupService.list_groups(account_id)


@app.post("/groups")
def create_group(payload: GroupCreateRequest):
    """Create a new magic group."""
    return GroupService.create_group(
        account_id=payload.account_id,
        name=payload.name,
        label2=payload.label2,
        font_color=payload.font_color,
        fill_color=payload.fill_color,
    )


@app.put("/groups/{group_id}")
def rename_group(group_id: int, payload: GroupRenameRequest):
    """Update a magic group."""
    success = GroupService.update_group(
        group_id=group_id,
        name=payload.name,
        label2=payload.label2,
        font_color=payload.font_color,
        fill_color=payload.fill_color,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"status": "ok"}


@app.delete("/groups/{group_id}")
def delete_group(group_id: int, account_id: str):
    """Delete a magic group."""
    GroupService.delete_group(account_id, group_id)
    return {"status": "ok"}


@app.post("/groups/{group_id}/assignments")
def update_group_assignments(group_id: int, payload: GroupAssignmentsRequest):
    """Update magic assignments for a group."""
    GroupService.update_group_assignments(
        account_id=payload.account_id,
        group_id=group_id,
        magic_ids=payload.magic_ids
    )
    return {"status": "ok"}


# ============== Data Queries ==============

@app.get("/open-positions")
def open_positions(account_id: str):
    """Get open positions summary."""
    return get_open_positions_summary(account_id)


@app.get("/aggregates")
def aggregates(account_id: str, from_date: datetime, to_date: datetime):
    """Get period aggregates."""
    return get_period_aggregates(account_id, from_date, to_date)


@app.get("/deals")
def deals(account_id: str, from_date: datetime, to_date: datetime):
    """Get deals for a period."""
    return get_deals(account_id, from_date, to_date)


# ============== Sync Operations ==============

@app.post("/sync/open")
async def sync_open(payload: SyncRequest):
    """Sync open positions from MT5."""
    result = await SyncService.sync_open_positions(
        account_id=payload.account_id,
        use_active=payload.use_active
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("detail"))
    
    return result


@app.post("/sync/history")
async def sync_history(payload: HistorySyncRequest):
    """Sync deals history from MT5."""
    result = await SyncService.sync_history(
        account_id=payload.account_id,
        use_active=payload.use_active,
        from_date=payload.from_date,
        to_date=payload.to_date,
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("detail"))
    
    return result
