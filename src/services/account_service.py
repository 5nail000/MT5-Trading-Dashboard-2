"""
Account service for managing MT5 accounts.

Handles:
- Account credentials (save, get, validate)
- Account labels and settings
- Account listing with info
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from ..db_sa.session import SessionLocal
from ..db_sa.models import Account, AccountInfo, AccountCredentials
from ..security.crypto import encrypt_text, decrypt_text
from ..utils.logger import get_logger

logger = get_logger()


class AccountService:
    """Service for account management operations."""
    
    @staticmethod
    def list_accounts() -> List[Dict[str, Any]]:
        """
        Get all accounts with their info and credential status.
        
        Returns:
            List of account dictionaries with account_id, label, account_info, has_credentials
        """
        with SessionLocal() as session:
            accounts = session.query(Account).all()
            infos = {info.account_id: info for info in session.query(AccountInfo).all()}
            creds = {c.account_id: c for c in session.query(AccountCredentials).all()}

        result = []
        for acc in accounts:
            info = infos.get(acc.account_id)
            result.append({
                "account_id": acc.account_id,
                "label": acc.label or acc.account_id,
                "history_start_date": acc.history_start_date.isoformat() if acc.history_start_date else None,
                "account_info": {
                    "account_number": info.account_number if info else acc.account_id,
                    "leverage": info.leverage if info else 0,
                    "server": info.server if info else "",
                },
                "has_credentials": bool(creds.get(acc.account_id) and creds[acc.account_id].password_encrypted),
            })
        return result
    
    @staticmethod
    def get_credentials(account_id: str) -> Optional[Dict[str, Any]]:
        """
        Get decrypted credentials for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Dict with login, password, server or None if not found
        """
        with SessionLocal() as session:
            creds = session.get(AccountCredentials, account_id)
            if not creds or not creds.password_encrypted or not creds.login or not creds.server:
                return None
            password = decrypt_text(creds.password_encrypted)
            if password is None:
                logger.error(f"Failed to decrypt credentials for account {account_id}")
                return None
            return {
                "login": int(creds.login),
                "password": password,
                "server": creds.server
            }
    
    @staticmethod
    def save_credentials(account_id: str, login: str, server: str, password: str) -> bool:
        """
        Save encrypted credentials for an account.
        
        Args:
            account_id: Account identifier
            login: MT5 login
            server: MT5 server
            password: MT5 password (will be encrypted)
            
        Returns:
            True if saved successfully
        """
        encrypted = encrypt_text(password)
        if encrypted is None:
            logger.error(f"Failed to encrypt credentials for account {account_id}")
            return False
            
        with SessionLocal() as session:
            creds = session.get(AccountCredentials, account_id)
            if not creds:
                creds = AccountCredentials(
                    account_id=account_id,
                    login=login,
                    server=server,
                    password_encrypted=encrypted,
                )
                session.add(creds)
            else:
                creds.login = login
                creds.server = server
                creds.password_encrypted = encrypted
            session.commit()
            
        logger.info(f"Credentials saved for account {account_id}")
        return True
    
    @staticmethod
    def update_label(account_id: str, label: str) -> bool:
        """
        Update account label.
        
        Args:
            account_id: Account identifier
            label: New label
            
        Returns:
            True if updated, False if account not found
        """
        with SessionLocal() as session:
            account = session.get(Account, account_id)
            if not account:
                return False
            account.label = label
            session.commit()
            
        logger.info(f"Label updated for account {account_id}: {label}")
        return True
    
    @staticmethod
    def update_history_start(account_id: str, history_start_date: Optional[datetime]) -> bool:
        """
        Update account history start date.
        
        Args:
            account_id: Account identifier
            history_start_date: Start date for history sync
            
        Returns:
            True if updated, False if account not found
        """
        with SessionLocal() as session:
            account = session.get(Account, account_id)
            if not account:
                return False
            account.history_start_date = history_start_date
            session.commit()
            
        logger.info(f"History start date updated for account {account_id}: {history_start_date}")
        return True
    
    @staticmethod
    def get_history_start_date(account_id: str) -> Optional[datetime]:
        """
        Get account history start date.
        
        Args:
            account_id: Account identifier
            
        Returns:
            History start date or None
        """
        with SessionLocal() as session:
            account = session.get(Account, account_id)
            if not account:
                return None
            return account.history_start_date
