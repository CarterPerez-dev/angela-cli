# angela/__init__.py
"""
Angela CLI: AI-powered command-line assistant integrated into your terminal shell.
"""

__version__ = '0.1.0'

# Import key functions needed at the top level
from angela.api.cli import app
from angela.core.registry import registry


def init_application():
    """Initialize all application components."""
    # Import and register core components
    from angela.api.cli import get_app
    from angela.api.execution import get_execution_engine, get_adaptive_engine
    from angela.api.safety import get_command_validator
    from angela.api.context import get_context_manager
    from angela.orchestrator import orchestrator
    
    # Register critical components
    registry.register("app", get_app())
    registry.register("execution_engine", get_execution_engine())
    registry.register("adaptive_engine", get_adaptive_engine())
    registry.register("orchestrator", orchestrator)
    
    # Initialize context
    from angela.api.context import initialize_project_inference
    initialize_project_inference()


# Export the main app and initialization function
__all__ = ['app', 'init_application', '__version__']
