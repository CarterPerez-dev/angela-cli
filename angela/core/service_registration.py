# angela/core/service_registration.py
"""Service registration for Angela CLI.

This module handles the registration of core services with the central registry.
It resolves circular import dependencies by importing services at registration time.
"""
from angela.core.registry import registry
from angela.utils.logging import get_logger

logger = get_logger(__name__)

def register_core_services():
    """Register all core services with the registry."""
    logger.info("Registering core services")

    # Register context enhancer if available
    try:
        from angela.context.enhancer import context_enhancer
        if context_enhancer is None:
            logger.error("context_enhancer is None after import, attempting to recreate")
            from angela.context.enhancer import ContextEnhancer
            context_enhancer = ContextEnhancer()
        
        registry.register("context_enhancer", context_enhancer)
        logger.debug(f"Registered context_enhancer: {type(context_enhancer).__name__}")
    except ImportError as e:
        logger.error(f"Could not import context_enhancer: {e}")
        try:
            from angela.context.enhancer import ContextEnhancer
            temp_enhancer = ContextEnhancer()
            registry.register("context_enhancer", temp_enhancer)
            logger.info("Created and registered new context_enhancer instance")
        except Exception as inner_e:
            logger.critical(f"Failed to create alternative context_enhancer: {inner_e}")

    # Register essential components
    try:
        from angela.execution.engine import execution_engine
        registry.register("execution_engine", execution_engine)
        logger.debug("Registered execution_engine")
    except ImportError as e:
        logger.warning(f"Could not import execution_engine: {e}")

    try:
        from angela.execution.adaptive_engine import adaptive_engine
        registry.register("adaptive_engine", adaptive_engine)
        logger.debug("Registered adaptive_engine")
    except ImportError as e:
        logger.warning(f"Could not import adaptive_engine: {e}")

    try:
        from angela.safety import check_command_safety, validate_command_safety
        registry.register("check_command_safety", check_command_safety)
        registry.register("validate_command_safety", validate_command_safety)
        logger.debug("Registered safety functions")
    except ImportError as e:
        logger.warning(f"Could not import safety functions: {e}")

    try:
        from angela.orchestrator import orchestrator
        registry.register("orchestrator", orchestrator)
        logger.debug("Registered orchestrator")
    except ImportError as e:
        logger.warning(f"Could not import orchestrator: {e}")

    # Register execution hooks
    try:
        from angela.execution.hooks import execution_hooks
        registry.register("execution_hooks", execution_hooks)
        logger.debug("Registered execution_hooks")
    except ImportError as e:
        logger.warning(f"Could not import execution_hooks: {e}")

    # Register error recovery manager
    try:
        from angela.execution.error_recovery import ErrorRecoveryManager
        error_recovery_manager = ErrorRecoveryManager()
        registry.register("error_recovery_manager", error_recovery_manager)
        logger.debug("Registered error_recovery_manager")
    except ImportError as e:
        logger.warning(f"Could not import ErrorRecoveryManager: {e}")

    # Register enhanced task planner
    try:
        from angela.intent.enhanced_task_planner import enhanced_task_planner
        registry.register("enhanced_task_planner", enhanced_task_planner)
        logger.debug("Registered enhanced_task_planner")
    except ImportError as e:
        logger.warning(f"Could not import enhanced_task_planner: {e}")
        try:
            # Alternative import from planner as fallback
            from angela.intent.planner import task_planner
            registry.register("enhanced_task_planner", task_planner)
            logger.info("Registered task_planner as fallback for enhanced_task_planner")
        except ImportError:
            logger.error("Could not register any task planner")

    # Register universal CLI translator
    try:
        from angela.toolchain.universal_cli import universal_cli_translator
        
        # Check if the instance was properly initialized
        if universal_cli_translator is None:
            from angela.toolchain.universal_cli import UniversalCLITranslator
            universal_cli_translator_instance = UniversalCLITranslator()
            registry.register("universal_cli_translator", universal_cli_translator_instance)
            logger.info("Created and registered new universal_cli_translator instance")
        else:
            registry.register("universal_cli_translator", universal_cli_translator)
            logger.info("Successfully registered existing universal_cli_translator")
            
    except ImportError as e:
        logger.error(f"Could not import universal_cli_translator: {e}")


    # Register complex workflow planner
    try:
        from angela.intent.complex_workflow_planner import complex_workflow_planner
        registry.register("complex_workflow_planner", complex_workflow_planner)
        logger.debug("Registered complex_workflow_planner")
    except ImportError as e:
        logger.warning(f"Could not import complex_workflow_planner: {e}")

    # Register CI/CD integration
    try:
        from angela.toolchain.ci_cd import ci_cd_integration
        registry.register("ci_cd_integration", ci_cd_integration)
        logger.debug("Registered ci_cd_integration")
    except ImportError as e:
        logger.warning(f"Could not import ci_cd_integration: {e}")

    # Register Docker integration
    try:
        from angela.toolchain.docker import docker_integration
        registry.register("docker_integration", docker_integration)
        logger.debug("Registered docker_integration")
    except ImportError as e:
        logger.warning(f"Could not import docker_integration: {e}")

    # Register file resolver
    try:
        from angela.context.file_resolver import file_resolver
        registry.register("file_resolver", file_resolver)
        logger.debug("Registered file_resolver")
    except ImportError as e:
        logger.warning(f"Could not import file_resolver: {e}")

    # Register rollback manager
    try:
        from angela.execution.rollback import rollback_manager
        registry.register("rollback_manager", rollback_manager)
        logger.debug("Registered rollback_manager")
    except ImportError as e:
        logger.warning(f"Could not import rollback_manager: {e}")

    logger.info("Core services registration complete")
