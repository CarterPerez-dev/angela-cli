# angela/__init__.py
"""
Angela CLI: AI-powered command-line assistant integrated into your terminal shell.
The main package initialization
"""
import sys

__version__ = '0.1.0'

def check_dependencies():
    """Check if all required dependencies are installed and warn if any are missing."""
    missing_deps = []
    
    # List of critical packages to check (package_name, import_name)
    dependencies = [
        ("pydantic", "pydantic"),
        ("python-dotenv", "dotenv"),
        ("prompt_toolkit", "prompt_toolkit"),
        ("typer", "typer"),
        ("rich", "rich"),
        # Only check tomli for Python < 3.11, otherwise use tomllib
        ("tomli" if sys.version_info < (3, 11) else "tomllib", 
         "tomli" if sys.version_info < (3, 11) else "tomllib"),
        ("loguru", "loguru"),
        ("google-generativeai", "google.generativeai"),
        ("aiohttp", "aiohttp"),
        ("PyYAML", "yaml"),
    ]
    
    for pkg_name, import_name in dependencies:
        try:
            __import__(import_name)
        except ImportError:
            missing_deps.append(pkg_name)
    
    if missing_deps:
        print(f"\033[31mWarning: Missing dependencies: {', '.join(missing_deps)}\033[0m", file=sys.stderr)
        print(f"\033[31mTo install missing dependencies: pip install {' '.join(missing_deps)}\033[0m", file=sys.stderr)
        print(f"\033[31mOr reinstall Angela with all dependencies: pip install -e .\033[0m", file=sys.stderr)



def init_application():
    """Initialize all application components."""
    # Check dependencies first
    check_dependencies()
    
    # Initialize core registry
    from angela.core.registry import registry

    
    # Register core services first, since other components depend on them
    from angela.core.service_registration import register_core_services
    register_core_services()
    
    from angela.context.enhancer import context_enhancer
    from angela.execution.engine import execution_engine
    from angela.execution.adaptive_engine import adaptive_engine
    from angela.safety import check_command_safety, validate_command_safety
    from angela.orchestrator import orchestrator

    
    # These should be already registered by register_core_services,
    # but let's re-register them to ensure they're available
    registry.register("context_enhancer", context_enhancer)    
    registry.register("execution_engine", execution_engine)
    registry.register("adaptive_engine", adaptive_engine)
    registry.register("check_command_safety", check_command_safety)
    registry.register("validate_command_safety", validate_command_safety)
    registry.register("orchestrator", orchestrator)
    registry.register("context_enhancer", context_enhancer)
    
    # Apply integrations
    from angela.integrations.enhanced_planner_integration import apply_enhanced_planner_integration
    from angela.integrations.semantic_integration import semantic_integration
    
    # Register additional services
    registry.register("semantic_integration", semantic_integration)
    
    # Apply integrations
    apply_enhanced_planner_integration()
    
    # Initialize phase12 (if available)
    try:
        from angela.integrations.phase12_integration import phase12_integration
        import asyncio
        
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule in running loop
            from angela.utils.logging import get_logger
            logger = get_logger(__name__)
            logger.info("Scheduling phase12 initialization in running event loop")
            loop.create_task(phase12_integration.initialize())
        else:
            # Run short async task
            loop.run_until_complete(phase12_integration.initialize())
    except Exception as e:
        from angela.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.warning(f"Could not initialize Phase 12: {str(e)}")
