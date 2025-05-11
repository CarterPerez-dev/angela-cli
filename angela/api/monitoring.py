# angela/api/monitoring.py
"""
Public API for the monitoring components.

This module provides functions to access monitoring components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable, Awaitable

from angela.core.registry import registry

# Background Monitor API
def get_background_monitor():
    """Get the background monitor instance."""
    from angela.components.monitoring.background import BackgroundMonitor, background_monitor 
    return registry.get_or_create("background_monitor", BackgroundMonitor, factory=lambda: background_monitor)

# Network Monitor API
def get_network_monitor():
    """Get the network monitor instance."""
    from angela.components.monitoring.network_monitor import NetworkMonitor, network_monitor 
    return registry.get_or_create("network_monitor", NetworkMonitor, factory=lambda: network_monitor)

# Notification Handler API
def get_notification_handler():
    """Get the notification handler instance."""
    from angela.components.monitoring.notification_handler import NotificationHandler, notification_handler 
    return registry.get_or_create("notification_handler", NotificationHandler, factory=lambda: notification_handler)

# Proactive Assistant API
def get_proactive_assistant():
    """Get the proactive assistant instance."""
    from angela.components.monitoring.proactive_assistant import ProactiveAssistant, proactive_assistant 
    return registry.get_or_create("proactive_assistant", ProactiveAssistant, factory=lambda: proactive_assistant)
