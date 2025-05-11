# angela/api/intent.py
"""
Public API for the intent components.

This module provides functions to access intent components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable

from angela.core.registry import registry

# Intent Models API
def get_intent_model_classes():
    """Get the intent model classes."""
    from angela.components.intent.models import Intent, IntentType, ActionPlan
    return Intent, IntentType, ActionPlan

# Task Planner API
def get_task_planner():
    """Get the task planner instance."""
    from angela.components.intent.planner import TaskPlanner, task_planner 
    return registry.get_or_create("task_planner", TaskPlanner, factory=lambda: task_planner)

# Enhanced Task Planner API
def get_enhanced_task_planner():
    """Get the enhanced task planner instance."""
    from angela.components.intent.enhanced_task_planner import EnhancedTaskPlanner, enhanced_task_planner 
    return registry.get_or_create("enhanced_task_planner", EnhancedTaskPlanner, factory=lambda: enhanced_task_planner)

# Semantic Task Planner API
def get_semantic_task_planner():
    """Get the semantic task planner instance."""
    from angela.components.intent.semantic_task_planner import SemanticTaskPlanner, semantic_task_planner 
    return registry.get_or_create("semantic_task_planner", SemanticTaskPlanner, factory=lambda: semantic_task_planner)

def get_intent_clarification_class():
    """Get the IntentClarification class."""
    from angela.components.intent.semantic_task_planner import IntentClarification
    return IntentClarification

# Complex Workflow Planner API
def get_complex_workflow_planner():
    """Get the complex workflow planner instance."""
    from angela.components.intent.complex_workflow_planner import ComplexWorkflowPlanner, complex_workflow_planner 
    return registry.get_or_create("complex_workflow_planner", ComplexWorkflowPlanner, factory=lambda: complex_workflow_planner)

def get_workflow_step_type_enum():
    """Get the WorkflowStepType enum."""
    from angela.components.intent.complex_workflow_planner import WorkflowStepType
    return WorkflowStepType

def get_complex_workflow_plan_class():
    """Get the ComplexWorkflowPlan class."""
    from angela.components.intent.complex_workflow_planner import ComplexWorkflowPlan
    return ComplexWorkflowPlan


def get_advanced_task_plan_class():
    """Get the AdvancedTaskPlan class."""
    from angela.components.intent.planner import AdvancedTaskPlan
    return AdvancedTaskPlan


def get_plan_step_type_enum():
    """Get the PlanStepType enum."""
    from angela.components.intent.planner import PlanStepType
    return PlanStepType


def get_plan_model_classes():
    """Get the plan model classes."""
    from angela.components.intent.planner import (
        PlanStep, TaskPlan, PlanStepType, AdvancedPlanStep, AdvancedTaskPlan
    )
    return PlanStep, TaskPlan, PlanStepType, AdvancedPlanStep, AdvancedTaskPlan


def create_action_plan(task_plan: Any) -> Any:
    """
    Create an action plan from a task plan.
    
    Args:
        task_plan: The task plan to convert
        
    Returns:
        An ActionPlan ready for execution
    """

    from angela.components.intent.planner import task_planner as base_task_planner
    return base_task_planner.create_action_plan(task_plan)
