# angela/integrations/__init__.py
"""
Integration modules for Angela CLI.

This package contains modules that integrate different components of the system,
extending functionality and connecting subsystems that would otherwise create
circular dependencies.
"""

# These integrations are primarily applied through side effects when imported
# Don't import them here to avoid premature loading
# They're applied from angela/__init__.py (init_application function)

# For components that need to be used directly by others, export them here
from .semantic_integration import semantic_integration
from .phase12_integration import phase12_integration

# Enhanced planner integration is applied through its side effects
# and doesn't need to be directly imported elsewhere

__all__ = ['semantic_integration', 'phase12_integration']
