"""
Logging configuration and utilities for MT5 Trading Dashboard
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from ..config.settings import Config


class LoggerConfig:
    """Logger configuration and setup"""
    
    _logger: Optional[logging.Logger] = None
    _initialized = False
    
    @classmethod
    def setup_logger(cls, log_level: str = None, log_file: Optional[str] = None) -> logging.Logger:
        """
        Setup application logger with console and file handlers
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                      If None, uses Config.LOG_LEVEL or defaults to INFO
            log_file: Path to log file. If None, logs only to console
        
        Returns:
            Configured logger instance
        """
        if cls._initialized and cls._logger:
            return cls._logger
        
        # Get log level
        if log_level is None:
            log_level = getattr(Config, 'LOG_LEVEL', 'INFO')
        
        level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Create logger
        logger = logging.getLogger('mt5_dashboard')
        logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (if log_file is specified)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        cls._logger = logger
        cls._initialized = True
        
        return logger
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get configured logger instance, setup if not initialized"""
        if not cls._initialized or cls._logger is None:
            return cls.setup_logger()
        return cls._logger


# Global logger instance
def get_logger() -> logging.Logger:
    """Get application logger"""
    return LoggerConfig.get_logger()

