"""
Public API for the generation components.

This module provides functions to access generation components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable

from angela.core.registry import registry

# Architecture Analyzer API
def get_architectural_analyzer():
    """Get the architectural analyzer instance."""
    from angela.components.generation.architecture import architectural_analyzer
    return registry.get_or_create("architectural_analyzer", lambda: architectural_analyzer)

def analyze_project_architecture(project_path, context=None):
    """Analyze project architecture wrapper function."""
    from angela.components.generation.architecture import analyze_project_architecture as _analyze
    return _analyze(project_path, context)

# Code Generation Engine API
def get_code_generation_engine():
    """Get the code generation engine instance."""
    from angela.components.generation.engine import code_generation_engine
    return registry.get_or_create("code_generation_engine", lambda: code_generation_engine)

# Documentation Generator API
def get_documentation_generator():
    """Get the documentation generator instance."""
    from angela.components.generation.documentation import documentation_generator
    return registry.get_or_create("documentation_generator", lambda: documentation_generator)

# Framework Generator API
def get_framework_generator():
    """Get the framework generator instance."""
    from angela.components.generation.frameworks import framework_generator
    return registry.get_or_create("framework_generator", lambda: framework_generator)

# Interactive Refiner API
def get_interactive_refiner():
    """Get the interactive refiner instance."""
    from angela.components.generation.refiner import interactive_refiner
    return registry.get_or_create("interactive_refiner", lambda: interactive_refiner)

# Project Planner API
def get_project_planner():
    """Get the project planner instance."""
    from angela.components.generation.planner import project_planner
    return registry.get_or_create("project_planner", lambda: project_planner)

# Generation Context Manager API
def get_generation_context_manager():
    """Get the generation context manager instance."""
    from angela.components.generation.context_manager import generation_context_manager
    return registry.get_or_create("generation_context_manager", lambda: generation_context_manager)

# Code Validator API
def validate_code(content, file_path):
    """Validate code wrapper function."""
    from angela.components.generation.validators import validate_code as _validate
    return _validate(content, file_path)

# Models
def get_code_file_class():
    """Get the CodeFile class."""
    from angela.components.generation.models import CodeFile
    return CodeFile

def get_code_project_class():
    """Get the CodeProject class."""
    from angela.components.generation.models import CodeProject
    return CodeProject

def get_project_architecture_class():
    """Get the ProjectArchitecture class."""
    from angela.components.generation.planner import ProjectArchitecture
    return ProjectArchitecture
