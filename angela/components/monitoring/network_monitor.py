# angela/monitoring/network_monitor.py

import asyncio
import time
import socket
import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple
from datetime import datetime, timedelta

from angela.config import config_manager
from angela.utils.logging import get_logger
from angela.shell.formatter import terminal_formatter
from angela.context import context_manager

logger = get_logger(__name__)

class NetworkMonitor:
    """
    Network monitoring for services, dependencies, and connections.
    
    Monitors:
    1. Local service health (e.g., web servers, databases)
    2. External API status
    3. Network connectivity
    4. Dependency update availability
    """
    
    def __init__(self):
        """Initialize the network monitor."""
        self._logger = logger
        self._monitoring_tasks = set()
        self._monitoring_active = False
        self._suggestions = set()
        self._last_suggestion_time = datetime.now() - timedelta(hours=1)
        self._suggestion_cooldown = timedelta(minutes=15)
        self._insight_callbacks = []  
        
    def start_monitoring(self):
        """Start network monitoring tasks."""
        if self._monitoring_active:
            return
            
        self._monitoring_active = True
        
        # Create and start monitoring tasks
        self._create_monitoring_task(self._monitor_local_services(), "local_services")
        self._create_monitoring_task(self._monitor_dependency_updates(), "dependency_updates")
        self._create_monitoring_task(self._monitor_network_connectivity(), "network_connectivity")
        
        self._logger.info("Network monitoring started")
    
    def stop_monitoring(self):
        """Stop all network monitoring tasks."""
        if not self._monitoring_active:
            return
            
        self._monitoring_active = False
        
        # Cancel all running tasks
        for task in self._monitoring_tasks:
            if not task.done():
                task.cancel()
                
        self._monitoring_tasks.clear()
        self._logger.info("Network monitoring stopped")
    
    def _create_monitoring_task(self, coro, name):
        """Create and start a monitoring task."""
        task = asyncio.create_task(self._run_monitoring_task(coro, name))
        self._monitoring_tasks.add(task)
        task.add_done_callback(self._monitoring_tasks.discard)
    
    async def _run_monitoring_task(self, coro, name):
        """Run a monitoring task with error handling."""
        try:
            await coro
        except asyncio.CancelledError:
            self._logger.debug(f"Network monitoring task {name} cancelled")
        except Exception as e:
            self._logger.exception(f"Error in network monitoring task {name}: {str(e)}")
            
            # Restart the task after a delay
            await asyncio.sleep(60)
            if self._monitoring_active:
                self._logger.info(f"Restarting network monitoring task {name}")
                if name == "local_services":
                    self._create_monitoring_task(self._monitor_local_services(), name)
                elif name == "dependency_updates":
                    self._create_monitoring_task(self._monitor_dependency_updates(), name)
                elif name == "network_connectivity":
                    self._create_monitoring_task(self._monitor_network_connectivity(), name)
    
    async def _monitor_local_services(self):
        """Monitor local services like web servers and databases."""
        self._logger.debug("Starting local services monitoring")
        
        # Track service status to detect changes
        service_status = {}
        
        while self._monitoring_active:
            try:
                # Get current project context
                context = context_manager.get_context_dict()
                project_type = context.get("project_type")
                
                # Detect potential services based on project type
                services_to_check = self._detect_project_services(project_type)
                
                # Check each service
                for service_name, service_info in services_to_check.items():
                    status = await self._check_service_status(service_info)
                    
                    # Compare with previous status
                    prev_status = service_status.get(service_name, {}).get("status")
                    if prev_status is not None and prev_status != status["status"]:
                        # Status changed
                        if status["status"] == "down" and self._can_show_suggestion():
                            suggestion = f"Service '{service_name}' appears to be down. {status.get('message', '')}"
                            terminal_formatter.print_proactive_suggestion(suggestion, "Network Monitor")
                            self._last_suggestion_time = datetime.now()
                    
                    # Update status
                    service_status[service_name] = status
                
                # Wait before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                self._logger.exception(f"Error monitoring local services: {str(e)}")
                await asyncio.sleep(120)  # Wait before retrying
    
    async def _monitor_dependency_updates(self):
        """Monitor for available updates to project dependencies."""
        self._logger.debug("Starting dependency updates monitoring")
        
        # Track which dependencies we've already notified about
        notified_updates = set()
        
        while self._monitoring_active:
            try:
                # Get current project context
                context = context_manager.get_context_dict()
                project_root = context.get("project_root")
                project_type = context.get("project_type")
                
                if not project_root:
                    # No project detected, sleep and try again later
                    await asyncio.sleep(3600)  # Check every hour
                    continue
                
                # Check dependencies based on project type
                if project_type == "python":
                    updates = await self._check_python_dependencies(Path(project_root))
                elif project_type == "node":
                    updates = await self._check_node_dependencies(Path(project_root))
                else:
                    # Unknown project type, sleep and try again later
                    await asyncio.sleep(3600)
                    continue
                
                # Notify about new updates
                if updates and self._can_show_suggestion():
                    # Filter out already notified updates
                    new_updates = [u for u in updates if f"{u['name']}:{u['new_version']}" not in notified_updates]
                    
                    if new_updates:
                        count = len(new_updates)
                        pkg_list = ", ".join([f"{u['name']} ({u['current_version']} → {u['new_version']})" 
                                             for u in new_updates[:3]])
                        more = f" and {count - 3} more" if count > 3 else ""
                        
                        suggestion = f"Found {count} dependency updates available: {pkg_list}{more}"
                        terminal_formatter.print_proactive_suggestion(suggestion, "Dependency Monitor")
                        
                        # Mark as notified
                        for update in new_updates:
                            notified_updates.add(f"{update['name']}:{update['new_version']}")
                        
                        self._last_suggestion_time = datetime.now()
                
                # Wait before checking again (dependencies don't change often)
                await asyncio.sleep(86400)  # Check once per day
                
            except Exception as e:
                self._logger.exception(f"Error monitoring dependency updates: {str(e)}")
                await asyncio.sleep(3600)  # Wait before retrying
    
    async def _monitor_network_connectivity(self):
        """Monitor network connectivity to important services."""
        self._logger.debug("Starting network connectivity monitoring")
        
        # Track connectivity status to detect changes
        connectivity_status = {
            "internet": True,  # Assume connected initially
            "last_check": datetime.now()
        }
        
        while self._monitoring_active:
            try:
                # Check internet connectivity
                internet_status = await self._check_internet_connectivity()
                
                # Check if status changed
                if connectivity_status["internet"] != internet_status["connected"]:
                    if not internet_status["connected"] and self._can_show_suggestion():
                        suggestion = f"Internet connectivity appears to be down. {internet_status.get('message', '')}"
                        terminal_formatter.print_proactive_suggestion(suggestion, "Network Monitor")
                        self._last_suggestion_time = datetime.now()
                    elif internet_status["connected"] and not connectivity_status["internet"]:
                        # Internet connection restored
                        elapsed = datetime.now() - connectivity_status["last_check"]
                        if elapsed > timedelta(minutes=5) and self._can_show_suggestion():
                            suggestion = "Internet connectivity has been restored."
                            terminal_formatter.print_proactive_suggestion(suggestion, "Network Monitor")
                            self._last_suggestion_time = datetime.now()
                
                # Update status
                connectivity_status["internet"] = internet_status["connected"]
                connectivity_status["last_check"] = datetime.now()
                
                # Wait before checking again
                await asyncio.sleep(30)
                
            except Exception as e:
                self._logger.exception(f"Error monitoring network connectivity: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def _detect_project_services(self, project_type: Optional[str]) -> Dict[str, Dict[str, Any]]:
        """
        Detect services to monitor based on project type.
        
        Args:
            project_type: The type of project
            
        Returns:
            Dictionary of service information
        """
        services = {}
        
        # Default services to check
        services["localhost:8000"] = {
            "host": "localhost",
            "port": 8000,
            "name": "Web Server (8000)",
            "type": "http"
        }
        
        # Add services based on project type
        if project_type == "node":
            services["localhost:3000"] = {
                "host": "localhost",
                "port": 3000,
                "name": "Node.js Server",
                "type": "http"
            }
        elif project_type == "python":
            services["localhost:5000"] = {
                "host": "localhost",
                "port": 5000,
                "name": "Flask Server",
                "type": "http"
            }
            services["localhost:8000"] = {
                "host": "localhost",
                "port": 8000,
                "name": "Django Server",
                "type": "http"
            }
        
        # Always check database ports
        services["localhost:5432"] = {
            "host": "localhost",
            "port": 5432,
            "name": "PostgreSQL",
            "type": "tcp"
        }
        services["localhost:3306"] = {
            "host": "localhost",
            "port": 3306,
            "name": "MySQL",
            "type": "tcp"
        }
        services["localhost:27017"] = {
            "host": "localhost",
            "port": 27017,
            "name": "MongoDB",
            "type": "tcp"
        }
        services["localhost:6379"] = {
            "host": "localhost",
            "port": 6379,
            "name": "Redis",
            "type": "tcp"
        }
        
        return services
    
    async def _check_service_status(self, service_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check the status of a service.
        
        Args:
            service_info: Service information
            
        Returns:
            Status information
        """
        host = service_info.get("host", "localhost")
        port = service_info.get("port", 80)
        service_type = service_info.get("type", "tcp")
        
        # Basic port check
        try:
            # Create a socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)  # 2 second timeout
            
            # Try to connect
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                # Port is open
                if service_type == "http":
                    # For HTTP services, try to get a response
                    try:
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"http://{host}:{port}/", timeout=5) as response:
                                if response.status < 400:
                                    return {"status": "up", "message": f"HTTP status: {response.status}"}
                                else:
                                    return {"status": "error", "message": f"HTTP error: {response.status}"}
                    except Exception as e:
                        return {"status": "error", "message": f"HTTP error: {str(e)}"}
                else:
                    # TCP service is up
                    return {"status": "up", "message": "Port is open"}
            else:
                # Port is closed
                return {"status": "down", "message": "Port is closed"}
                
        except Exception as e:
            return {"status": "error", "message": f"Error checking service: {str(e)}"}
    
    async def _check_python_dependencies(self, project_root: Path) -> List[Dict[str, Any]]:
        """
        Check for updates to Python dependencies.
        
        Args:
            project_root: The project root directory
            
        Returns:
            List of available updates
        """
        requirements_path = project_root / "requirements.txt"
        
        if not requirements_path.exists():
            return []
        
        try:
            # Run pip list --outdated
            result = await self._run_command("pip list --outdated --format=json")
            
            if not result["success"]:
                return []
                
            # Parse the output
            outdated = json.loads(result["stdout"])
            
            # Format the updates
            updates = []
            for pkg in outdated:
                updates.append({
                    "name": pkg["name"],
                    "current_version": pkg["version"],
                    "new_version": pkg["latest_version"],
                    "type": "python"
                })
                
            return updates
            
        except Exception as e:
            self._logger.error(f"Error checking Python dependencies: {str(e)}")
            return []
    
    async def _check_node_dependencies(self, project_root: Path) -> List[Dict[str, Any]]:
        """
        Check for updates to Node.js dependencies.
        
        Args:
            project_root: The project root directory
            
        Returns:
            List of available updates
        """
        package_json_path = project_root / "package.json"
        
        if not package_json_path.exists():
            return []
        
        try:
            # Run npm outdated --json
            result = await self._run_command("npm outdated --json", cwd=str(project_root))
            
            if not result["success"] and not result["stdout"]:
                return []
                
            # Parse the output
            try:
                outdated = json.loads(result["stdout"])
            except json.JSONDecodeError:
                # npm outdated returns non-zero exit code when updates are available
                if not result["stdout"]:
                    return []
                outdated = {}
            
            # Format the updates
            updates = []
            for pkg_name, pkg_info in outdated.items():
                updates.append({
                    "name": pkg_name,
                    "current_version": pkg_info.get("current", "unknown"),
                    "new_version": pkg_info.get("latest", "unknown"),
                    "type": "npm"
                })
                
            return updates
            
        except Exception as e:
            self._logger.error(f"Error checking Node.js dependencies: {str(e)}")
            return []
    
    async def _check_internet_connectivity(self) -> Dict[str, Any]:
        """
        Check internet connectivity.
        
        Returns:
            Status information
        """
        # List of reliable domains to check
        check_domains = [
            "google.com",
            "cloudflare.com",
            "amazon.com",
            "microsoft.com"
        ]
        
        successes = 0
        failures = 0
        
        for domain in check_domains:
            try:
                # Try to resolve the domain
                await asyncio.get_event_loop().getaddrinfo(domain, 80)
                successes += 1
            except socket.gaierror:
                failures += 1
        
        # Consider internet connected if at least half of the checks succeeded
        connected = successes >= len(check_domains) / 2
        
        return {
            "connected": connected,
            "message": f"{successes}/{len(check_domains)} connectivity checks succeeded"
        }
    
    async def _run_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a shell command and return its output.
        
        Args:
            command: The command to run
            cwd: Optional working directory
            
        Returns:
            Dictionary with command results
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "command": command,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode,
                "success": process.returncode == 0
            }
        except Exception as e:
            self._logger.error(f"Error running command '{command}': {str(e)}")
            return {
                "command": command,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "success": False
            }
    
    def _can_show_suggestion(self) -> bool:
        """
        Check if we can show a suggestion now (respecting cooldown period).
        
        Returns:
            True if a suggestion can be shown, False otherwise
        """
        now = datetime.now()
        return (now - self._last_suggestion_time) >= self._suggestion_cooldown


    def register_insight_callback(self, callback):
        """
        Register a callback function to be called when an insight is generated.
        
        Args:
            callback: Async function to call with insight_type and insight_data
        """
        self._logger.debug(f"Registering insight callback: {callback.__name__}")
        self._insight_callbacks.append(callback)
    
    def unregister_insight_callback(self, callback):
        """
        Unregister a previously registered callback function.
        
        Args:
            callback: The callback function to unregister
        """
        if callback in self._insight_callbacks:
            self._logger.debug(f"Unregistering insight callback: {callback.__name__}")
            self._insight_callbacks.remove(callback)
    
    async def _notify_insight_callbacks(self, insight_type, insight_data):
        """
        Notify all registered callbacks about a new insight.
        
        Args:
            insight_type: Type of insight
            insight_data: Insight data
        """
        for callback in self._insight_callbacks:
            try:
                await callback(insight_type, insight_data)
            except Exception as e:
                self._logger.error(f"Error in insight callback: {str(e)}")




# Global network monitor instance
network_monitor = NetworkMonitor()
