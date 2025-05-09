# angela/monitoring/__init__.py
"""
Monitoring and proactive assistance for Angela CLI.

This package provides background monitoring capabilities that allow Angela
to offer proactive suggestions and assistance based on system state.
"""

from .background import background_monitor
from .network_monitor import network_monitor
# The proactive_assistant may have circular dependencies, so it's not exported here
# Import it directly when needed

__all__ = ['background_monitor', 'network_monitor']
