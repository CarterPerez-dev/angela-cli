# angela/components/intent/__init__.py
"""
Intent components for Angela CLI.

This package provides functionality for understanding user intent,
planning and executing tasks, and orchestrating complex workflows
across multiple levels of abstraction.
"""

# Export core intent models
from angela.components.intent.models import IntentType, Intent, ActionPlan

# Export base planner components
from angela.components.intent.planner import (
    PlanStep, TaskPlan, PlanStepType, 
    AdvancedPlanStep, AdvancedTaskPlan,
    task_planner
)

# Export enhanced planner components - now that we have the API layer, 
# direct imports are safe since they'll be accessed through the API
from angela.components.intent.enhanced_task_planner import EnhancedTaskPlanner, enhanced_task_planner
from angela.components.intent.semantic_task_planner import SemanticTaskPlanner, semantic_task_planner, IntentClarification
from angela.components.intent.complex_workflow_planner import (
    ComplexWorkflowPlanner, complex_workflow_planner, 
    WorkflowStepType, ComplexWorkflowPlan
)

# Define the public API
__all__ = [
    # Core intent models
    'IntentType', 'Intent', 'ActionPlan',
    
    # Base planning components
    'PlanStep', 'TaskPlan', 'PlanStepType', 
    'AdvancedPlanStep', 'AdvancedTaskPlan',
    'task_planner',
    
    # Enhanced planning components
    'EnhancedTaskPlanner', 'enhanced_task_planner',
    'SemanticTaskPlanner', 'semantic_task_planner', 'IntentClarification',
    'ComplexWorkflowPlanner', 'complex_workflow_planner', 
    'WorkflowStepType', 'ComplexWorkflowPlan',
]
