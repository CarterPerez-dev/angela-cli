# angela/utils/enhanced_logging.py
import json
import inspect
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class EnhancedLogger:
    """Enhanced logger with context tracking and structured output."""
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
    
    def add_context(self, key: str, value: Any) -> None:
        """Add context information for subsequent log messages."""
        self._context[key] = value
    
    def remove_context(self, key: str) -> None:
        """Remove context information."""
        if key in self._context:
            del self._context[key]
    
    def _format_message(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Format message with context information."""
        # Get caller info
        frame = inspect.currentframe().f_back.f_back
        func_name = frame.f_code.co_name
        filename = frame.f_code.co_filename.split('/')[-1]
        lineno = frame.f_lineno
        
        # Combine contexts
        context = {**self._context}
        if extra:
            context.update(extra)
        
        # Create structured log
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "message": msg,
            "context": context,
            "caller": f"{filename}:{func_name}:{lineno}"
        }
        
        return json.dumps(log_data)
    
    def debug(self, msg: str, *args, **kwargs):
        """Log a debug message with context."""
        extra = kwargs.pop("extra", {})
        self._logger.debug(self._format_message(msg, extra), *args, **kwargs)
    
    # Similar methods for info, warning, error, exception...
