# angela/generation/__init__.py
"""
Generation components for Angela CLI.

This package provides code generation, architecture analysis, and documentation
generation capabilities for creating and managing software projects through:
- Architectural pattern analysis and recommendations
- Documentation generation for projects and APIs
- Code generation for multiple languages and frameworks
- Framework-specific project scaffolding
- Code validation and refinement capabilities
"""

# Export the main components from each module
from .architecture import architectural_analyzer, analyze_project_architecture
from .documentation import documentation_generator
from .engine import code_generation_engine, CodeFile, CodeProject
from .frameworks import framework_generator
from .validators import validate_code
from .refiner import interactive_refiner
from .planner import project_planner, ProjectArchitecture

# Try to import generation_context_manager
# Note: context_manager.py is referenced by several modules but wasn't visible
# in the provided files. Attempting to import it conditionally.
try:
    from .context_manager import generation_context_manager
    _has_context_manager = True
except ImportError:
    _has_context_manager = False

# Define the public API
__all__ = [
    # Architecture analysis
    'architectural_analyzer',
    'analyze_project_architecture',
    
    # Documentation generation
    'documentation_generator',
    
    # Code generation
    'code_generation_engine',
    'CodeFile',
    'CodeProject',
    
    # Framework generators
    'framework_generator',
    
    # Code validation
    'validate_code',
    
    # Code refinement
    'interactive_refiner',
    
    # Project planning
    'project_planner',
    'ProjectArchitecture'
]

# Add generation_context_manager to __all__ if available
if _has_context_manager:
    __all__.append('generation_context_manager')
