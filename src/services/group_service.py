"""
Group service for managing magic number groups.

Handles:
- Creating, updating, deleting groups
- Group assignments (magic -> group)
- Magic labels management
"""

from typing import Optional, Dict, Any, List

from ..db_sa.session import SessionLocal
from ..db_sa.models import MagicGroup, MagicGroupAssignment, Magic
from ..readmodels.dashboard_queries import get_magics_with_groups, get_groups
from ..utils.logger import get_logger

logger = get_logger()


class GroupService:
    """Service for magic group management operations."""
    
    @staticmethod
    def list_magics(account_id: str) -> List[Dict[str, Any]]:
        """
        Get all magics with their group assignments.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List of magic dictionaries
        """
        return get_magics_with_groups(account_id)
    
    @staticmethod
    def list_groups(account_id: str) -> List[Dict[str, Any]]:
        """
        Get all groups for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List of group dictionaries
        """
        return get_groups(account_id)
    
    @staticmethod
    def create_group(
        account_id: str,
        name: str,
        label2: Optional[str] = None,
        font_color: Optional[str] = None,
        fill_color: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new magic group.
        
        Args:
            account_id: Account identifier
            name: Group name
            label2: Secondary label (optional)
            font_color: Font color for display (optional)
            fill_color: Fill color for display (optional)
            
        Returns:
            Created group data
        """
        with SessionLocal() as session:
            group = MagicGroup(
                account_id=account_id,
                name=name,
                label2=label2.strip() if label2 else None,
                font_color=font_color.strip() if font_color else None,
                fill_color=fill_color.strip() if fill_color else None,
            )
            session.add(group)
            session.commit()
            session.refresh(group)
            
            result = {
                "group_id": group.id,
                "account_id": group.account_id,
                "name": group.name,
                "label2": group.label2,
                "font_color": group.font_color,
                "fill_color": group.fill_color,
            }
            
        logger.info(f"Group created: {name} (id={result['group_id']}) for account {account_id}")
        return result
    
    @staticmethod
    def update_group(
        group_id: int,
        name: Optional[str] = None,
        label2: Optional[str] = None,
        font_color: Optional[str] = None,
        fill_color: Optional[str] = None
    ) -> bool:
        """
        Update a magic group.
        
        Args:
            group_id: Group identifier
            name: New group name (optional)
            label2: New secondary label (optional)
            font_color: New font color (optional)
            fill_color: New fill color (optional)
            
        Returns:
            True if updated, False if group not found
        """
        with SessionLocal() as session:
            group = session.get(MagicGroup, group_id)
            if not group:
                return False
            
            if name is not None:
                group.name = name
            if label2 is not None:
                cleaned = label2.strip()
                group.label2 = cleaned or None
            if font_color is not None:
                cleaned = font_color.strip()
                group.font_color = cleaned or None
            if fill_color is not None:
                cleaned = fill_color.strip()
                group.fill_color = cleaned or None
            
            session.commit()
            
        logger.info(f"Group updated: id={group_id}")
        return True
    
    @staticmethod
    def delete_group(account_id: str, group_id: int) -> bool:
        """
        Delete a magic group and its assignments.
        
        Args:
            account_id: Account identifier
            group_id: Group identifier
            
        Returns:
            True if deleted
        """
        with SessionLocal() as session:
            # Delete assignments first
            session.query(MagicGroupAssignment).filter(
                MagicGroupAssignment.account_id == account_id,
                MagicGroupAssignment.group_id == group_id,
            ).delete()
            
            # Delete group
            deleted = session.query(MagicGroup).filter(
                MagicGroup.account_id == account_id,
                MagicGroup.id == group_id,
            ).delete()
            
            session.commit()
            
        logger.info(f"Group deleted: id={group_id} for account {account_id}")
        return deleted > 0
    
    @staticmethod
    def update_group_assignments(account_id: str, group_id: int, magic_ids: List[int]) -> bool:
        """
        Update magic assignments for a group (replaces all existing).
        
        Args:
            account_id: Account identifier
            group_id: Group identifier
            magic_ids: List of magic IDs to assign
            
        Returns:
            True if updated
        """
        with SessionLocal() as session:
            # Delete existing assignments
            session.query(MagicGroupAssignment).filter(
                MagicGroupAssignment.account_id == account_id,
                MagicGroupAssignment.group_id == group_id,
            ).delete()
            
            # Add new assignments
            for magic_id in magic_ids:
                session.add(
                    MagicGroupAssignment(
                        account_id=account_id,
                        group_id=group_id,
                        magic_id=magic_id
                    )
                )
            
            session.commit()
            
        logger.info(f"Group assignments updated: group_id={group_id}, magics={magic_ids}")
        return True
    
    @staticmethod
    def update_magic_labels(account_id: str, labels: List[Dict[str, Any]]) -> bool:
        """
        Update labels for multiple magic numbers.
        
        Args:
            account_id: Account identifier
            labels: List of {magic: int, label: str} dicts
            
        Returns:
            True if updated
        """
        with SessionLocal() as session:
            for item in labels:
                magic_id = item["magic"]
                label = item["label"]
                
                magic = session.get(Magic, {"account_id": account_id, "id": magic_id})
                if not magic:
                    magic = Magic(account_id=account_id, id=magic_id, label=label)
                    session.add(magic)
                else:
                    magic.label = label
            
            session.commit()
            
        logger.info(f"Magic labels updated for account {account_id}: {len(labels)} labels")
        return True
