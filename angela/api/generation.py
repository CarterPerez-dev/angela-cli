# angela/api/generation.py
"""
Public API for the generation components.

This module provides functions to access generation components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable

from angela.core.registry import registry

# Import Class types needed for registry.get_or_create cls argument
from angela.components.generation.architecture import ArchitecturalAnalyzer
from angela.components.generation.engine import CodeGenerationEngine
from angela.components.generation.documentation import DocumentationGenerator
from angela.components.generation.frameworks import FrameworkGenerator
from angela.components.generation.refiner import InteractiveRefiner
from angela.components.generation.planner import ProjectPlanner
from angela.components.generation.context_manager import GenerationContextManager
from angela.components.generation.models import CodeFile, CodeProject
from angela.components.generation.planner import ProjectArchitecture 

# Architecture Analyzer API
def get_architectural_analyzer():
    """Get the architectural analyzer instance."""
    from angela.components.generation.architecture import architectural_analyzer as architectural_analyzer_instance
    return registry.get_or_create(
        "architectural_analyzer",
        ArchitecturalAnalyzer,
        factory=lambda: architectural_analyzer_instance
    )

def analyze_project_architecture(project_path, context=None):
    """Analyze project architecture wrapper function."""
    from angela.components.generation.architecture import analyze_project_architecture as _analyze
    return _analyze(project_path, context)

# Code Generation Engine API
def get_code_generation_engine():
    """Get the code generation engine instance."""
    from angela.components.generation.engine import code_generation_engine as code_generation_engine_instance
    return registry.get_or_create(
        "code_generation_engine",
        CodeGenerationEngine,
        factory=lambda: code_generation_engine_instance
    )

# Documentation Generator API
def get_documentation_generator():
    """Get the documentation generator instance."""
    from angela.components.generation.documentation import documentation_generator as documentation_generator_instance
    return registry.get_or_create(
        "documentation_generator",
        DocumentationGenerator,
        factory=lambda: documentation_generator_instance
    )

# Framework Generator API
def get_framework_generator():
    """Get the framework generator instance."""
    from angela.components.generation.frameworks import framework_generator as framework_generator_instance
    return registry.get_or_create(
        "framework_generator",
        FrameworkGenerator,  # Pass the CLASS here
        factory=lambda: framework_generator_instance # Factory returns the INSTANCE
    )

# Interactive Refiner API
def get_interactive_refiner():
    """Get the interactive refiner instance."""
    from angela.components.generation.refiner import interactive_refiner as interactive_refiner_instance
    return registry.get_or_create(
        "interactive_refiner",
        InteractiveRefiner,
        factory=lambda: interactive_refiner_instance
    )

# Project Planner API
def get_project_planner():
    """Get the project planner instance."""
    from angela.components.generation.planner import project_planner as project_planner_instance
    return registry.get_or_create(
        "project_planner",
        ProjectPlanner,
        factory=lambda: project_planner_instance
    )

# Generation Context Manager API
def get_generation_context_manager():
    """Get the generation context manager instance."""
    from angela.components.generation.context_manager import generation_context_manager as generation_context_manager_instance
    return registry.get_or_create(
        "generation_context_manager",
        GenerationContextManager,
        factory=lambda: generation_context_manager_instance
    )

# Code Validator API
def validate_code(content, file_path):
    """Validate code wrapper function."""
    from angela.components.generation.validators import validate_code as _validate
    return _validate(content, file_path)

# Models
def get_code_file_class():
    """Get the CodeFile class."""
    return CodeFile

def get_code_project_class():
    """Get the CodeProject class."""
    return CodeProject

def get_project_architecture_class():
    """Get the ProjectArchitecture class."""
    return ProjectArchitecture
