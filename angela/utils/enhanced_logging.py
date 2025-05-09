# angela/utils/enhanced_logging.py
import json
import inspect
import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union

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
    
    def clear_context(self) -> None:
        """Clear all context information."""
        self._context.clear()
    
    def with_context(self, **context) -> 'EnhancedLogger':
        """Create a new logger with added context."""
        new_logger = EnhancedLogger(self._logger.name)
        new_logger._context = {**self._context, **context}
        return new_logger
    
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
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log a debug message with context."""
        extra = kwargs.pop("extra", {})
        self._logger.debug(self._format_message(msg, extra), *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """Log an info message with context."""
        extra = kwargs.pop("extra", {})
        self._logger.info(self._format_message(msg, extra), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message with context."""
        extra = kwargs.pop("extra", {})
        self._logger.warning(self._format_message(msg, extra), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """Log an error message with context."""
        extra = kwargs.pop("extra", {})
        self._logger.error(self._format_message(msg, extra), *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log a critical message with context."""
        extra = kwargs.pop("extra", {})
        self._logger.critical(self._format_message(msg, extra), *args, **kwargs)
    
    def exception(self, msg: str, exc_info: Union[bool, BaseException] = True, 
                 *args, **kwargs) -> None:
        """Log an exception with context."""
        extra = kwargs.pop("extra", {})
        # Add exception info to context
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_type = type(exc_info).__name__
                exc_message = str(exc_info)
            else:
                exc_info = sys.exc_info()
                exc_type = exc_info[0].__name__ if exc_info[0] else "Unknown"
                exc_message = str(exc_info[1]) if exc_info[1] else ""
            
            exception_context = {
                "exception_type": exc_type,
                "exception_message": exc_message,
                "traceback": traceback.format_exc()
            }
            if not extra:
                extra = {}
            extra["exception"] = exception_context
            
        self._logger.exception(self._format_message(msg, extra), *args, **kwargs)
    
    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log a message with the specified level."""
        extra = kwargs.pop("extra", {})
        self._logger.log(level, self._format_message(msg, extra), *args, **kwargs)

    @property
    def name(self) -> str:
        """Get the logger name."""
        return self._logger.name
    
    @property
    def level(self) -> int:
        """Get the logger level."""
        return self._logger.level
    
    @level.setter
    def level(self, level: int) -> None:
        """Set the logger level."""
        self._logger.setLevel(level)
