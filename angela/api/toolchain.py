"""
Public API for toolchain components.

This module provides functions to access toolchain components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable

from angela.core.registry import registry

# Git Integration API
def get_git_integration():
    """Get the git integration instance."""
    from angela.components.toolchain.git import git_integration
    return registry.get_or_create("git_integration", lambda: git_integration)

# Package Manager Integration API
def get_package_manager_integration():
    """Get the package manager integration instance."""
    from angela.components.toolchain.package_managers import package_manager_integration
    return registry.get_or_create("package_manager_integration", lambda: package_manager_integration)

# Docker Integration API
def get_docker_integration():
    """Get the docker integration instance."""
    from angela.components.toolchain.docker import docker_integration
    return registry.get_or_create("docker_integration", lambda: docker_integration)

# Universal CLI Translator API
def get_universal_cli_translator():
    """Get the universal CLI translator instance."""
    from angela.components.toolchain.universal_cli import universal_cli_translator
    return registry.get_or_create("universal_cli_translator", lambda: universal_cli_translator)

# CI/CD Integration API
def get_ci_cd_integration():
    """Get the CI/CD integration instance."""
    from angela.components.toolchain.ci_cd import ci_cd_integration
    return registry.get_or_create("ci_cd_integration", lambda: ci_cd_integration)

# Enhanced Universal CLI API
def get_enhanced_universal_cli():
    """Get the enhanced universal CLI instance."""
    from angela.components.toolchain.enhanced_universal_cli import enhanced_universal_cli
    return registry.get_or_create("enhanced_universal_cli", lambda: enhanced_universal_cli)

# Cross Tool Workflow Engine API
def get_cross_tool_workflow_engine():
    """Get the cross tool workflow engine instance."""
    from angela.components.toolchain.cross_tool_workflow_engine import cross_tool_workflow_engine
    return registry.get_or_create("cross_tool_workflow_engine", lambda: cross_tool_workflow_engine)

# Test Framework Integration API
def get_test_framework_integration():
    """Get the test framework integration instance."""
    from angela.components.toolchain.test_frameworks import test_framework_integration
    return registry.get_or_create("test_framework_integration", lambda: test_framework_integration)

# Helper functions for cross-tool workflows

def create_cross_tool_workflow(request: str, context: Dict[str, Any], tools: Optional[List[str]] = None) -> Any:
    """
    Create a cross-tool workflow from a natural language request.
    
    Args:
        request: Natural language request
        context: Context information
        tools: Optional list of tools to include
        
    Returns:
        A CrossToolWorkflow ready for execution
    """
    engine = get_cross_tool_workflow_engine()
    return engine.create_workflow(request, context, tools)

async def execute_cross_tool_workflow(workflow: Any, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a cross-tool workflow.
    
    Args:
        workflow: The workflow to execute
        variables: Optional initial variables
        
    Returns:
        Dictionary with execution results
    """
    engine = get_cross_tool_workflow_engine()
    return await engine.execute_workflow(workflow, variables)
