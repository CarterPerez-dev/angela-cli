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
    check_dependencies()
    
    # Initialize core registry
    from angela.core.registry import registry    
    
    # REMOVE THIS BLOCK - Let service_registration handle context_enhancer
    # try:
    #     from angela.context.enhancer import context_enhancer
    #     registry.register("context_enhancer", context_enhancer)
    #     logger.debug("Successfully pre-registered context_enhancer")
    # except Exception as e:
    #     logger.error(f"Failed to pre-register context_enhancer: {str(e)}")
        
    # Register core services first, since other components depend on them
    from angela.core.service_registration import register_core_services
    register_core_services() # This will handle context_enhancer registration
    
    # Import services AFTER they are registered by register_core_services if needed locally
    from angela.execution.engine import execution_engine
    from angela.execution.adaptive_engine import adaptive_engine
    from angela.safety import check_command_safety, validate_command_safety
    from angela.orchestrator import orchestrator
    # It's generally better to get these from the registry if they are needed here,
    # rather than re-importing directly after registration.
    # For example: context_enhancer_instance = registry.get("context_enhancer")

    # These re-registrations might be redundant if register_core_services does its job.
    # If context_enhancer was removed above, this line would cause a NameError.
    # Consider if these are necessary or if you should fetch from registry and re-register
    # only if missing (which is what Orchestrator's fallback does).
    # For now, to fix the potential NameError, ensure 'context_enhancer' is defined
    # or remove these re-registrations.
    # A safer approach:
    current_ce = registry.get("context_enhancer")
    if current_ce: # Only re-register if it was successfully registered by service_registration
        registry.register("context_enhancer", current_ce)
    else:
        # This case should ideally be handled by register_core_services failing loudly
        # or by Orchestrator's fallback.
        logger.warning("context_enhancer not in registry after service_registration for re-registration in init_application")


    # registry.register("context_enhancer", context_enhancer) # REMOVE or make conditional
    registry.register("execution_engine", execution_engine)
    registry.register("adaptive_engine", adaptive_engine)
    registry.register("check_command_safety", check_command_safety)
    registry.register("validate_command_safety", validate_command_safety)
    registry.register("orchestrator", orchestrator)
    # registry.register("context_enhancer", context_enhancer) # REMOVE or make conditional

    # ... (rest of your init_application)
    
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
        
        
        
    from angela.core.registry import registry
    critical_services = [
        "universal_cli_translator",
        "execution_engine",
        "adaptive_engine",
        # Add other critical services here
    ]
    
    missing_services = []
    for service_name in critical_services:
        if registry.get(service_name) is None:
            missing_services.append(service_name)
    
    if missing_services:
        from angela.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"CRITICAL ERROR: The following essential services are missing: {', '.join(missing_services)}")
        logger.error("Application functionality will be severely limited")
        
        # Attempt to register missing services as a last resort
        for service_name in missing_services:
            if service_name == "universal_cli_translator":
                try:
                    from angela.toolchain.universal_cli import universal_cli_translator, UniversalCLITranslator
                    if universal_cli_translator is None:
                        universal_cli_translator = UniversalCLITranslator()
                    registry.register("universal_cli_translator", universal_cli_translator)
                    logger.info(f"Emergency registration of {service_name} successful")
                except Exception as e:
                    logger.error(f"Emergency registration failed for {service_name}: {e}")        
