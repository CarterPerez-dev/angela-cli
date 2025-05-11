# angela/integrations/__init__.py
"""
Integration modules for Angela CLI.

This package contains modules that integrate different components of the system,
extending functionality and connecting subsystems that would otherwise create
circular dependencies.
"""


from .phase12_integration import phase12_integration


__all__ = ['phase12_integration']
