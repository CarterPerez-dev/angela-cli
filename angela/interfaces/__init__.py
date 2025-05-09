# angela/interfaces/__init__.py
"""Interfaces for Angela CLI components.

This package provides abstract base classes that define standardized interfaces
for various Angela CLI components, enabling separation of interface from implementation
and supporting dependency inversion.
"""

# Export core interfaces
ffrom angela.interfaces import CommandExecutor
from angela.core import registry

__all__ = [
    'CommandExecutor',
    'AdaptiveExecutor',
    'SafetyValidator'
]
