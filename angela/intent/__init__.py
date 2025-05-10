# angela/intent/__init__.py
"""
Intent components for Angela CLI.

This package provides functionality for understanding user intent,
planning and executing tasks, and orchestrating complex workflows
across multiple levels of abstraction.
"""

# Export core intent models
from .models import IntentType, Intent, ActionPlan

# Export base planner components
from .planner import (
    PlanStep, TaskPlan, PlanStepType, 
    AdvancedPlanStep, AdvancedTaskPlan,
    task_planner
)

def get_enhanced_task_planner():
    """Get the enhanced task planner lazily to avoid circular imports."""
    from .enhanced_task_planner import enhanced_task_planner
    return enhanced_task_planner

# Export semantic understanding components
# Note: May have circular dependencies with shell.inline_feedback
from .semantic_task_planner import (
    IntentClarification,
    semantic_task_planner
)

# Export complex workflow planning components
from .complex_workflow_planner import (
    WorkflowStepType, ComplexWorkflowPlan,
    complex_workflow_planner
)

# Define the public API
__all__ = [
    # Core intent models
    'IntentType', 'Intent', 'ActionPlan',
    
    # Base planning components
    'PlanStep', 'TaskPlan', 'PlanStepType', 
    'AdvancedPlanStep', 'AdvancedTaskPlan',
    'task_planner',
    
    # Enhanced planning components - CHANGE THIS LINE
    'EnhancedTaskPlanner', 
    'get_enhanced_task_planner',
    
    # Keep the rest of the list the same
    'IntentClarification',
    'semantic_task_planner',
    'WorkflowStepType', 'ComplexWorkflowPlan',
    'complex_workflow_planner',
]
