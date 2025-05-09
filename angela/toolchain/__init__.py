# angela/toolchain/__init__.py
"""
Toolchain components for Angela CLI.

This package provides integrations with various development tools
including package managers, Git, Docker, CI/CD systems, and universal
CLI translation capabilities.
"""

# Git integration
from .git import git_integration

# Package manager integration
from .package_managers import package_manager_integration

# Docker integration
from .docker import docker_integration

# Universal CLI translator
from .unviversal_cli import universal_cli_translator

# CI/CD integration
from .ci_cd import ci_cd_integration

# Enhanced Universal CLI
from .enhanced_universal_cli import enhanced_universal_cli

# Cross-tool workflow engine
from .cross_tool_workflow_engine import cross_tool_workflow_engine

# Define the public API
__all__ = [
    'git_integration',
    'package_manager_integration', 
    'docker_integration',
    'universal_cli_translator',
    'ci_cd_integration',
    'enhanced_universal_cli',
    'cross_tool_workflow_engine'
]
