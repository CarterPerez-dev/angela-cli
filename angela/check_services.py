# check_services.py
import asyncio
from angela import init_application
from angela.core.registry import registry
from angela.utils.logging import setup_logging, get_logger

async def main():
    # Set up logging
    setup_logging(debug=True)
    logger = get_logger("check_services")
    
    logger.info("Initializing application...")
    init_application()
    
    # Check for required services
    required_services = [
        "error_recovery_manager",
        "universal_cli_translator", 
        "complex_workflow_planner",
        "ci_cd_integration",
        "proactive_assistant",
        "execution_hooks"
    ]
    
    logger.info("Checking for required services...")
    all_present = True
    
    for service_name in required_services:
        service = registry.get(service_name)
        if service:
            logger.info(f"✅ {service_name} is registered")
            
            # Check for required methods if appropriate
            if service_name == "execution_hooks":
                if hasattr(service, "register_hook"):
                    logger.info(f"  ✅ {service_name} has register_hook method")
                else:
                    logger.error(f"  ❌ {service_name} is missing register_hook method")
                    all_present = False
        else:
            logger.error(f"❌ {service_name} is NOT registered")
            all_present = False
    
    if all_present:
        logger.info("All required services are properly registered!")
    else:
        logger.error("Some required services are missing or incomplete")
    
    # Try to initialize phase12 integration
    try:
        from angela.integrations.phase12_integration import phase12_integration
        logger.info("Initializing Phase 12 integration...")
        result = await phase12_integration.initialize()
        if result:
            logger.info("✅ Phase 12 initialization successful")
        else:
            logger.error("❌ Phase 12 initialization failed")
    except Exception as e:
        logger.error(f"❌ Error initializing Phase 12: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
