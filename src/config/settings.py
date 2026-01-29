"""
Configuration settings for MT5 Trading Dashboard
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass


class Config:
    """Main configuration class"""
    
    # Application settings
    APP_NAME = os.getenv("APP_NAME", "MT5 Trading Dashboard")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    PAGE_TITLE = os.getenv("PAGE_TITLE", "Trading Dashboard")
    
    # Database settings
    DATABASE_PATH = os.getenv("DATABASE_PATH", "magics.db")
    SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", None)
    
    # Trading settings
    BALANCE_START = int(os.getenv("BALANCE_START", "8736"))
    CUSTOM_TEXT = os.getenv("CUSTOM_TEXT", "October")
    LOCAL_TIMESHIFT = int(os.getenv("LOCAL_TIMESHIFT", "3"))
    
    # Auto-refresh settings
    AUTO_REFRESH_INTERVAL = int(os.getenv("AUTO_REFRESH_INTERVAL", "60"))  # seconds
    AUTO_REFRESH_ENABLED = os.getenv("AUTO_REFRESH_ENABLED", "True").lower() == "true"
    
    # Logging settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE = os.getenv("LOG_FILE", None)  # Path to log file, None for console only

    # Credential encryption key (Fernet)
    MT5_CRED_KEY = os.getenv("MT5_CRED_KEY", None)

    # Drawdown calculation toggle (tick data heavy)
    DRAWNDOWN_ENABLED = os.getenv("DRAWDOWN_ENABLED", "false").lower() == "true"

    # MT5 signal handlers (disable to let uvicorn handle Ctrl+C)
    MT5_REGISTER_SIGNAL_HANDLERS = os.getenv("MT5_REGISTER_SIGNAL_HANDLERS", "false").lower() == "true"
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate configuration settings
        
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate LOCAL_TIMESHIFT
        if not isinstance(cls.LOCAL_TIMESHIFT, int) or cls.LOCAL_TIMESHIFT < -12 or cls.LOCAL_TIMESHIFT > 14:
            errors.append(f"LOCAL_TIMESHIFT must be an integer between -12 and 14, got {cls.LOCAL_TIMESHIFT}")
        
        # Validate AUTO_REFRESH_INTERVAL
        if not isinstance(cls.AUTO_REFRESH_INTERVAL, int) or cls.AUTO_REFRESH_INTERVAL < 0:
            errors.append(f"AUTO_REFRESH_INTERVAL must be a non-negative integer, got {cls.AUTO_REFRESH_INTERVAL}")
        
        # Validate LOG_LEVEL
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of {valid_log_levels}, got {cls.LOG_LEVEL}")
        
        # Validate DATABASE_PATH
        if not cls.DATABASE_PATH or not isinstance(cls.DATABASE_PATH, str):
            errors.append("DATABASE_PATH must be a non-empty string")
        
        # Validate BALANCE_START
        if not isinstance(cls.BALANCE_START, (int, float)) or cls.BALANCE_START < 0:
            errors.append(f"BALANCE_START must be a non-negative number, got {cls.BALANCE_START}")
        
        return len(errors) == 0, errors
    
    # Date range presets
    @staticmethod
    def get_date_presets() -> Dict[str, Dict[str, datetime]]:
        """Get predefined date ranges (returns local time)"""
        now = datetime.now()
        # Добавляем 1 день к текущему времени, чтобы наверняка захватить все сделки
        # с учетом GMT shift и возможных задержек
        end_time = now + timedelta(days=1)
        
        # datetime.now() уже возвращает локальное время, не нужно добавлять LOCAL_TIMESHIFT
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = today - timedelta(days=now.weekday())
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return {
            "today": {
                "from": today,
                "to": end_time
            },
            "this_week": {
                "from": start_of_week,
                "to": end_time
            },
            "this_month": {
                "from": start_of_month,
                "to": end_time
            },
            "this_year": {
                "from": start_of_year,
                "to": end_time
            }
        }
    
    # UI settings
    CHART_HEIGHT_MULTIPLIER = 30
    MIN_CHART_HEIGHT = 300
    CHART_MARGINS = {
        "t": 120,
        "b": 40,
        "l": 40,
        "r": 20
    }
    
    # Color schemes
    COLOR_SCHEMES = {
        "profit_loss": "RdYlGn",
        "positive": "lime",
        "negative_warning": "orange",
        "negative_critical": "OrangeRed",
        "negative_danger": "red"
    }
    
    # Performance thresholds (as percentages)
    PERFORMANCE_THRESHOLDS = {
        "warning": -12,
        "critical": -20
    }


# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    LOG_LEVEL = "INFO"


# Configuration factory
def get_config(env: str = None) -> Config:
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv("ENVIRONMENT", "development")
    
    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig
    }
    
    config = config_map.get(env, DevelopmentConfig)()
    
    # Validate configuration
    is_valid, errors = config.validate()
    if not is_valid:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    
    return config
