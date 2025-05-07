def init_application():
    """Initialize all application components."""
    # Import components here to avoid early imports during module loading
    from angela.execution.engine import execution_engine
    from angela.execution.adaptive_engine import adaptive_engine
    from angela.safety import check_command_safety, validate_command_safety
    from angela.orchestrator import orchestrator
    
    # Import enhanced planner integration (add this line)
    from angela.integrations.enhanced_planner_integration import apply_enhanced_planner_integration
    
    # Register core services
    registry.register("execution_engine", execution_engine)
    registry.register("adaptive_engine", adaptive_engine)
    registry.register("check_command_safety", check_command_safety)
    registry.register("validate_command_safety", validate_command_safety)
    registry.register("orchestrator", orchestrator)
    
    # Apply the enhanced planner integration (add this line)
    apply_enhanced_planner_integration()
