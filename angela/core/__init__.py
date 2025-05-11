# angela/core/__init__.py
"""
Core infrastructure for Angela CLI.

This module provides the foundation for all Angela components.
"""
from angela.core.registry import registry, singleton_service

__all__ = ['registry', 'singleton_service']
