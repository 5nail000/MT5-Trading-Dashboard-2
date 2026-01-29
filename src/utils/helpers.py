"""
Utility functions and helpers for MT5 Trading Dashboard
"""

import pprint
import time as time_mod
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional
from ..config.settings import Config


class PrettyPrinter:
    """Pretty printer utility"""
    
    def __init__(self, indent: int = 4):
        self.pp = pprint.PrettyPrinter(indent=indent)
    
    def print(self, obj: Any):
        """Print object with pretty formatting"""
        self.pp.pprint(obj)


class DateUtils:
    """Date and time utilities"""
    
    @staticmethod
    def get_current_time() -> datetime:
        """Get current local time"""
        # datetime.now() уже возвращает локальное время системы
        return datetime.now()
    
    @staticmethod
    def get_today() -> datetime:
        """Get today's date at midnight (local time)"""
        now = datetime.now()
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def get_start_of_week() -> datetime:
        """Get start of current week (local time)"""
        today = DateUtils.get_today()
        now = datetime.now()
        return today - timedelta(days=now.weekday())
    
    @staticmethod
    def get_start_of_month() -> datetime:
        """Get start of current month (local time)"""
        now = datetime.now()
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def get_start_of_year() -> datetime:
        """Get start of current year (local time)"""
        now = datetime.now()
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def is_weekend() -> bool:
        """Check if current day is weekend"""
        return datetime.now().weekday() in [5, 6]  # Saturday or Sunday
    
    @staticmethod
    def format_datetime_range(from_date: datetime, to_date: datetime) -> str:
        """Format datetime range for display"""
        return f"From {from_date} to {to_date}"


class PerformanceUtils:
    """Performance calculation utilities"""
    
    @staticmethod
    def calculate_percentage_change(current: float, start: float) -> float:
        """Calculate percentage change"""
        if start == 0:
            return 0
        return ((current - start) / start) * 100
    
    @staticmethod
    def get_performance_color(percentage: float) -> str:
        """Get color based on performance percentage"""
        if percentage >= 0:
            return Config.COLOR_SCHEMES["positive"]
        elif percentage >= Config.PERFORMANCE_THRESHOLDS["warning"]:
            return Config.COLOR_SCHEMES["negative_warning"]
        elif percentage >= Config.PERFORMANCE_THRESHOLDS["critical"]:
            return Config.COLOR_SCHEMES["negative_critical"]
        else:
            return Config.COLOR_SCHEMES["negative_danger"]
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD") -> str:
        """Format currency amount"""
        return f"{amount:.2f} {currency}"
    
    @staticmethod
    def format_percentage(percentage: float) -> str:
        """Format percentage with sign"""
        return f"{percentage:+.2f}%"


class DataUtils:
    """Data processing utilities"""
    
    @staticmethod
    def create_labels_dict(magics: List[int], descriptions: Dict[int, str], 
                          account_id: str, reverse_order: bool = False) -> Dict[int, str]:
        """Create labels dictionary for magic numbers"""
        labels = {}
        for magic in magics:
            description = descriptions.get(magic)
            if description:
                if reverse_order:
                    labels[magic] = f"{description} - {magic}"
                else:
                    labels[magic] = f"{magic} - {description}"
            else:
                labels[magic] = str(magic)
        return labels
    
    @staticmethod
    def prepare_chart_data(data: Dict[str, Any], sort_option: str) -> Dict[str, Any]:
        """Prepare data for chart display"""
        # This would contain chart-specific data preparation logic
        return data
    
    @staticmethod
    def filter_deals_by_period(deals: List, from_date: datetime, to_date: datetime) -> List:
        """Filter deals by time period"""
        filtered_deals = []
        for deal in deals:
            if deal.type == 2:  # Skip balance changes
                continue
            if from_date and deal.time < from_date.timestamp():
                continue
            if to_date and deal.time > to_date.timestamp():
                continue
            filtered_deals.append(deal)
        return filtered_deals


class SessionUtils:
    """Session management utilities"""
    
    @staticmethod
    def init_session_state(session_state: Any):
        """Initialize session state variables"""
        from datetime import timedelta
        if 'from_date' not in session_state:
            session_state.from_date = DateUtils.get_today()
        if 'to_date' not in session_state:
            # Добавляем 1 день к текущему времени по умолчанию, чтобы наверняка захватить все сделки
            # с учетом GMT shift и возможных задержек
            session_state.to_date = DateUtils.get_current_time() + timedelta(days=1)
        if 'pending_from_date' not in session_state:
            session_state.pending_from_date = session_state.from_date
        if 'pending_to_date' not in session_state:
            session_state.pending_to_date = session_state.to_date
        if 'last_update' not in session_state:
            session_state.last_update = time_mod.time()
    
    @staticmethod
    def should_auto_refresh(session_state: Any) -> bool:
        """Check if auto-refresh should trigger"""
        current_time = time_mod.time()
        return (current_time - session_state.last_update >= Config.AUTO_REFRESH_INTERVAL)
    
    @staticmethod
    def update_session_timestamp(session_state: Any):
        """Update session timestamp"""
        session_state.last_update = time_mod.time()


class ValidationUtils:
    """Data validation utilities"""
    
    @staticmethod
    def validate_account_data(account: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate account data
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not isinstance(account, dict):
            return False, "Account data must be a dictionary"
        
        required_fields = ['login', 'password', 'server']
        missing_fields = [field for field in required_fields if field not in account]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        if not isinstance(account.get('login'), (int, str)):
            return False, "Login must be an integer or string"
        
        if not isinstance(account.get('password'), str):
            return False, "Password must be a string"
        
        if not isinstance(account.get('server'), str):
            return False, "Server must be a string"
        
        return True, None
    
    @staticmethod
    def validate_date_range(from_date: datetime, to_date: datetime) -> tuple[bool, Optional[str]]:
        """
        Validate date range
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not isinstance(from_date, datetime):
            return False, "from_date must be a datetime object"
        
        if not isinstance(to_date, datetime):
            return False, "to_date must be a datetime object"
        
        if from_date > to_date:
            return False, f"from_date ({from_date}) must be <= to_date ({to_date})"
        
        return True, None
    
    @staticmethod
    def validate_magic_number(magic: int) -> tuple[bool, Optional[str]]:
        """
        Validate magic number
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not isinstance(magic, int):
            return False, f"Magic number must be an integer, got {type(magic).__name__}"
        
        if magic < 0:
            return False, f"Magic number must be non-negative, got {magic}"
        
        return True, None
    
    @staticmethod
    def validate_deals_list(deals: List) -> tuple[bool, Optional[str]]:
        """
        Validate deals list (accepts both list and tuple)
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not isinstance(deals, (list, tuple)):
            return False, f"Deals must be a list or tuple, got {type(deals).__name__}"
        
        return True, None


# Global utility instances
pp = PrettyPrinter()
date_utils = DateUtils()
performance_utils = PerformanceUtils()
data_utils = DataUtils()
session_utils = SessionUtils()
validation_utils = ValidationUtils()
