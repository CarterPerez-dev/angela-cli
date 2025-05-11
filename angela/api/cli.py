"""
Public API for CLI components.

This module provides functions to access CLI components with lazy initialization.
"""
from typing import Optional, Any, Dict
import typer

from angela.core.registry import registry

# Import CLI apps but don't expose them directly
from angela.components.cli.main import app as main_app
from angela.components.cli.files import app as files_app
from angela.components.cli.workflows import app as workflows_app
from angela.components.cli.generation import app as generation_app
from angela.components.cli.docker import app as docker_app
from angela.components.execution.rollback_commands import app as rollback_app

# Main CLI App
def get_main_app():
    """Get the main CLI app instance."""
    return registry.get_or_create("main_app", typer.Typer, factory=lambda: main_app)

def get_files_app():
    """Get the files CLI app instance."""
    return registry.get_or_create("files_app", typer.Typer, factory=lambda: files_app)

def get_workflows_app():
    """Get the workflows CLI app instance."""
    return registry.get_or_create("workflows_app", typer.Typer, factory=lambda: workflows_app)

def get_generation_app():
    """Get the generation CLI app instance."""
    return registry.get_or_create("generation_app", typer.Typer, factory=lambda: generation_app)

def get_docker_app():
    """Get the docker CLI app instance."""
    return registry.get_or_create("docker_app", typer.Typer, factory=lambda: docker_app)

def get_rollback_app():
    """Get the rollback commands CLI app instance."""
    return registry.get_or_create("rollback_app", typer.Typer, factory=lambda: rollback_app)

# Unified App Interface
def get_app():
    """
    Get the complete CLI app with all subcommands registered.
    
    This is the main entry point for the CLI interface.
    """
    # Retrieve (or create) the main app
    app = get_main_app()
    
    # Add subcommands if they're not already registered
    _ensure_subcommands_registered(app)
    
    return app

def _ensure_subcommands_registered(app):
    """
    Ensure all subcommands are registered with the main app.
    
    This function checks the app's registered commands and adds
    any missing subcommands.
    """
    # Get the subcommand typer apps
    files = get_files_app()
    workflows = get_workflows_app() 
    generation = get_generation_app()
    docker = get_docker_app()
    rollback = get_rollback_app()
    
    # Check if subcommands are already registered
    registered_commands = getattr(app, "registered_commands", {})
    
    # Add each subcommand if not already registered
    if "files" not in registered_commands:
        app.add_typer(files, name="files", help="File and directory operations")
    
    if "workflows" not in registered_commands:
        app.add_typer(workflows, name="workflows", help="Workflow management")
    
    if "generate" not in registered_commands:
        app.add_typer(generation, name="generate", help="Code generation")
    
    if "rollback" not in registered_commands:
        app.add_typer(rollback, name="rollback", help="Rollback operations and transactions")
    
    if "docker" not in registered_commands:
        app.add_typer(docker, name="docker", help="Docker and Docker Compose operations")
        
        
app = get_app()        
