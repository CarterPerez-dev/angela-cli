# angela/core/service_registration.py - Enhanced implementation

"""
Service registration for Angela CLI.

This module ensures all core services are properly instantiated and registered
with the central service registry.
"""
import traceback
from angela.core.registry import registry
from angela.utils.logging import get_logger

logger = get_logger(__name__)

def register_core_services():
    """Register all core services with the registry."""
    logger.info("Registering core services...")
    
    # First, initialize all service objects
    # 1. Error Recovery Manager
    try:
        from angela.execution.error_recovery import ErrorRecoveryManager
        error_recovery_manager = ErrorRecoveryManager()
        registry.register("error_recovery_manager", error_recovery_manager)
        logger.info("✅ Successfully registered error_recovery_manager")
    except Exception as e:
        logger.error(f"❌ Failed to register error_recovery_manager: {str(e)}")
        logger.error(traceback.format_exc())  # Print full traceback for debugging
    
    # 2. Universal CLI Translator
    try:
        from angela.toolchain.universal_cli import universal_cli_translator
        registry.register("universal_cli_translator", universal_cli_translator)
        logger.info("✅ Successfully registered universal_cli_translator")
    except Exception as e:
        logger.error(f"❌ Failed to register universal_cli_translator: {str(e)}")
        logger.error(traceback.format_exc())
    
    # 3. CI/CD Integration
    try:
        from angela.toolchain.ci_cd import ci_cd_integration
        registry.register("ci_cd_integration", ci_cd_integration)
        logger.debug("Registered ci_cd_integration")
    except Exception as e:
        logger.error(f"Failed to register ci_cd_integration: {str(e)}")
    
    # 4. Complex Workflow Planner
    try:
        from angela.intent.complex_workflow_planner import complex_workflow_planner
        registry.register("complex_workflow_planner", complex_workflow_planner)
        logger.debug("Registered complex_workflow_planner")
    except Exception as e:
        logger.error(f"Failed to register complex_workflow_planner: {str(e)}")
    
    # 5. Proactive Assistant - this depends on execution_hooks having register_hook
    try:
        # First, ensure execution_hooks is available and properly registered
        from angela.execution.hooks import execution_hooks
        registry.register("execution_hooks", execution_hooks)
        logger.debug("Registered execution_hooks")
        
        # Now register proactive assistant
        from angela.monitoring.proactive_assistant import proactive_assistant
        registry.register("proactive_assistant", proactive_assistant)
        logger.debug("Registered proactive_assistant")
    except Exception as e:
        logger.error(f"Failed to register proactive_assistant: {str(e)}")
    
    # Verify registrations
    registered_services = [
        "error_recovery_manager",
        "universal_cli_translator",
        "ci_cd_integration",
        "complex_workflow_planner",
        "execution_hooks",
        "proactive_assistant"
    ]
    
    missing = []
    for service in registered_services:
        if not registry.get(service):
            missing.append(service)
    
    if missing:
        logger.warning(f"Still missing services after registration: {missing}")
    else:
        logger.info("All core services registered successfully")
