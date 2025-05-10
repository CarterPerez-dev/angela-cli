# diagnostic.py
import asyncio
import importlib
import sys
import traceback
from angela import init_application
from angela.core.registry import registry
from angela.utils.logging import setup_logging, get_logger

async def diagnose_services():
    # Set up logging
    setup_logging(debug=True)
    logger = get_logger("diagnostics")
    
    logger.info("=== Angela CLI Service Diagnostic Tool ===")
    
    # Try to import key modules directly to check for issues
    modules_to_check = [
        "angela.execution.error_recovery",
        "angela.toolchain.universal_cli",
        "angela.intent.complex_workflow_planner",
        "angela.toolchain.ci_cd",
        "angela.execution.hooks"
    ]
    
    logger.info("Checking module imports:")
    for module_path in modules_to_check:
        try:
            module = importlib.import_module(module_path)
            logger.info(f"✅ Successfully imported {module_path}")
            
            # Check for expected objects in the module
            if module_path == "angela.execution.error_recovery":
                if hasattr(module, "ErrorRecoveryManager"):
                    logger.info(f"  ✅ {module_path} has ErrorRecoveryManager")
                else:
                    logger.error(f"  ❌ {module_path} is missing ErrorRecoveryManager class")
            
            if module_path == "angela.toolchain.universal_cli":
                if hasattr(module, "universal_cli_translator"):
                    logger.info(f"  ✅ {module_path} has universal_cli_translator")
                else:
                    logger.error(f"  ❌ {module_path} is missing universal_cli_translator")
                    
        except Exception as e:
            logger.error(f"❌ Failed to import {module_path}: {str(e)}")
            logger.error(traceback.format_exc())
    
    # Try initializing application
    logger.info("\nInitializing application:")
    try:
        init_application()
        logger.info("✅ Application initialized successfully")
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Check registry contents
    logger.info("\nChecking service registry:")
    # List all registered services
    all_services = dir(registry._services) if hasattr(registry, "_services") else []
    logger.info(f"Total registered services: {len(all_services)}")
    
    # Check for specific required services
    required_services = [
        "error_recovery_manager",
        "universal_cli_translator",
        "complex_workflow_planner", 
        "ci_cd_integration",
        "execution_hooks"
    ]
    
    for service_name in required_services:
        service = registry.get(service_name)
        if service:
            logger.info(f"✅ {service_name} is registered")
            logger.info(f"  Type: {type(service).__name__}")
        else:
            logger.error(f"❌ {service_name} is NOT registered")

if __name__ == "__main__":
    asyncio.run(diagnose_services())
