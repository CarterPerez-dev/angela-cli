# angela/cli/__init__.py
"""
CLI forwarding module for Angela CLI.

This module re-exports CLI components for backward compatibility.
"""
from angela.components.cli import app, main_app, files_app, workflows_app, generation_app, docker_app

__all__ = ['app', 'main_app', 'files_app', 'workflows_app', 'generation_app', 'docker_app']
