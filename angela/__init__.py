# angela/__init__.py
"""
Angela CLI: AI-powered command-line assistant integrated into your terminal shell.
The main package initialization
"""

__version__ = '0.1.0'

def init_application():
    """Initialize all application components."""
    # Import components here to avoid early imports during module loading
    from angela.execution.engine import execution_engine
    from angela.execution.adaptive_engine import adaptive_engine
    from angela.safety import check_command_safety, validate_command_safety
    from angela.orchestrator import orchestrator
    from angela.toolchain.docker import docker_integration
    from angela.generation.context_manager import generation_context_manager
    from angela.generation.refiner import interactive_refiner    
    from angela.integrations.enhanced_planner_integration import apply_enhanced_planner_integration
    from angela.core.registry import registry  # Explicit import for clarity
    
    # This import might be missing, let's check if it exists
    try:
        from angela.integrations.semantic_integration import apply_semantic_integration
        has_semantic_integration = True
    except ImportError:
        has_semantic_integration = False
    
    from angela.context.enhancer import context_enhancer    
    
    # Register core services
    registry.register("execution_engine", execution_engine)
    registry.register("adaptive_engine", adaptive_engine)
    registry.register("check_command_safety", check_command_safety)
    registry.register("validate_command_safety", validate_command_safety)
    registry.register("orchestrator", orchestrator)
    registry.register("context_enhancer", context_enhancer)
    registry.register("docker_integration", docker_integration)
    registry.register("generation_context_manager", generation_context_manager)
    registry.register("interactive_refiner", interactive_refiner)
    
    # Apply integrations
    apply_enhanced_planner_integration()
    
    # Apply semantic integration if available
    if has_semantic_integration:
        apply_semantic_integration()
