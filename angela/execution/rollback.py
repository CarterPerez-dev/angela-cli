"""
Rollback functionality for Angela CLI operations.

This module provides the ability to undo previous operations
by restoring files and directories from backups.
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union

from angela.utils.logging import get_logger
from angela.execution.filesystem import BACKUP_DIR

logger = get_logger(__name__)

# File to store operation history for rollback
HISTORY_FILE = BACKUP_DIR / "operation_history.json"


class OperationRecord:
    """Record of an operation for rollback purposes."""
    
    def __init__(
        self,
        operation_type: str,
        params: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        backup_path: Optional[str] = None
    ):
        self.operation_type = operation_type
        self.params = params
        self.timestamp = timestamp or datetime.now()
        self.backup_path = backup_path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the record to a dictionary for storage."""
        return {
            "operation_type": self.operation_type,
            "params": self.params,
            "timestamp": self.timestamp.isoformat(),
            "backup_path": str(self.backup_path) if self.backup_path else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationRecord':
        """Create a record from a dictionary."""
        return cls(
            operation_type=data["operation_type"],
            params=data["params"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            backup_path=data["backup_path"]
        )


class RollbackManager:
    """Manager for operation history and rollback functionality."""
    
    def __init__(self):
        """Initialize the rollback manager."""
        self._ensure_history_file()
        self._operations = self._load_history()
    
    def _ensure_history_file(self):
        """Ensure the history file and directory exist."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if not HISTORY_FILE.exists():
            self._save_history([])
    
    def _load_history(self) -> List[OperationRecord]:
        """Load operation history from the history file."""
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
            
            return [OperationRecord.from_dict(item) for item in data]
        
        except Exception as e:
            logger.error(f"Error loading operation history: {str(e)}")
            return []
    
    def _save_history(self, operations: List[OperationRecord]):
        """Save operation history to the history file."""
        try:
            with open(HISTORY_FILE, 'w') as f:
                json.dump([op.to_dict() for op in operations], f, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving operation history: {str(e)}")
    
    async def record_operation(
        self,
        operation_type: str,
        params: Dict[str, Any],
        backup_path: Optional[Union[str, Path]] = None
    ):
        """
        Record an operation for potential rollback.
        
        Args:
            operation_type: The type of operation.
            params: Parameters of the operation.
            backup_path: Path to the backup, if one was created.
        """
        try:
            record = OperationRecord(
                operation_type=operation_type,
                params=params,
                backup_path=str(backup_path) if backup_path else None
            )
            
            self._operations.append(record)
            self._save_history(self._operations)
            
            logger.debug(f"Recorded operation: {operation_type}")
        
        except Exception as e:
            logger.error(f"Error recording operation: {str(e)}")
    
    async def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a list of recent operations that can be rolled back.
        
        Args:
            limit: Maximum number of operations to return.
            
        Returns:
            A list of operation details.
        """
        try:
            # Get the most recent operations, up to the limit
            recent = self._operations[-limit:] if self._operations else []
            
            # Convert to a more user-friendly format
            result = []
            for i, op in enumerate(reversed(recent)):
                # Create a more readable description
                description = self._get_operation_description(op)
                
                result.append({
                    "id": len(self._operations) - i - 1,  # Original index in the full list
                    "timestamp": op.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "operation_type": op.operation_type,
                    "description": description,
                    "can_rollback": bool(op.backup_path)
                })
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting recent operations: {str(e)}")
            return []
    
    def _get_operation_description(self, op: OperationRecord) -> str:
        """Generate a human-readable description of an operation."""
        try:
            if op.operation_type == "create_file":
                return f"Created file: {op.params.get('path', 'unknown')}"
            
            elif op.operation_type == "write_file":
                return f"Wrote to file: {op.params.get('path', 'unknown')}"
            
            elif op.operation_type == "delete_file":
                return f"Deleted file: {op.params.get('path', 'unknown')}"
            
            elif op.operation_type == "create_directory":
                return f"Created directory: {op.params.get('path', 'unknown')}"
            
            elif op.operation_type == "delete_directory":
                return f"Deleted directory: {op.params.get('path', 'unknown')}"
            
            elif op.operation_type == "copy_file":
                return f"Copied file from {op.params.get('source', 'unknown')} to {op.params.get('destination', 'unknown')}"
            
            elif op.operation_type == "move_file":
                return f"Moved file from {op.params.get('source', 'unknown')} to {op.params.get('destination', 'unknown')}"
            
            elif op.operation_type == "execute_command":
                return f"Executed command: {op.params.get('command', 'unknown')}"
            
            else:
                return f"{op.operation_type}: {op.params}"
        
        except Exception as e:
            logger.error(f"Error generating operation description: {str(e)}")
            return "Unknown operation"
    
    async def rollback_operation(self, operation_id: int) -> bool:
        """
        Roll back an operation by its ID.
        
        Args:
            operation_id: The ID of the operation to roll back.
            
        Returns:
            True if the rollback was successful, False otherwise.
        """
        try:
            # Validate the operation ID
            if operation_id < 0 or operation_id >= len(self._operations):
                logger.error(f"Invalid operation ID: {operation_id}")
                return False
            
            # Get the operation record
            op = self._operations[operation_id]
            
            # Check if a backup exists
            if not op.backup_path:
                logger.error(f"No backup available for operation: {op.operation_type}")
                return False
            
            backup_path = Path(op.backup_path)
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Perform the rollback based on operation type
            if op.operation_type == "create_file":
                # For file creation, delete the created file
                path = Path(op.params.get("path", ""))
                if path.exists() and path.is_file():
                    path.unlink()
                    logger.info(f"Rolled back file creation: {path}")
            
            elif op.operation_type == "write_file" or op.operation_type == "delete_file":
                # For file writing/deletion, restore from backup
                path = Path(op.params.get("path", ""))
                # Create parent directory if it doesn't exist
                path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(backup_path, path)
                logger.info(f"Restored file from backup: {path}")
            
            elif op.operation_type == "create_directory":
                # For directory creation, delete the created directory
                path = Path(op.params.get("path", ""))
                if path.exists() and path.is_dir():
                    # Use rmtree to handle non-empty directories
                    shutil.rmtree(path)
                    logger.info(f"Rolled back directory creation: {path}")
            
            elif op.operation_type == "delete_directory":
                # For directory deletion, restore from backup
                path = Path(op.params.get("path", ""))
                # Create parent directory if it doesn't exist
                path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copytree(backup_path, path)
                logger.info(f"Restored directory from backup: {path}")
            
            elif op.operation_type == "copy_file" or op.operation_type == "move_file":
                # For copy/move, multiple files may need to be restored
                destination = Path(op.params.get("destination", ""))
                
                if destination.exists():
                    # Restore the destination if it was overwritten
                    if Path(op.backup_path).is_file():
                        shutil.copy2(backup_path, destination)
                        logger.info(f"Restored destination file: {destination}")
                    else:
                        shutil.rmtree(destination, ignore_errors=True)
                        shutil.copytree(backup_path, destination)
                        logger.info(f"Restored destination directory: {destination}")
                
                # For move operations, also restore the source
                if op.operation_type == "move_file":
                    source = Path(op.params.get("source", ""))
                    if not source.exists() and backup_path.exists():
                        # Create parent directory if it doesn't exist
                        source.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(backup_path, source)
                        logger.info(f"Restored source file: {source}")
            
            else:
                logger.error(f"Unsupported operation type for rollback: {op.operation_type}")
                return False
            
            # Remove the operation and all later operations from history
            self._operations = self._operations[:operation_id]
            self._save_history(self._operations)
            
            logger.info(f"Successfully rolled back operation {operation_id}: {op.operation_type}")
            return True
        
        except Exception as e:
            logger.exception(f"Error rolling back operation {operation_id}: {str(e)}")
            return False


# Global rollback manager instance
rollback_manager = RollbackManager()
