# angela/core/registry.py
"""
Enhanced service registry with improved error handling and initialization.

This registry provides centralized access to all components in the Angela CLI.
It supports lazy initialization, dependency injection, and proper error handling.
"""
from typing import Dict, Any, Type, Optional, Callable, TypeVar, List, Set
import logging
import threading
from functools import wraps

# Type variable for generic methods
T = TypeVar('T')

class ServiceRegistry:
    """
    Service registry with improved error handling and initialization support.
    
    This registry implements:
    - Lazy initialization via get_or_create
    - Factory functions for complex initialization
    - Instance tracking for debugging
    - Thread safety for concurrent access
    """
    
    _instance = None
    _lock = threading.RLock()
    
    @classmethod
    def get_instance(cls) -> 'ServiceRegistry':
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ServiceRegistry()
        return cls._instance
    
    def __init__(self):
        """Initialize the registry."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._service_types: Dict[str, Type] = {}
        self._initialization_order: List[str] = []
        self._logger = logging.getLogger(__name__)
    
    def register(self, name: str, service: Any) -> Any:
        """
        Register a service with the registry.
        
        Args:
            name: Unique identifier for the service
            service: The service instance to register
            
        Returns:
            The registered service (for method chaining)
        """
        with self._lock:
            self._services[name] = service
            self._service_types[name] = type(service)
            if name not in self._initialization_order:
                self._initialization_order.append(name)
            
            self._logger.debug(f"Registered service: {name} ({type(service).__name__})")
            return service
    
    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """
        Register a factory function for lazy initialization.
        
        Args:
            name: Unique identifier for the service
            factory: Callable that returns the service instance
        """
        with self._lock:
            self._factories[name] = factory
            self._logger.debug(f"Registered factory for: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """
        Get a service from the registry.
        
        Args:
            name: The name of the service to retrieve
            
        Returns:
            The service instance or None if not found
        """
        # Return existing service if available
        if name in self._services:
            return self._services[name]
        
        # Try to create service using factory if available
        if name in self._factories:
            try:
                with self._lock:
                    # Check again in case another thread created it
                    if name in self._services:
                        return self._services[name]
                    
                    self._logger.debug(f"Creating service via factory: {name}")
                    service = self._factories[name]()
                    return self.register(name, service)
            except Exception as e:
                self._logger.error(f"Error creating service '{name}' via factory: {e}", exc_info=True)
                return None
        
        return None
    
    def get_or_create(self, name: str, cls: Type[T], *args, **kwargs) -> T:
        """
        Get a service or create it if it doesn't exist.
        
        Args:
            name: Service name
            cls: Class to instantiate if service doesn't exist
            *args, **kwargs: Arguments to pass to the class constructor
            
        Returns:
            The existing or newly created service
            
        Raises:
            Exception: If service creation fails
        """
        # Return existing service if available
        service = self.get(name)
        if service is not None:
            # Validate the service type matches the expected class
            if not isinstance(service, cls):
                self._logger.warning(
                    f"Type mismatch for service '{name}': expected {cls.__name__}, "
                    f"got {type(service).__name__}"
                )
            return service
        
        # Create new service instance
        try:
            with self._lock:
                # Check again inside lock in case another thread created it
                if name in self._services:
                    return self._services[name]
                
                self._logger.debug(f"Creating service: {name} ({cls.__name__})")
                service = cls(*args, **kwargs)
                return self.register(name, service)
        except Exception as e:
            self._logger.error(f"Error creating service '{name}': {e}", exc_info=True)
            # Raise to make errors obvious
            raise
    
    def clear(self) -> None:
        """Clear all registered services."""
        with self._lock:
            self._logger.debug("Clearing service registry")
            self._services.clear()
            self._factories.clear()
            self._service_types.clear()
            self._initialization_order.clear()
    
    def partial_clear(self, prefix: str) -> None:
        """
        Clear services with names starting with the given prefix.
        
        Args:
            prefix: Prefix for service names to clear
        """
        with self._lock:
            to_remove = [
                name for name in self._services
                if name.startswith(prefix)
            ]
            
            for name in to_remove:
                self._services.pop(name, None)
                self._factories.pop(name, None)
                self._service_types.pop(name, None)
                
                if name in self._initialization_order:
                    self._initialization_order.remove(name)
            
            self._logger.debug(f"Cleared {len(to_remove)} services with prefix '{prefix}'")
    
    def list_services(self) -> Dict[str, Type]:
        """
        Get a dictionary of all registered services and their types.
        
        Returns:
            Dictionary of service names and their types
        """
        with self._lock:
            return self._service_types.copy()
    
    def get_initialization_order(self) -> List[str]:
        """
        Get the order in which services were initialized.
        
        Returns:
            List of service names in initialization order
        """
        with self._lock:
            return self._initialization_order.copy()


    def get_safe(self, name: str, fallback_import_path: Optional[str] = None) -> Optional[Any]:
        """
        Get a service with fallback to direct import if needed.
        
        Args:
            name: Service name to retrieve
            fallback_import_path: Optional import path to try if service not found
            
        Returns:
            Service instance or None
        """
        # Try registry first
        service = self.get(name)
        if service is not None:
            return service
            
        # Try fallback import if provided
        if fallback_import_path:
            try:
                module_path, attr_name = fallback_import_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[attr_name])
                return getattr(module, attr_name)
            except (ImportError, AttributeError) as e:
                self._logger.error(f"Fallback import failed for {fallback_import_path}: {e}")
        
        return None
        

# Create global registry instance
registry = ServiceRegistry.get_instance()


# Optional: Decorator for singleton services
def singleton_service(service_name: Optional[str] = None):
    """
    Decorator to mark a class as a singleton service.
    
    When a class is decorated with @singleton_service, it will be
    automatically registered in the global registry the first time
    it's instantiated.
    
    Args:
        service_name: Optional name for the service. If not provided,
                     the class name will be used.
    """
    def decorator(cls: Type[T]) -> Type[T]:
        orig_init = cls.__init__
        
        @wraps(orig_init)
        def __init__(self, *args, **kwargs):
            # Store the original init arguments
            self._init_args = args
            self._init_kwargs = kwargs
            
            # Call the original __init__
            orig_init(self, *args, **kwargs)
            
            # Register the instance
            name = service_name or cls.__name__.lower()
            registry.register(name, self)
        
        # Replace the __init__ method
        cls.__init__ = __init__
        
        # Add a get_instance classmethod
        @classmethod
        def get_instance(cls, *args, **kwargs):
            name = service_name or cls.__name__.lower()
            return registry.get_or_create(name, cls, *args, **kwargs)
        
        cls.get_instance = get_instance
        
        return cls
    
    return decorator
