# angela/__init__.py (modified)
"""
Angela-CLI: AI-powered command-line assistant integrated into your terminal shell.
"""

from angela.constants import APP_VERSION
from angela.core.registry import registry

__version__ = APP_VERSION

# Initialize the application components
def init_application():
    """Initialize all application components."""
    # Import components here to avoid early imports during module loading
    from angela.execution.engine import execution_engine
    from angela.execution.adaptive_engine import adaptive_engine
    from angela.safety import check_command_safety, validate_command_safety
    from angela.orchestrator import orchestrator
    
    # Register core services
    registry.register("execution_engine", execution_engine)
    registry.register("adaptive_engine", adaptive_engine)
    registry.register("check_command_safety", check_command_safety)
    registry.register("validate_command_safety", validate_command_safety)
    registry.register("orchestrator", orchestrator)

# Don't run initialization during import - it will be called at app startup
