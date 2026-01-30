"""
Chart service for managing chart (.chr) file editing.

Handles:
- Reading/writing .chr files (UCS-2 LE BOM encoding)
- Chart sections CRUD
- Validation of chart parameters
- Writing parameter values to chart files
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..db_sa.session import SessionLocal
from ..db_sa.models import ChartConfig, ChartSection
from ..utils.logger import get_logger

logger = get_logger()

# Default charts path relative to project root
DEFAULT_CHARTS_PATH = "charts"


class ChartService:
    """Service for chart file editing operations."""

    # --- Config Management ---

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Get or create chart configuration.

        Returns:
            Config dict with charts_path
        """
        with SessionLocal() as session:
            config = session.query(ChartConfig).first()
            if not config:
                # Create default config
                project_root = Path(__file__).resolve().parents[2]
                default_path = str(project_root / DEFAULT_CHARTS_PATH)
                config = ChartConfig(charts_path=default_path)
                session.add(config)
                session.commit()
                session.refresh(config)
                logger.info(f"Created default chart config with path: {default_path}")

            return {
                "id": config.id,
                "charts_path": config.charts_path,
            }

    @staticmethod
    def set_charts_path(path: str) -> Dict[str, Any]:
        """
        Update charts folder path.

        Args:
            path: New path to charts folder

        Returns:
            Updated config dict
        """
        with SessionLocal() as session:
            config = session.query(ChartConfig).first()
            if not config:
                config = ChartConfig(charts_path=path)
                session.add(config)
            else:
                config.charts_path = path
            session.commit()
            session.refresh(config)

            logger.info(f"Charts path updated to: {path}")
            return {
                "id": config.id,
                "charts_path": config.charts_path,
            }

    # --- Folder Operations ---

    @staticmethod
    def list_folders() -> List[str]:
        """
        List subfolders in charts directory.

        Returns:
            List of folder names
        """
        config = ChartService.get_config()
        charts_path = config["charts_path"]

        if not os.path.exists(charts_path):
            logger.warning(f"Charts path does not exist: {charts_path}")
            return []

        folders = []
        for item in os.listdir(charts_path):
            item_path = os.path.join(charts_path, item)
            if os.path.isdir(item_path):
                folders.append(item)

        logger.info(f"Found {len(folders)} folders in {charts_path}")
        return sorted(folders)

    @staticmethod
    def _get_chr_files(folder_name: str) -> List[str]:
        """
        Get list of .chr files in a folder.

        Args:
            folder_name: Name of subfolder

        Returns:
            List of full paths to .chr files
        """
        config = ChartService.get_config()
        folder_path = os.path.join(config["charts_path"], folder_name)

        if not os.path.exists(folder_path):
            return []

        files = []
        for item in os.listdir(folder_path):
            if item.lower().endswith(".chr"):
                files.append(os.path.join(folder_path, item))

        return sorted(files)

    # --- File Operations (UCS-2 LE BOM) ---

    @staticmethod
    def _read_chr_file(path: str) -> str:
        """
        Read .chr file with UCS-2 LE BOM encoding.

        Args:
            path: Path to .chr file

        Returns:
            File content as string
        """
        with open(path, "r", encoding="utf-16-le") as f:
            content = f.read()
            # Remove BOM if present
            if content.startswith("\ufeff"):
                content = content[1:]
            return content

    @staticmethod
    def _write_chr_file(path: str, content: str) -> None:
        """
        Write .chr file with UCS-2 LE BOM encoding.

        Args:
            path: Path to .chr file
            content: Content to write
        """
        with open(path, "w", encoding="utf-16-le") as f:
            # Add BOM
            f.write("\ufeff" + content)

    @staticmethod
    def _normalize_line(line: str) -> str:
        """
        Normalize line for comparison (remove extra spaces from MT5 format).

        MT5 .chr files have spaces between characters in UCS-2 format.
        This normalizes for comparison.

        Args:
            line: Raw line from file

        Returns:
            Normalized line
        """
        # Remove null characters and extra whitespace
        return line.replace("\x00", "").strip()

    # --- Section CRUD ---

    @staticmethod
    def list_sections(folder_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get sections, optionally filtered by folder.

        Args:
            folder_name: Filter by folder (optional)

        Returns:
            List of section dicts
        """
        with SessionLocal() as session:
            query = session.query(ChartSection)
            if folder_name:
                query = query.filter(ChartSection.folder_name == folder_name)
            query = query.order_by(ChartSection.folder_name, ChartSection.order_index)

            sections = []
            for s in query.all():
                sections.append({
                    "id": s.id,
                    "folder_name": s.folder_name,
                    "validation_line1": s.validation_line1,
                    "validation_line2": s.validation_line2,
                    "param_key": s.param_key,
                    "param_value": s.param_value,
                    "order_index": s.order_index,
                })

            return sections

    @staticmethod
    def create_section(
        folder_name: str,
        validation_line1: str,
        validation_line2: Optional[str],
        param_key: str,
        param_value: str,
    ) -> Dict[str, Any]:
        """
        Create a new chart section.

        Args:
            folder_name: Folder name
            validation_line1: First validation line
            validation_line2: Second validation line (optional)
            param_key: Parameter key (e.g. "Lot=")
            param_value: Parameter value (e.g. "0.2")

        Returns:
            Created section dict
        """
        with SessionLocal() as session:
            # Get max order_index for this folder
            max_order = session.query(ChartSection).filter(
                ChartSection.folder_name == folder_name
            ).count()

            section = ChartSection(
                folder_name=folder_name,
                validation_line1=validation_line1.strip(),
                validation_line2=validation_line2.strip() if validation_line2 else None,
                param_key=param_key.strip(),
                param_value=param_value.strip(),
                order_index=max_order,
            )
            session.add(section)
            session.commit()
            session.refresh(section)

            result = {
                "id": section.id,
                "folder_name": section.folder_name,
                "validation_line1": section.validation_line1,
                "validation_line2": section.validation_line2,
                "param_key": section.param_key,
                "param_value": section.param_value,
                "order_index": section.order_index,
            }

            logger.info(f"Section created: id={section.id}, folder={folder_name}")
            return result

    @staticmethod
    def update_section(
        section_id: int,
        validation_line1: Optional[str] = None,
        validation_line2: Optional[str] = None,
        param_key: Optional[str] = None,
        param_value: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing section.

        Args:
            section_id: Section ID
            validation_line1: New validation line 1 (optional)
            validation_line2: New validation line 2 (optional)
            param_key: New parameter key (optional)
            param_value: New parameter value (optional)

        Returns:
            Updated section dict or None if not found
        """
        with SessionLocal() as session:
            section = session.get(ChartSection, section_id)
            if not section:
                return None

            if validation_line1 is not None:
                section.validation_line1 = validation_line1.strip()
            if validation_line2 is not None:
                section.validation_line2 = validation_line2.strip() if validation_line2 else None
            if param_key is not None:
                section.param_key = param_key.strip()
            if param_value is not None:
                section.param_value = param_value.strip()

            session.commit()
            session.refresh(section)

            result = {
                "id": section.id,
                "folder_name": section.folder_name,
                "validation_line1": section.validation_line1,
                "validation_line2": section.validation_line2,
                "param_key": section.param_key,
                "param_value": section.param_value,
                "order_index": section.order_index,
            }

            logger.info(f"Section updated: id={section_id}")
            return result

    @staticmethod
    def delete_section(section_id: int) -> bool:
        """
        Delete a section.

        Args:
            section_id: Section ID

        Returns:
            True if deleted
        """
        with SessionLocal() as session:
            deleted = session.query(ChartSection).filter(
                ChartSection.id == section_id
            ).delete()
            session.commit()

            logger.info(f"Section deleted: id={section_id}")
            return deleted > 0

    # --- Validation ---

    @staticmethod
    def validate_section(
        folder_name: str,
        validation_line1: str,
        validation_line2: Optional[str],
        param_key: str,
    ) -> Dict[str, Any]:
        """
        Validate section against chart files.

        Args:
            folder_name: Folder name
            validation_line1: First validation line
            validation_line2: Second validation line (optional)
            param_key: Parameter key to find

        Returns:
            Validation result with:
            - matched_files: list of matching file names
            - matched_file: single matched file (if exactly one)
            - needs_second_validation: True if multiple files match line1
            - param_found: True if param_key found in matched file
            - current_value: Current value of the parameter
            - status: "ok", "multiple_files", "no_match", "param_not_found"
        """
        chr_files = ChartService._get_chr_files(folder_name)
        val1_normalized = validation_line1.strip().lower()
        val2_normalized = validation_line2.strip().lower() if validation_line2 else None
        param_key_normalized = param_key.strip().lower()

        matched_files = []

        for file_path in chr_files:
            try:
                content = ChartService._read_chr_file(file_path)
                content_lower = content.lower()

                # Check validation line 1
                if val1_normalized in content_lower:
                    # If we have validation line 2, check it too
                    if val2_normalized:
                        if val2_normalized in content_lower:
                            matched_files.append(file_path)
                    else:
                        matched_files.append(file_path)
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
                continue

        result = {
            "matched_files": [os.path.basename(f) for f in matched_files],
            "matched_file": None,
            "needs_second_validation": False,
            "param_found": False,
            "current_value": None,
            "status": "no_match",
        }

        if len(matched_files) == 0:
            result["status"] = "no_match"
        elif len(matched_files) > 1 and not val2_normalized:
            result["status"] = "multiple_files"
            result["needs_second_validation"] = True
        else:
            # Single match or multiple with both validations
            matched_file = matched_files[0]
            result["matched_file"] = os.path.basename(matched_file)

            # Find parameter value
            try:
                content = ChartService._read_chr_file(matched_file)
                lines = content.split("\n")

                for line in lines:
                    line_stripped = line.strip().lower()
                    if line_stripped.startswith(param_key_normalized):
                        result["param_found"] = True
                        # Extract value after =
                        if "=" in line:
                            value = line.split("=", 1)[1].strip()
                            result["current_value"] = value
                        result["status"] = "ok"
                        break

                if not result["param_found"]:
                    result["status"] = "param_not_found"

            except Exception as e:
                logger.warning(f"Error reading matched file: {e}")
                result["status"] = "error"

        return result

    # --- Write Operations ---

    @staticmethod
    def write_section(section_id: int) -> Dict[str, Any]:
        """
        Write section parameter value to the matched chart file.

        Args:
            section_id: Section ID

        Returns:
            Result dict with status and message
        """
        with SessionLocal() as session:
            section = session.get(ChartSection, section_id)
            if not section:
                return {"status": "error", "message": "Section not found"}

            # Validate to find the file
            validation = ChartService.validate_section(
                section.folder_name,
                section.validation_line1,
                section.validation_line2,
                section.param_key,
            )

            if validation["status"] != "ok":
                return {
                    "status": "error",
                    "message": f"Validation failed: {validation['status']}",
                }

            # Get full file path
            config = ChartService.get_config()
            file_path = os.path.join(
                config["charts_path"],
                section.folder_name,
                validation["matched_file"],
            )

            try:
                content = ChartService._read_chr_file(file_path)
                lines = content.split("\n")
                param_key_lower = section.param_key.strip().lower()
                modified = False

                for i, line in enumerate(lines):
                    line_stripped = line.strip().lower()
                    if line_stripped.startswith(param_key_lower):
                        # Replace the value
                        if "=" in line:
                            key_part = line.split("=", 1)[0]
                            lines[i] = f"{key_part}={section.param_value}"
                            modified = True
                            break

                if not modified:
                    return {
                        "status": "error",
                        "message": "Parameter not found in file",
                    }

                # Write back
                new_content = "\n".join(lines)
                ChartService._write_chr_file(file_path, new_content)

                logger.info(f"Written section {section_id} to {file_path}")
                return {
                    "status": "ok",
                    "message": f"Updated {validation['matched_file']}",
                    "file": validation["matched_file"],
                }

            except Exception as e:
                logger.error(f"Error writing to file: {e}")
                return {"status": "error", "message": str(e)}

    @staticmethod
    def write_folder_sections(folder_name: str) -> Dict[str, Any]:
        """
        Write all sections for a folder.

        Args:
            folder_name: Folder name

        Returns:
            Result dict with status and details
        """
        sections = ChartService.list_sections(folder_name)
        results = []
        success_count = 0
        error_count = 0

        for section in sections:
            result = ChartService.write_section(section["id"])
            results.append({
                "section_id": section["id"],
                "param_key": section["param_key"],
                **result,
            })
            if result["status"] == "ok":
                success_count += 1
            else:
                error_count += 1

        logger.info(f"Write folder {folder_name}: {success_count} success, {error_count} errors")
        return {
            "status": "ok" if error_count == 0 else "partial",
            "success_count": success_count,
            "error_count": error_count,
            "results": results,
        }
