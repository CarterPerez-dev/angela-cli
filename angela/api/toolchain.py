# angela/api/toolchain.py
"""
Public API for toolchain components.

This module provides functions to access toolchain components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable

from angela.core.registry import registry

# Git Integration API
def get_git_integration():
    """Get the git integration instance."""
    from angela.components.toolchain.git import GitIntegration, git_integration
    return registry.get_or_create("git_integration", GitIntegration, factory=lambda: git_integration)

# Package Manager Integration API
def get_package_manager_integration():
    """Get the package manager integration instance."""
    from angela.components.toolchain.package_managers import PackageManagerIntegration, package_manager_integration
    return registry.get_or_create("package_manager_integration", PackageManagerIntegration, factory=lambda: package_manager_integration)

# Docker Integration API
def get_docker_integration():
    """Get the docker integration instance."""
    from angela.components.toolchain.docker import DockerIntegration, docker_integration
    return registry.get_or_create("docker_integration", DockerIntegration, factory=lambda: docker_integration)

# Universal CLI Translator API
def get_universal_cli_translator():
    """Get the universal CLI translator instance."""
    from angela.components.toolchain.universal_cli import UniversalCLITranslator, universal_cli_translator
    return registry.get_or_create("universal_cli_translator", UniversalCLITranslator, factory=lambda: universal_cli_translator)

# CI/CD Integration API
def get_ci_cd_integration():
    """Get the CI/CD integration instance."""
    from angela.components.toolchain.ci_cd import CiCdIntegration, ci_cd_integration
    return registry.get_or_create("ci_cd_integration", CiCdIntegration, factory=lambda: ci_cd_integration)

# Enhanced Universal CLI API
def get_enhanced_universal_cli():
    """Get the enhanced universal CLI instance."""
    from angela.components.toolchain.enhanced_universal_cli import EnhancedUniversalCLI, enhanced_universal_cli
    return registry.get_or_create("enhanced_universal_cli", EnhancedUniversalCLI, factory=lambda: enhanced_universal_cli)

# Cross Tool Workflow Engine API
def get_cross_tool_workflow_engine():
    """Get the cross tool workflow engine instance."""
    from angela.components.toolchain.cross_tool_workflow_engine import CrossToolWorkflowEngine, cross_tool_workflow_engine
    return registry.get_or_create("cross_tool_workflow_engine", CrossToolWorkflowEngine, factory=lambda: cross_tool_workflow_engine)

# Test Framework Integration API
def get_test_framework_integration():
    """Get the test framework integration instance."""
    from angela.components.toolchain.test_frameworks import TestFrameworkIntegration, test_framework_integration
    return registry.get_or_create("test_framework_integration", TestFrameworkIntegration, factory=lambda: test_framework_integration)


def create_cross_tool_workflow(request: str, context: Dict[str, Any], tools: Optional[List[str]] = None) -> Any:
    """
    Create a cross-tool workflow from a natural language request.
    """
    engine = get_cross_tool_workflow_engine() 
    return engine.create_workflow(request, context, tools)

async def execute_cross_tool_workflow(workflow: Any, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a cross-tool workflow.
    """
    engine = get_cross_tool_workflow_engine() # This will get the instance correctly now
    return await engine.execute_workflow(workflow, variables)
