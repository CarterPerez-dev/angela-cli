# angela/execution/rollback.py
"""
Enhanced rollback functionality for Angela CLI operations.

This module provides the ability to undo complex, multi-step operations
by tracking and reverting individual actions within a transaction.
It supports rolling back different types of operations including:
- File system operations (create, modify, delete files and directories)
- Content manipulations (AI-driven file changes)
- Command executions (with compensating actions)
"""
import os
import json
import shlex
import uuid
import shutil
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union, Set


from angela.api.utils import get_logger
from angela.api.review import get_diff_manager
from angela.api.execution import get_execution_engine, get_backup_dir

logger = get_logger(__name__)

# File to store operation history for rollback
BACKUP_DIR = get_backup_dir()
HISTORY_FILE = BACKUP_DIR / "operation_history.json"
TRANSACTION_DIR = BACKUP_DIR / "transactions"

# Operation types
OP_FILE_SYSTEM = "filesystem"     # File system operations (create, delete, etc.)
OP_CONTENT = "content"            # Content manipulation operations
OP_COMMAND = "command"            # Command execution operations
OP_PLAN = "plan"                  # Plan execution operations


class OperationRecord:
    """Record of an operation for rollback purposes."""
    
    def __init__(
        self,
        operation_type: str,
        params: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        backup_path: Optional[str] = None,
        transaction_id: Optional[str] = None,
        step_id: Optional[str] = None,
        undo_info: Optional[Dict[str, Any]] = None
    ):
        self.operation_type = operation_type
        self.params = params
        self.timestamp = timestamp or datetime.now()
        self.backup_path = backup_path
        self.transaction_id = transaction_id
        self.step_id = step_id
        self.undo_info = undo_info or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the record to a dictionary for storage."""
        return {
            "operation_type": self.operation_type,
            "params": self.params,
            "timestamp": self.timestamp.isoformat(),
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "transaction_id": self.transaction_id,
            "step_id": self.step_id,
            "undo_info": self.undo_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationRecord':
        """Create a record from a dictionary."""
        return cls(
            operation_type=data["operation_type"],
            params=data["params"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            backup_path=data["backup_path"],
            transaction_id=data.get("transaction_id"),
            step_id=data.get("step_id"),
            undo_info=data.get("undo_info", {})
        )


class Transaction:
    """A group of operations that form a single logical action."""
    
    def __init__(
        self,
        transaction_id: str,
        description: str,
        timestamp: Optional[datetime] = None,
        status: str = "started"  # started, completed, failed, rolled_back
    ):
        self.transaction_id = transaction_id
        self.description = description
        self.timestamp = timestamp or datetime.now()
        self.status = status
        self.operation_ids: List[int] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the transaction to a dictionary for storage."""
        return {
            "transaction_id": self.transaction_id,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "operation_ids": self.operation_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create a transaction from a dictionary."""
        transaction = cls(
            transaction_id=data["transaction_id"],
            description=data["description"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status=data["status"]
        )
        transaction.operation_ids = data.get("operation_ids", [])
        return transaction


class RollbackManager:
    """Manager for operation history and rollback functionality."""
    
    def __init__(self):
        """Initialize the rollback manager."""
        self._ensure_directories()
        self._operations = self._load_history()
        self._transactions = self._load_transactions()
        self._active_transactions: Dict[str, Transaction] = {}
        self._command_compensations = self._load_command_compensations()
    
    def _ensure_directories(self):
        """Ensure the history file and transaction directory exist."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        TRANSACTION_DIR.mkdir(parents=True, exist_ok=True)
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
    
    def _load_transactions(self) -> Dict[str, Transaction]:
        """Load transactions from the transaction directory."""
        transactions = {}
        try:
            for file in TRANSACTION_DIR.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        transaction = Transaction.from_dict(data)
                        transactions[transaction.transaction_id] = transaction
                except Exception as e:
                    logger.error(f"Error loading transaction {file}: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading transactions: {str(e)}")
        
        return transactions
    
    def _save_transaction(self, transaction: Transaction):
        """Save a transaction to its file."""
        try:
            file_path = TRANSACTION_DIR / f"{transaction.transaction_id}.json"
            with open(file_path, 'w') as f:
                json.dump(transaction.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving transaction {transaction.transaction_id}: {str(e)}")
    
    def _load_command_compensations(self) -> Dict[str, str]:
        """Load command compensation rules from a file."""
        compensations = {}
        
        # Define built-in command compensations
        built_in = {
            # Git compensations
            "git add": "git reset",               # Unstage files
            "git commit": "git reset --soft HEAD~1",  # Undo last commit
            "git push": "git push -f origin HEAD~1:${branch}",  # Force push previous commit
            "git branch": "git branch -D",        # Delete branch
            
            # Package manager compensations
            "npm install": "npm uninstall",       # Uninstall npm package
            "pip install": "pip uninstall -y",    # Uninstall pip package
            "apt-get install": "apt-get remove",  # Remove apt package
            
            # File operations (as fallbacks)
            "mkdir": "rmdir",                     # Remove directory
            "touch": "rm",                        # Remove file
        }
        
        # Add the built-in compensations
        compensations.update(built_in)
        
        # TODO: Load custom compensations from a file
        
        return compensations
    
    async def start_transaction(self, description: str) -> str:
        """
        Start a new transaction.
        
        Args:
            description: Description of the transaction
            
        Returns:
            Transaction ID
        """
        transaction_id = str(uuid.uuid4())
        transaction = Transaction(transaction_id, description)
        
        # Add to active transactions
        self._active_transactions[transaction_id] = transaction
        
        # Save the transaction
        self._save_transaction(transaction)
        
        logger.info(f"Started transaction {transaction_id}: {description}")
        return transaction_id
    
    async def end_transaction(self, transaction_id: str, status: str = "completed") -> bool:
        """
        End a transaction.
        
        Args:
            transaction_id: Transaction ID
            status: Transaction status ("completed" or "failed")
            
        Returns:
            True if successful, False otherwise
        """
        if transaction_id not in self._active_transactions:
            logger.error(f"Transaction {transaction_id} not found in active transactions")
            return False
        
        # Update the transaction
        transaction = self._active_transactions[transaction_id]
        transaction.status = status
        
        # Save the transaction
        self._save_transaction(transaction)
        
        # Add to transactions dict
        self._transactions[transaction_id] = transaction
        
        # Remove from active transactions
        del self._active_transactions[transaction_id]
        
        logger.info(f"Ended transaction {transaction_id} with status: {status}")
        return True
    
    async def record_operation(
        self,
        operation_type: str,
        params: Dict[str, Any],
        backup_path: Optional[Union[str, Path]] = None,
        transaction_id: Optional[str] = None,
        step_id: Optional[str] = None,
        undo_info: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Record an operation for potential rollback.
        
        Args:
            operation_type: The type of operation.
            params: Parameters of the operation.
            backup_path: Path to the backup, if one was created.
            transaction_id: ID of the transaction this operation belongs to.
            step_id: ID of the step in the plan this operation belongs to.
            undo_info: Additional information needed for undoing the operation.
            
        Returns:
            Index of the operation in the history or None on error
        """
        try:
            # Create the operation record
            record = OperationRecord(
                operation_type=operation_type,
                params=params,
                backup_path=str(backup_path) if backup_path else None,
                transaction_id=transaction_id,
                step_id=step_id,
                undo_info=undo_info or {}
            )
            
            # Add to operations list
            operation_id = len(self._operations)
            self._operations.append(record)
            
            # Update transaction if provided
            if transaction_id:
                if transaction_id in self._active_transactions:
                    self._active_transactions[transaction_id].operation_ids.append(operation_id)
                    self._save_transaction(self._active_transactions[transaction_id])
                elif transaction_id in self._transactions:
                    self._transactions[transaction_id].operation_ids.append(operation_id)
                    self._save_transaction(self._transactions[transaction_id])
                else:
                    logger.warning(f"Transaction {transaction_id} not found when recording operation")
            
            # Save updated history
            self._save_history(self._operations)
            
            logger.debug(f"Recorded operation: {operation_type} (ID: {operation_id})")
            return operation_id
        
        except Exception as e:
            logger.error(f"Error recording operation: {str(e)}")
            return None
    
    async def record_file_operation(
        self,
        operation_type: str,
        params: Dict[str, Any],
        backup_path: Optional[Union[str, Path]] = None,
        transaction_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[int]:
        """
        Record a file system operation for potential rollback.
        
        Args:
            operation_type: The type of file operation.
            params: Parameters of the operation.
            backup_path: Path to the backup, if one was created.
            transaction_id: ID of the transaction this operation belongs to.
            step_id: ID of the step in the plan this operation belongs to.
            
        Returns:
            Index of the operation in the history or None on error
        """
        return await self.record_operation(
            operation_type=OP_FILE_SYSTEM,
            params={
                "file_operation": operation_type,
                **params
            },
            backup_path=backup_path,
            transaction_id=transaction_id,
            step_id=step_id
        )
    
    async def record_content_manipulation(
        self,
        file_path: Union[str, Path],
        original_content: str,
        modified_content: str,
        instruction: Optional[str] = None,
        transaction_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[int]:
        """
        Record a content manipulation operation for potential rollback.
        
        Args:
            file_path: Path to the file that was modified.
            original_content: Original content of the file.
            modified_content: Modified content of the file.
            instruction: The instruction that caused the modification.
            transaction_id: ID of the transaction this operation belongs to.
            step_id: ID of the step in the plan this operation belongs to.
            
        Returns:
            Index of the operation in the history or None on error
        """
        try:
            # Generate diff between original and modified content
            diff = diff_manager.generate_diff(original_content, modified_content)
            
            # Record the operation
            return await self.record_operation(
                operation_type=OP_CONTENT,
                params={
                    "file_path": str(file_path),
                    "instruction": instruction
                },
                transaction_id=transaction_id,
                step_id=step_id,
                undo_info={
                    "diff": diff,
                    "has_changes": original_content != modified_content
                }
            )
        
        except Exception as e:
            logger.error(f"Error recording content manipulation: {str(e)}")
            return None
    
    async def record_command_execution(
        self,
        command: str,
        return_code: int,
        stdout: str,
        stderr: str,
        cwd: Optional[str] = None,
        transaction_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[int]:
        """
        Record a command execution for potential rollback.
        
        Args:
            command: The command that was executed.
            return_code: Return code of the command.
            stdout: Standard output of the command.
            stderr: Standard error of the command.
            cwd: Current working directory when the command was executed.
            transaction_id: ID of the transaction this operation belongs to.
            step_id: ID of the step in the plan this operation belongs to.
            
        Returns:
            Index of the operation in the history or None on error
        """
        try:
            # Determine the compensating action for this command
            compensating_action = await self._identify_compensating_action(
                command=command,
                stdout=stdout,
                stderr=stderr,
                cwd=cwd
            )
            
            # Record the operation
            return await self.record_operation(
                operation_type=OP_COMMAND,
                params={
                    "command": command,
                    "return_code": return_code,
                    "cwd": cwd or str(Path.cwd())
                },
                transaction_id=transaction_id,
                step_id=step_id,
                undo_info={
                    "compensating_action": compensating_action,
                    "stdout": stdout[:1000] if stdout else "",  # Truncate for storage
                    "stderr": stderr[:1000] if stderr else ""   # Truncate for storage
                }
            )
        
        except Exception as e:
            logger.error(f"Error recording command execution: {str(e)}")
            return None
    
    async def record_plan_execution(
        self,
        plan_id: str,
        goal: str,
        plan_data: Dict[str, Any],
        transaction_id: Optional[str] = None
    ) -> Optional[int]:
        """
        Record a plan execution for potential rollback.
        
        Args:
            plan_id: ID of the plan that was executed.
            goal: Goal of the plan.
            plan_data: Plan data structure.
            transaction_id: ID of the transaction this operation belongs to.
            
        Returns:
            Index of the operation in the history or None on error
        """
        try:
            # Record the operation
            return await self.record_operation(
                operation_type=OP_PLAN,
                params={
                    "plan_id": plan_id,
                    "goal": goal
                },
                transaction_id=transaction_id,
                undo_info={
                    "plan_data": plan_data
                }
            )
        
        except Exception as e:
            logger.error(f"Error recording plan execution: {str(e)}")
            return None
    
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
                
                # Determine if the operation can be rolled back
                can_rollback = bool(op.backup_path) or op.operation_type in [OP_CONTENT, OP_COMMAND]
                
                # Get transaction info if available
                transaction_info = None
                if op.transaction_id:
                    if op.transaction_id in self._transactions:
                        transaction = self._transactions[op.transaction_id]
                        transaction_info = {
                            "id": transaction.transaction_id,
                            "description": transaction.description,
                            "status": transaction.status
                        }
                    elif op.transaction_id in self._active_transactions:
                        transaction = self._active_transactions[op.transaction_id]
                        transaction_info = {
                            "id": transaction.transaction_id,
                            "description": transaction.description,
                            "status": transaction.status
                        }
                
                result.append({
                    "id": len(self._operations) - i - 1,  # Original index in the full list
                    "timestamp": op.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "operation_type": op.operation_type,
                    "description": description,
                    "can_rollback": can_rollback,
                    "transaction": transaction_info
                })
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting recent operations: {str(e)}")
            return []
    
    async def get_recent_transactions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get a list of recent transactions that can be rolled back.
        
        Args:
            limit: Maximum number of transactions to return.
            
        Returns:
            A list of transaction details.
        """
        try:
            # Combine active and completed transactions
            all_transactions = list(self._transactions.values()) + list(self._active_transactions.values())
            
            # Sort by timestamp (newest first)
            all_transactions.sort(key=lambda t: t.timestamp, reverse=True)
            
            # Take only the most recent up to the limit
            recent = all_transactions[:limit]
            
            # Convert to a more user-friendly format
            result = []
            for transaction in recent:
                # Count operations in this transaction
                operation_count = len(transaction.operation_ids)
                
                # Determine if the transaction can be rolled back
                can_rollback = transaction.status == "completed" and operation_count > 0
                
                result.append({
                    "id": transaction.transaction_id,
                    "timestamp": transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "description": transaction.description,
                    "status": transaction.status,
                    "operation_count": operation_count,
                    "can_rollback": can_rollback
                })
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting recent transactions: {str(e)}")
            return []
    
    def _get_operation_description(self, op: OperationRecord) -> str:
        """Generate a human-readable description of an operation."""
        try:
            if op.operation_type == OP_FILE_SYSTEM:
                file_operation = op.params.get("file_operation", "unknown")
                
                if file_operation == "create_file":
                    return f"Created file: {op.params.get('path', 'unknown')}"
                
                elif file_operation == "write_file":
                    return f"Wrote to file: {op.params.get('path', 'unknown')}"
                
                elif file_operation == "delete_file":
                    return f"Deleted file: {op.params.get('path', 'unknown')}"
                
                elif file_operation == "create_directory":
                    return f"Created directory: {op.params.get('path', 'unknown')}"
                
                elif file_operation == "delete_directory":
                    return f"Deleted directory: {op.params.get('path', 'unknown')}"
                
                elif file_operation == "copy_file":
                    return f"Copied file from {op.params.get('source', 'unknown')} to {op.params.get('destination', 'unknown')}"
                
                elif file_operation == "move_file":
                    return f"Moved file from {op.params.get('source', 'unknown')} to {op.params.get('destination', 'unknown')}"
                
                else:
                    return f"{file_operation}: {op.params}"
            
            elif op.operation_type == OP_CONTENT:
                file_path = op.params.get("file_path", "unknown")
                instruction = op.params.get("instruction", "Modified content")
                return f"Modified content of {file_path}: {instruction}"
            
            elif op.operation_type == OP_COMMAND:
                command = op.params.get("command", "unknown")
                return f"Executed command: {command}"
            
            elif op.operation_type == OP_PLAN:
                goal = op.params.get("goal", "unknown")
                return f"Executed plan: {goal}"
            
            else:
                return f"{op.operation_type}: {op.params}"
                
        except Exception as e:
            logger.error(f"Error generating operation description: {str(e)}")
            return "Unknown operation"
    
    async def _identify_compensating_action(
        self,
        command: str,
        stdout: str,
        stderr: str,
        cwd: Optional[str] = None
    ) -> Optional[str]:
        """
        Identify a compensating action for a command.
        
        Args:
            command: The command that was executed.
            stdout: Standard output of the command.
            stderr: Standard error of the command.
            cwd: Current working directory when the command was executed.
            
        Returns:
            Compensating action command or None if not available.
        """
        try:
            # Parse the command
            tokens = shlex.split(command)
            if not tokens:
                return None
            
            base_cmd = tokens[0]
            
            # Check for common commands with known compensations
            for cmd_pattern, compensation in self._command_compensations.items():
                if command.startswith(cmd_pattern):
                    # Extract arguments to construct the compensation
                    args = tokens[len(cmd_pattern.split()):]
                    if not args:
                        continue
                    
                    # Special handling for different command types
                    if cmd_pattern == "git add":
                        # git reset <files>
                        return f"{compensation} {' '.join(args)}"
                    
                    elif cmd_pattern == "git push":
                        # Extract branch from command or use current branch
                        branch = None
                        for i, arg in enumerate(tokens):
                            if i > 0 and arg not in ["-f", "--force", "-u", "--set-upstream"]:
                                branch = arg
                                break
                        
                        if not branch:
                            # Get current branch
                            branch = "$(git rev-parse --abbrev-ref HEAD)"
                        
                        # Substitute ${branch} in the compensation
                        return compensation.replace("${branch}", branch)
                    
                    elif cmd_pattern in ["npm install", "pip install", "apt-get install"]:
                        # Extract package names, skipping flags
                        packages = []
                        for arg in args:
                            if not arg.startswith("-"):
                                packages.append(arg)
                        
                        if packages:
                            return f"{compensation} {' '.join(packages)}"
                    
                    else:
                        # Generic compensation with all arguments
                        return f"{compensation} {' '.join(args)}"
            
            # No known compensation found
            return None
            
        except Exception as e:
            logger.error(f"Error identifying compensating action: {str(e)}")
            return None
    
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
            
            # Roll back based on operation type
            if op.operation_type == OP_FILE_SYSTEM:
                success = await self._rollback_file_operation(op)
            elif op.operation_type == OP_CONTENT:
                success = await self._rollback_content_manipulation(op)
            elif op.operation_type == OP_COMMAND:
                success = await self._rollback_command_execution(op)
            elif op.operation_type == OP_PLAN:
                success = await self._rollback_plan_execution(op)
            else:
                logger.error(f"Unsupported operation type for rollback: {op.operation_type}")
                return False
            
            # If rollback was successful, update the operations list
            if success:
                # If this operation is part of a transaction, we don't remove it here
                # Instead, we'll handle it in rollback_transaction
                if not op.transaction_id:
                    self._operations = self._operations[:operation_id]
                    self._save_history(self._operations)
                
                logger.info(f"Successfully rolled back operation {operation_id}: {op.operation_type}")
                return True
            else:
                logger.error(f"Failed to roll back operation {operation_id}: {op.operation_type}")
                return False
                
        except Exception as e:
            logger.exception(f"Error rolling back operation {operation_id}: {str(e)}")
            return False
    
    async def _rollback_file_operation(self, op: OperationRecord) -> bool:
        """
        Roll back a file system operation.
        
        Args:
            op: The operation record.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            file_operation = op.params.get("file_operation")
            
            if file_operation == "create_file":
                # For file creation, delete the created file
                path = Path(op.params.get("path", ""))
                if path.exists() and path.is_file():
                    path.unlink()
                    logger.info(f"Rolled back file creation: {path}")
                    return True
                else:
                    logger.warning(f"File no longer exists: {path}")
                    return True  # Consider it success if file is already gone
            
            elif file_operation in ["write_file", "delete_file"]:
                # For file writing/deletion, restore from backup
                path = Path(op.params.get("path", ""))
                backup_path = op.backup_path
                
                if not backup_path:
                    logger.error(f"No backup path for {file_operation} operation")
                    return False
                
                backup_path_obj = Path(backup_path)
                if not backup_path_obj.exists():
                    logger.error(f"Backup file not found: {backup_path}")
                    return False
                
                # Create parent directory if it doesn't exist
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Restore the file
                shutil.copy2(backup_path_obj, path)
                logger.info(f"Restored file from backup: {path}")
                return True
            
            elif file_operation == "create_directory":
                # For directory creation, delete the created directory
                path = Path(op.params.get("path", ""))
                if path.exists() and path.is_dir():
                    # Use rmtree to handle non-empty directories
                    shutil.rmtree(path)
                    logger.info(f"Rolled back directory creation: {path}")
                    return True
                else:
                    logger.warning(f"Directory no longer exists: {path}")
                    return True  # Consider it success if directory is already gone
            
            elif file_operation == "delete_directory":
                # For directory deletion, restore from backup
                path = Path(op.params.get("path", ""))
                backup_path = op.backup_path
                
                if not backup_path:
                    logger.error(f"No backup path for {file_operation} operation")
                    return False
                
                backup_path_obj = Path(backup_path)
                if not backup_path_obj.exists():
                    logger.error(f"Backup directory not found: {backup_path}")
                    return False
                
                # Create parent directory if it doesn't exist
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Restore the directory
                if path.exists():
                    shutil.rmtree(path)  # Remove existing directory first
                shutil.copytree(backup_path_obj, path)
                logger.info(f"Restored directory from backup: {path}")
                return True
            
            elif file_operation in ["copy_file", "move_file"]:
                # For copy/move, multiple files may need to be restored
                destination = Path(op.params.get("destination", ""))
                backup_path = op.backup_path
                
                if not backup_path:
                    logger.error(f"No backup path for {file_operation} operation")
                    return False
                
                # Restore the destination if it was overwritten
                if destination.exists() and backup_path:
                    backup_path_obj = Path(backup_path)
                    if backup_path_obj.exists():
                        if backup_path_obj.is_file():
                            shutil.copy2(backup_path_obj, destination)
                            logger.info(f"Restored destination file: {destination}")
                        else:
                            shutil.rmtree(destination, ignore_errors=True)
                            shutil.copytree(backup_path_obj, destination)
                            logger.info(f"Restored destination directory: {destination}")
                
                # For move operations, also delete the destination
                if file_operation == "move_file":
                    source = Path(op.params.get("source", ""))
                    if destination.exists():
                        # Restore the source copy if available
                        if source.exists():
                            logger.warning(f"Source already exists, not restoring: {source}")
                        else:
                            # Create parent directory if needed
                            source.parent.mkdir(parents=True, exist_ok=True)
                            
                            if destination.is_file():
                                # Copy destination back to source
                                shutil.copy2(destination, source)
                                logger.info(f"Restored source file: {source}")
                            else:
                                # Copy directory
                                shutil.copytree(destination, source)
                                logger.info(f"Restored source directory: {source}")
                        
                        # Remove destination
                        if destination.is_file():
                            destination.unlink()
                        else:
                            shutil.rmtree(destination)
                        logger.info(f"Removed destination: {destination}")
                
                return True
            
            else:
                logger.error(f"Unsupported file operation for rollback: {file_operation}")
                return False
                
        except Exception as e:
            logger.exception(f"Error rolling back file operation: {str(e)}")
            return False
    
    async def _rollback_content_manipulation(self, op: OperationRecord) -> bool:
        """
        Roll back a content manipulation operation.
        
        Args:
            op: The operation record.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            file_path = op.params.get("file_path")
            if not file_path:
                logger.error("No file path in content manipulation operation")
                return False
            
            path_obj = Path(file_path)
            if not path_obj.exists() or not path_obj.is_file():
                logger.error(f"File not found: {file_path}")
                return False
            
            # Check if there was a diff
            diff = op.undo_info.get("diff")
            if not diff:
                logger.error("No diff found in content manipulation undo info")
                return False
            
            # Read the current content
            try:
                with open(path_obj, 'r', encoding='utf-8', errors='replace') as f:
                    current_content = f.read()
            except Exception as e:
                logger.error(f"Error reading current file content: {str(e)}")
                return False
            
            # Apply the reversed diff
            # The diff is from original to modified, so we reverse it
            # In this simple approach, we swap "+" and "-" in the diff
            reversed_diff = ""
            for line in diff.splitlines():
                if line.startswith('+'):
                    reversed_diff += '-' + line[1:] + '\n'
                elif line.startswith('-'):
                    reversed_diff += '+' + line[1:] + '\n'
                else:
                    reversed_diff += line + '\n'
            
            # Get diff_manager through API
            diff_manager = get_diff_manager()
            
            # Try to apply the reversed diff
            result, success = diff_manager.apply_diff(current_content, reversed_diff)
            
            if not success:
                logger.error("Failed to apply reversed diff")
                return False
            
            # Write the reverted content back to the file
            try:
                with open(path_obj, 'w', encoding='utf-8') as f:
                    f.write(result)
            except Exception as e:
                logger.error(f"Error writing reverted content: {str(e)}")
                return False
            
            logger.info(f"Successfully rolled back content changes for {file_path}")
            return True
            
        except Exception as e:
            logger.exception(f"Error rolling back content manipulation: {str(e)}")
            return False
    
    async def _rollback_command_execution(self, op: OperationRecord) -> bool:
        """
        Roll back a command execution operation.
        
        Args:
            op: The operation record.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get the compensating action
            compensating_action = op.undo_info.get("compensating_action")
            if not compensating_action:
                logger.warning(f"No compensating action available for command: {op.params.get('command')}")
                return False
            
            # Get the working directory
            cwd = op.params.get("cwd")
            
            # Get execution_engine through API
            execution_engine = get_execution_engine()
            
            # Execute the compensating action
            logger.info(f"Executing compensating action: {compensating_action}")
            stdout, stderr, return_code = await execution_engine.execute_command(
                compensating_action,
                check_safety=False,  # Skip safety checks for compensating actions
                working_dir=cwd
            )
            
            # Check if the compensating action was successful
            if return_code != 0:
                logger.error(f"Compensating action failed: {stderr}")
                return False
            
            logger.info(f"Successfully executed compensating action: {compensating_action}")
            return True
            
        except Exception as e:
            logger.exception(f"Error rolling back command execution: {str(e)}")
            return False
    
    async def _rollback_plan_execution(self, op: OperationRecord) -> bool:
        """
        Roll back a plan execution operation.
        
        Args:
            op: The operation record.
            
        Returns:
            True if successful, False otherwise.
        """
        # For plan execution, there's not much to do at this level
        # as the individual operations within the plan should be rolled back
        logger.info(f"Rolled back plan execution: {op.params.get('goal')}")
        return True
    
    async def rollback_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Roll back all operations in a transaction.
        
        Args:
            transaction_id: ID of the transaction to roll back.
            
        Returns:
            Dictionary with rollback results.
        """
        try:
            # Find the transaction
            if transaction_id in self._transactions:
                transaction = self._transactions[transaction_id]
            elif transaction_id in self._active_transactions:
                transaction = self._active_transactions[transaction_id]
            else:
                return {
                    "success": False,
                    "error": f"Transaction not found: {transaction_id}",
                    "transaction_id": transaction_id
                }
            
            # Collect all operations in this transaction
            operation_ids = transaction.operation_ids
            if not operation_ids:
                logger.warning(f"No operations found in transaction: {transaction_id}")
                return {
                    "success": True,
                    "message": "No operations to roll back",
                    "transaction_id": transaction_id,
                    "rolled_back": 0,
                    "failed": 0
                }
            
            # Sort operations in reverse order (most recent first)
            operation_ids.sort(reverse=True)
            
            # Roll back each operation
            rolled_back = 0
            failed = 0
            results = []
            
            for op_id in operation_ids:
                if op_id >= len(self._operations):
                    logger.error(f"Invalid operation ID in transaction: {op_id}")
                    failed += 1
                    results.append({
                        "operation_id": op_id,
                        "success": False,
                        "error": "Invalid operation ID"
                    })
                    continue
                
                # Roll back this operation
                op = self._operations[op_id]
                description = self._get_operation_description(op)
                
                success = await self.rollback_operation(op_id)
                if success:
                    rolled_back += 1
                    results.append({
                        "operation_id": op_id,
                        "operation_type": op.operation_type,
                        "description": description,
                        "success": True
                    })
                else:
                    failed += 1
                    results.append({
                        "operation_id": op_id,
                        "operation_type": op.operation_type,
                        "description": description,
                        "success": False,
                        "error": "Rollback failed"
                    })
            
            # Update transaction status
            transaction.status = "rolled_back"
            self._save_transaction(transaction)
            
            # Return the results
            return {
                "success": failed == 0,
                "transaction_id": transaction_id,
                "rolled_back": rolled_back,
                "failed": failed,
                "total": len(operation_ids),
                "results": results
            }
            
        except Exception as e:
            logger.exception(f"Error rolling back transaction {transaction_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "transaction_id": transaction_id
            }
    
    async def create_backup_file(self, path: Path) -> Optional[Path]:
        """
        Create a backup of a file for potential rollback.
        
        Args:
            path: The path of the file to back up.
            
        Returns:
            The path of the backup file or None if backup failed.
        """
        try:
            # Ensure backup directory exists
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create a unique backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{path.name}.{timestamp}.bak"
            backup_path = BACKUP_DIR / backup_name
            
            # Copy the file to the backup location
            shutil.copy2(path, backup_path)
            logger.debug(f"Created backup of {path} at {backup_path}")
            
            return backup_path
        
        except Exception as e:
            logger.warning(f"Failed to create backup of {path}: {str(e)}")
            return None
    
    async def create_backup_directory(self, path: Path) -> Optional[Path]:
        """
        Create a backup of a directory for potential rollback.
        
        Args:
            path: The path of the directory to back up.
            
        Returns:
            The path of the backup directory or None if backup failed.
        """
        try:
            # Ensure backup directory exists
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create a unique backup directory name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{path.name}.{timestamp}.bak"
            backup_path = BACKUP_DIR / backup_name
            
            # Copy the directory to the backup location
            shutil.copytree(path, backup_path)
            logger.debug(f"Created backup of directory {path} at {backup_path}")
            
            return backup_path
        
        except Exception as e:
            logger.warning(f"Failed to create backup of directory {path}: {str(e)}")
            return None

# Global rollback manager instance
rollback_manager = RollbackManager()
