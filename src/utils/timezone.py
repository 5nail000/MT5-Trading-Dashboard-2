"""
Timezone utilities for MT5 Trading Dashboard.

Provides consistent time handling across the application:
- UTC for storage and MT5 API
- Local time (UTC+LOCAL_TIMESHIFT) for display
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from ..config.settings import Config
from .logger import get_logger

logger = get_logger()


def utc_now() -> datetime:
    """
    Get current time in UTC with timezone info.
    
    Returns:
        datetime: Current UTC time with tzinfo
    """
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    """
    Get current time in local timezone (UTC+LOCAL_TIMESHIFT).
    
    Returns:
        datetime: Current local time (naive, without tzinfo)
    """
    return datetime.now()


def to_mt5_server_time(dt: datetime) -> datetime:
    """
    Convert local time to MT5 server time (UTC).
    
    MT5 API expects times in UTC. This function converts local time
    (which is UTC+LOCAL_TIMESHIFT) to UTC.
    
    Args:
        dt: Local datetime (naive or with tzinfo)
        
    Returns:
        datetime: UTC datetime for MT5 API (naive, without tzinfo)
    """
    if dt.tzinfo is not None:
        # If timezone aware, convert to UTC
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.replace(tzinfo=None)
    else:
        # If naive, assume it's local time and subtract LOCAL_TIMESHIFT
        return dt - timedelta(hours=Config.LOCAL_TIMESHIFT)


def from_mt5_server_time(dt: datetime) -> datetime:
    """
    Convert MT5 server time (UTC) to local time.
    
    MT5 API returns times in UTC. This function converts UTC
    to local time (UTC+LOCAL_TIMESHIFT).
    
    Args:
        dt: UTC datetime from MT5 (naive or with tzinfo)
        
    Returns:
        datetime: Local datetime (naive, without tzinfo)
    """
    if dt.tzinfo is not None:
        # If timezone aware, convert to UTC first, then add LOCAL_TIMESHIFT
        dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt_utc + timedelta(hours=Config.LOCAL_TIMESHIFT)
    else:
        # If naive, assume it's UTC and add LOCAL_TIMESHIFT
        return dt + timedelta(hours=Config.LOCAL_TIMESHIFT)


def timestamp_to_local(timestamp: int) -> datetime:
    """
    Convert Unix timestamp (UTC) to local datetime.
    
    MT5 deal times are Unix timestamps in UTC.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        datetime: Local datetime (naive)
    """
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)


def local_to_timestamp(dt: datetime) -> int:
    """
    Convert local datetime to Unix timestamp (UTC).
    
    Args:
        dt: Local datetime (naive)
        
    Returns:
        int: Unix timestamp (seconds since epoch)
    """
    # Convert local time to UTC
    dt_utc = dt - timedelta(hours=Config.LOCAL_TIMESHIFT)
    # Add UTC timezone info for correct timestamp calculation
    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return int(dt_utc.timestamp())


def start_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get start of day (00:00:00) for given datetime.
    
    Args:
        dt: Datetime to get start of day for (default: now)
        
    Returns:
        datetime: Start of day (naive, local time)
    """
    if dt is None:
        dt = local_now()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get end of day (23:59:59) for given datetime.
    
    Args:
        dt: Datetime to get end of day for (default: now)
        
    Returns:
        datetime: End of day (naive, local time)
    """
    if dt is None:
        dt = local_now()
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string.
    
    Args:
        dt: Datetime to format
        fmt: Format string (default: ISO-like)
        
    Returns:
        str: Formatted datetime string
    """
    return dt.strftime(fmt)


def parse_datetime(s: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse datetime from string.
    
    Args:
        s: String to parse
        fmt: Format string (default: ISO-like)
        
    Returns:
        datetime: Parsed datetime (naive)
    """
    return datetime.strptime(s, fmt)
