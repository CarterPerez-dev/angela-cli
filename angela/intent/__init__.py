# angela/intent/__init__.py
"""
Intent components for Angela CLI.

This package provides functionality for understanding user intent,
planning and executing tasks, and orchestrating complex workflows
across multiple levels of abstraction.
"""

# Export core intent models
from .models import IntentType, Intent, ActionPlan

# Export base planner components - these should be safe to import directly
from .planner import (
    PlanStep, TaskPlan, PlanStepType, 
    AdvancedPlanStep, AdvancedTaskPlan,
    task_planner
)

# Try to import EnhancedTaskPlanner directly if available
try:
    from .planner import EnhancedTaskPlanner  # This will work after our fix
except ImportError:
    # If not available from planner, we'll try enhanced_task_planner module directly
    try:
        from .enhanced_task_planner import EnhancedTaskPlanner
    except ImportError:
        # Log that it's not available, but don't crash
        import logging
        logging.getLogger(__name__).warning(
            "EnhancedTaskPlanner is not available. Advanced planning features will be limited."
        )
        EnhancedTaskPlanner = None

# Define functions to lazily load components that might cause circular imports
def get_enhanced_task_planner():
    """Get the enhanced task planner lazily to avoid circular imports."""
    try:
        from .enhanced_task_planner import enhanced_task_planner
        return enhanced_task_planner
    except ImportError:
        # Return basic task planner as fallback
        return task_planner

# Export semantic understanding components as lazy functions
def get_semantic_task_planner():
    """Get the semantic task planner lazily to avoid circular imports."""
    from .semantic_task_planner import (
        semantic_task_planner,
        IntentClarification
    )
    return semantic_task_planner

# Export complex workflow planning components as lazy functions
def get_complex_workflow_planner():
    """Get the complex workflow planner lazily to avoid circular imports."""
    from .complex_workflow_planner import (
        WorkflowStepType,
        ComplexWorkflowPlan,
        complex_workflow_planner
    )
    return complex_workflow_planner

# Define the public API
__all__ = [
    # Core intent models
    'IntentType', 'Intent', 'ActionPlan',
    
    # Base planning components
    'PlanStep', 'TaskPlan', 'PlanStepType', 
    'AdvancedPlanStep', 'AdvancedTaskPlan',
    'task_planner',
    
    # Enhanced Task Planner (if available)
    'EnhancedTaskPlanner',
    
    # Lazy loading functions for components with potential circular deps
    'get_enhanced_task_planner',
    'get_semantic_task_planner',
    'get_complex_workflow_planner',
]
