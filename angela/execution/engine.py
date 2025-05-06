# angela/execution/engine.py
import asyncio
import shlex
import subprocess
from typing import Dict, Any, List, Tuple

from angela.utils.logging import get_logger
from angela.intent.models import ActionPlan

logger = get_logger(__name__)

class ExecutionEngine:
    """Engine for safely executing commands."""
    
    async def execute_command(self, command: str) -> Tuple[str, str, int]:
        """Execute a shell command and return its output."""
        logger.info(f"Executing command: {command}")
        
        try:
            # Split the command properly using shlex
            args = shlex.split(command)
            
            # Execute the command and capture output
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Wait for the command to complete
            stdout_bytes, stderr_bytes = await process.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            logger.debug(f"Command completed with return code: {process.returncode}")
            logger.debug(f"stdout: {stdout[:100]}{'...' if len(stdout) > 100 else ''}")
            if stderr:
                logger.debug(f"stderr: {stderr}")
            
            return stdout, stderr, process.returncode
        
        except Exception as e:
            logger.exception(f"Error executing command '{command}': {str(e)}")
            return "", str(e), -1
    
    async def execute_plan(self, plan: ActionPlan) -> List[Dict[str, Any]]:
        """Execute an action plan and return the results."""
        results = []
        
        for i, command in enumerate(plan.commands):
            stdout, stderr, return_code = await self.execute_command(command)
            
            result = {
                "command": command,
                "explanation": plan.explanations[i] if i < len(plan.explanations) else "",
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "success": return_code == 0
            }
            
            results.append(result)
        
        return results

# Global execution engine instance
execution_engine = ExecutionEngine()
