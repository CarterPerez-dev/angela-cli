# angela/core/service_registration.py

"""
Service registration for Angela CLI.

This module ensures all core services are properly instantiated and registered
with the central service registry.
"""

from angela.core.registry import registry
from angela.execution.error_recovery import ErrorRecoveryManager
from angela.toolchain.universal_cli import universal_cli_translator
from angela.intent.complex_workflow_planner import complex_workflow_planner

def register_core_services():
    """Register all core services with the registry."""
    
    # Create error recovery manager if not already registered
    if not registry.get("error_recovery_manager"):
        error_recovery_manager = ErrorRecoveryManager()
        registry.register("error_recovery_manager", error_recovery_manager)
    
    # Register universal CLI translator if not already registered
    if not registry.get("universal_cli_translator"):
        registry.register("universal_cli_translator", universal_cli_translator)
    
    # CI/CD integration is already created in toolchain/ci_cd.py,
    # just need to register it
    from angela.toolchain.ci_cd import ci_cd_integration
    if not registry.get("ci_cd_integration"):
        registry.register("ci_cd_integration", ci_cd_integration)
    
    # Register complex workflow planner if not already registered
    if not registry.get("complex_workflow_planner"):
        registry.register("complex_workflow_planner", complex_workflow_planner)
    
    # Create and register proactive assistant if module is available
    try:
        from angela.monitoring.proactive_assistant import proactive_assistant
        if not registry.get("proactive_assistant"):
            registry.register("proactive_assistant", proactive_assistant)
    except ImportError:
        # This component might be incomplete - log but don't fail
        from angela.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.warning("Proactive assistant module not found. Some advanced features might be unavailable.")
