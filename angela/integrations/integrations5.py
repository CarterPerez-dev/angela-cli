# angela/integrations.py

import asyncio
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from angela.utils.logging import get_logger
from angela.context import context_manager
from angela.context.project_inference import project_inference
from angela.intent.advanced_planner import advanced_task_planner
from angela.ai.content_analyzer import content_analyzer
from angela.monitoring.network_monitor import network_monitor
from angela.workflows.sharing import workflow_sharing_manager
from angela.execution.error_recovery import ErrorRecoveryManager

logger = get_logger(__name__)

class PhaseIntegration:
    """
    Integration module for Phase 5.5 features.
    
    This class provides:
    1. Initialization and setup of Phase 5.5 features
    2. Integration between different components
    3. Helper methods for the orchestrator
    4. Status reporting
    """
    
    def __init__(self):
        """Initialize the integration module."""
        self._logger = logger
        self._error_recovery = ErrorRecoveryManager()
        self._features_enabled = {}
    
    async def initialize(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initialize Phase 5.5 features.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            Status of initialization
        """
        config = config or {}
        results = {}
        
        # Initialize project inference
        if config.get("enable_project_inference", True):
            try:
                project_root = context_manager.project_root
                if project_root:
                    project_info = await project_inference.infer_project_info(project_root)
                    results["project_inference"] = {
                        "status": "initialized",
                        "project_type": project_info.get("project_type", "unknown")
                    }
                    self._features_enabled["project_inference"] = True
                else:
                    results["project_inference"] = {
                        "status": "disabled",
                        "reason": "No project root detected"
                    }
            except Exception as e:
                self._logger.error(f"Error initializing project inference: {str(e)}")
                results["project_inference"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Initialize network monitoring
        if config.get("enable_network_monitoring", False):
            try:
                network_monitor.start_monitoring()
                results["network_monitoring"] = {
                    "status": "started"
                }
                self._features_enabled["network_monitoring"] = True
            except Exception as e:
                self._logger.error(f"Error starting network monitoring: {str(e)}")
                results["network_monitoring"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Log the initialization results
        self._logger.info(f"Phase 5.5 features initialized: {', '.join(k for k, v in self._features_enabled.items() if v)}")
        
        return results
    
    async def get_enhanced_context(self) -> Dict[str, Any]:
        """
        Get enhanced context information for AI prompts.
        
        Returns:
            Enhanced context dictionary
        """
        context = {}
        
        # Add project inference data if available
        if self._features_enabled.get("project_inference"):
            project_root = context_manager.project_root
            if project_root:
                try:
                    project_info = await project_inference.infer_project_info(project_root)
                    context["project_info"] = project_info
                except Exception as e:
                    self._logger.error(f"Error getting project information: {str(e)}")
        
        # Add network status if available
        if self._features_enabled.get("network_monitoring"):
            try:
                # This is a placeholder - in a real implementation, you would
                # get the actual network status from the network monitor
                context["network_status"] = {
                    "internet_connected": True,
                    "local_services": {}
                }
            except Exception as e:
                self._logger.error(f"Error getting network status: {str(e)}")
        
        return context
    
    async def handle_execution_error(
        self, 
        step: Any, 
        error_result: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle execution errors with recovery.
        
        Args:
            step: The step that failed
            error_result: The execution result with error information
            context: Context information
            
        Returns:
            Updated execution result
        """
        return await self._error_recovery.handle_error(step, error_result, context)
    
    async def analyze_content(
        self, 
        file_path: Path, 
        request: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze file content with enhanced capabilities.
        
        Args:
            file_path: Path to the file to analyze
            request: Optional specific analysis request
            
        Returns:
            Analysis results
        """
        # Get project context for better analysis
        enhanced_context = {}
        if self._features_enabled.get("project_inference"):
            project_root = context_manager.project_root
            if project_root:
                try:
                    project_info = await project_inference.infer_project_info(project_root)
                    enhanced_context["project_type"] = project_info.get("project_type", "unknown")
                    enhanced_context["frameworks"] = project_info.get("detected_frameworks", {})
                except Exception as e:
                    self._logger.error(f"Error getting project information: {str(e)}")
        
        # Use the enhanced content analyzer
        from angela.ai.content_analyzer_extensions import enhanced_content_analyzer
        return await enhanced_content_analyzer.analyze_content(file_path, request)
    
    async def status(self) -> Dict[str, Any]:
        """
        Get status of Phase 5.5 features.
        
        Returns:
            Status dictionary
        """
        status = {
            "enabled_features": {k: v for k, v in self._features_enabled.items() if v},
            "phase": "5.5",
            "description": "Autonomous Task Orchestration & Proactive Assistance"
        }
        
        # Add project information if available
        if self._features_enabled.get("project_inference"):
            project_root = context_manager.project_root
            if project_root:
                try:
                    project_info = await project_inference.infer_project_info(project_root)
                    status["project"] = {
                        "type": project_info.get("project_type", "unknown"),
                        "frameworks": list(project_info.get("detected_frameworks", {}).keys()),
                        "dependencies_count": len(project_info.get("dependencies", []))
                    }
                except Exception as e:
                    self._logger.error(f"Error getting project status: {str(e)}")
        
        # Add network status if available
        if self._features_enabled.get("network_monitoring"):
            try:
                # This is a placeholder - in a real implementation, you would
                # get actual network monitor statistics
                status["network_monitoring"] = {
                    "status": "active",
                    "services_monitored": 0,
                    "dependency_updates": 0
                }
            except Exception as e:
                self._logger.error(f"Error getting network status: {str(e)}")
        
        return status

# Global integration instance
phase_integration = PhaseIntegration()
