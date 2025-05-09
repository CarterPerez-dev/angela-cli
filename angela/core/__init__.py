# angela/core/__init__.py
"""Core components for Angela CLI.

This package provides fundamental infrastructure used throughout the application,
including the service registry for dependency management and event bus for
system-wide communication.
"""

# Export core infrastructure components
from .registry import registry, ServiceRegistry
from .events import event_bus, EventBus

__all__ = [
    'registry',
    'ServiceRegistry',
    'event_bus',
    'EventBus'
]
