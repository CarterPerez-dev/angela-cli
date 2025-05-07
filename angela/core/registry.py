# angela/core/registry.py
"""
Service registry for breaking circular dependencies.
"""
from typing import Dict, Any, Type, Optional
import logging

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """
    A simple service locator that allows components to be registered and retrieved
    without direct imports, breaking circular dependencies.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ServiceRegistry':
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            cls._instance = ServiceRegistry()
        return cls._instance
    
    def __init__(self):
        """Initialize the registry."""
        self._services: Dict[str, Any] = {}
        logger.debug("Service registry initialized")
    
    def register(self, name: str, service: Any) -> None:
        """
        Register a service with the registry.
        
        Args:
            name: The name to register the service under
            service: The service instance
        """
        self._services[name] = service
        logger.debug(f"Service registered: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """
        Get a service from the registry.
        
        Args:
            name: The name of the service to retrieve
            
        Returns:
            The service instance or None if not found
        """
        service = self._services.get(name)
        if service is None:
            logger.warning(f"Service not found: {name}")
        return service
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        logger.debug("Service registry cleared")

# Global instance for convenience
registry = ServiceRegistry.get_instance()
