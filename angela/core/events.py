# angela/core/events.py
from typing import Dict, Any, Callable, List
import asyncio

class EventBus:
    """Central event bus for system-wide communication."""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._logger = get_logger(__name__)
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        self._logger.debug(f"Handler subscribed to {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            self._logger.debug(f"Handler unsubscribed from {event_type}")
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        self._logger.debug(f"Publishing event: {event_type}")
        
        if event_type not in self._handlers:
            return
            
        # Call all handlers asynchronously
        tasks = []
        for handler in self._handlers[event_type]:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(asyncio.create_task(handler(event_type, data)))
            else:
                handler(event_type, data)
        
        # Wait for all async handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

# Global event bus instance
event_bus = EventBus()
