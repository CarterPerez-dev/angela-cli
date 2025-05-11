# angela/api/__init__.py
"""
Public API for Angela CLI.

This module provides a clean, stable interface to access all Angela CLI components.
Each sub-module provides access to a specific category of functionality.
"""

# Import all API modules to make them available through the API package
from angela.api import cli
from angela.api import ai
from angela.api import context
from angela.api import execution
from angela.api import generation
from angela.api import intent
from angela.api import monitoring
from angela.api import review
from angela.api import safety
from angela.api import shell
from angela.api import toolchain
from angela.api import workflows
from angela.api import interfaces

# Define the public API
__all__ = [
    'cli',
    'ai',
    'context',
    'execution',
    'generation',
    'intent',
    'interfaces',
    'monitoring',
    'review',
    'safety',
    'shell',
    'toolchain',
    'workflows'
]
