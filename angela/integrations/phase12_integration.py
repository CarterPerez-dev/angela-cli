"""
Phase 12 Integration: Advanced Orchestration & Universal Tool Translation for Angela CLI.

This module ties together the Universal CLI Translator, Complex Workflow Orchestration,
CI/CD Pipeline Automation, and Proactive Assistance V2 components to provide
a unified interface for advanced, cross-tool workflows.
"""
import asyncio
import logging
import re
import os
from typing import Dict, Any, List, Optional, Set, Union, Tuple
from pathlib import Path

from angela.utils.logging import get_logger
from angela.context import context_manager
from angela.core.registry import registry
from angela.ai.client import gemini_client, GeminiRequest
from angela.shell.formatter import terminal_formatter

logger = get_logger(__name__)

class Phase12Integration:
    """
    Integration class for Phase 12 components: Universal CLI Translator,
    Complex Workflow Orchestration, CI/CD Pipeline Automation, and
    Proactive Assistance V2.
    """
    
    def __init__(self):
        """Initialize the Phase 12 integration."""
        self._logger = logger
        self._ready = False
        self._components = {}
    
    async def initialize(self):
        """Initialize and verify all Phase 12 components."""
        self._logger.info("Initializing Phase 12 integration components")
        
        # Check for required components
        self._components = {
            "universal_cli_translator": registry.get("universal_cli_translator"),
            "complex_workflow_planner": registry.get("complex_workflow_planner"),
            "ci_cd_integration": registry.get("ci_cd_integration"),
            "proactive_assistant": registry.get("proactive_assistant")
        }
        
        missing_components = [name for name, component in self._components.items() 
                             if component is None]
        
        if missing_components:
            self._logger.warning(f"Missing Phase 12 components: {missing_components}")
            
            # Try to import the missing components
            if "universal_cli_translator" in missing_components:
                try:
                    from angela.toolchain.universal_cli import universal_cli_translator
                    self._components["universal_cli_translator"] = universal_cli_translator
                    registry.register("universal_cli_translator", universal_cli_translator)
                except ImportError:
                    self._logger.error("Failed to import Universal CLI Translator")
            
            if "complex_workflow_planner" in missing_components:
                try:
                    from angela.intent.complex_workflow_planner import complex_workflow_planner
                    self._components["complex_workflow_planner"] = complex_workflow_planner
                    registry.register("complex_workflow_planner", complex_workflow_planner)
                except ImportError:
                    self._logger.error("Failed to import Complex Workflow Planner")
            
            if "ci_cd_integration" in missing_components:
                try:
                    from angela.toolchain.ci_cd import ci_cd_integration
                    self._components["ci_cd_integration"] = ci_cd_integration
                    registry.register("ci_cd_integration", ci_cd_integration)
                except ImportError:
                    self._logger.error("Failed to import CI/CD Integration")
            
            if "proactive_assistant" in missing_components:
                try:
                    from angela.monitoring.proactive_assistant import proactive_assistant
                    self._components["proactive_assistant"] = proactive_assistant
                    registry.register("proactive_assistant", proactive_assistant)
                except ImportError:
                    self._logger.error("Failed to import Proactive Assistant")
            
            # Check again after import attempts
            missing_components = [name for name, component in self._components.items() 
                                if component is None]
            
            if missing_components:
                self._logger.warning(f"Still missing Phase 12 components after import attempts: {missing_components}")
                self._ready = False
                return False
        
        # Start the proactive assistant if available
        if self._components["proactive_assistant"]:
            try:
                self._components["proactive_assistant"].start()
                self._logger.info("Started Proactive Assistant")
            except Exception as e:
                self._logger.error(f"Failed to start Proactive Assistant: {str(e)}")
        
        self._ready = True
        self._logger.info("Phase 12 integration successfully initialized")
        return True
    
    async def detect_pipeline_opportunities(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect opportunities for setting up CI/CD pipelines in the current context.
        
        Args:
            context: Context information
            
        Returns:
            Dictionary with pipeline opportunities
        """
        self._logger.info("Detecting CI/CD pipeline opportunities")
        
        if not self._components["ci_cd_integration"]:
            return {
                "success": False,
                "error": "CI/CD Integration component not available"
            }
        
        project_root = context.get("project_root")
        if not project_root:
            return {
                "success": False,
                "error": "No project root detected in context"
            }
        
        # Check for existing CI/CD configuration
        has_github_actions = Path(project_root, ".github", "workflows").exists()
        has_gitlab_ci = Path(project_root, ".gitlab-ci.yml").exists()
        has_jenkins = Path(project_root, "Jenkinsfile").exists()
        has_travis = Path(project_root, ".travis.yml").exists()
        has_circle_ci = Path(project_root, ".circleci").exists()
        
        existing_ci = []
        if has_github_actions:
            existing_ci.append("github_actions")
        if has_gitlab_ci:
            existing_ci.append("gitlab_ci")
        if has_jenkins:
            existing_ci.append("jenkins")
        if has_travis:
            existing_ci.append("travis")
        if has_circle_ci:
            existing_ci.append("circle_ci")
        
        # Determine project type
        detection_result = await self._components["ci_cd_integration"].detect_project_type(project_root)
        project_type = detection_result.get("project_type")
        
        # Check for repository URL
        repository_url = None
        try:
            from angela.execution.engine import execution_engine
            stdout, stderr, return_code = await execution_engine.execute_command(
                command="git remote get-url origin",
                check_safety=True,
                working_dir=project_root
            )
            
            if return_code == 0 and stdout.strip():
                repository_url = stdout.strip()
        except Exception as e:
            self._logger.debug(f"Error getting repository URL: {str(e)}")
        
        # Determine repository provider
        repository_provider = "unknown"
        if repository_url:
            repository_provider = self._components["ci_cd_integration"].get_repository_provider_from_url(repository_url)
        
        # Identify recommended CI/CD platform based on repository provider
        recommended_platform = None
        if repository_provider == "github":
            recommended_platform = "github_actions"
        elif repository_provider == "gitlab":
            recommended_platform = "gitlab_ci"
        elif repository_provider == "bitbucket":
            recommended_platform = "bitbucket_pipelines"
        elif repository_provider == "azure_devops":
            recommended_platform = "azure_pipelines"
        
        # Check for deployment configuration
        has_deploy_config = any([
            Path(project_root, "deploy.sh").exists(),
            Path(project_root, "deploy.yml").exists(),
            Path(project_root, "deploy.json").exists(),
            Path(project_root, "deployment").exists(),
            Path(project_root, ".deploy").exists()
        ])
        
        # Return pipeline opportunity information
        return {
            "success": True,
            "has_ci_cd": bool(existing_ci),
            "existing_ci": existing_ci,
            "project_root": str(project_root),
            "project_type": project_type,
            "repository_url": repository_url,
            "repository_provider": repository_provider,
            "recommended_platform": recommended_platform or "github_actions",
            "has_deploy_config": has_deploy_config,
            "needs_setup": not bool(existing_ci),
            "suggested_actions": self._get_suggested_actions(
                existing_ci=existing_ci,
                project_type=project_type,
                repository_provider=repository_provider,
                has_deploy_config=has_deploy_config
            )
        }
    
    def _get_suggested_actions(
        self, 
        existing_ci: List[str],
        project_type: Optional[str],
        repository_provider: str,
        has_deploy_config: bool
    ) -> List[Dict[str, Any]]:
        """
        Get suggested CI/CD actions based on the current state.
        
        Args:
            existing_ci: List of existing CI/CD platforms
            project_type: Project type
            repository_provider: Repository provider
            has_deploy_config: Whether deployment configuration exists
            
        Returns:
            List of suggested actions
        """
        suggestions = []
        
        if not existing_ci:
            # Suggest setting up CI/CD
            suggested_platform = None
            if repository_provider == "github":
                suggested_platform = "github_actions"
            elif repository_provider == "gitlab":
                suggested_platform = "gitlab_ci"
            elif repository_provider == "bitbucket":
                suggested_platform = "bitbucket_pipelines"
            elif repository_provider == "azure_devops":
                suggested_platform = "azure_pipelines"
            else:
                # Default based on project type
                if project_type == "python":
                    suggested_platform = "github_actions"
                elif project_type == "node":
                    suggested_platform = "github_actions"
                elif project_type == "java":
                    suggested_platform = "jenkins"
                elif project_type == "go":
                    suggested_platform = "github_actions"
                else:
                    suggested_platform = "github_actions"
            
            suggestions.append({
                "action": "setup_ci",
                "platform": suggested_platform,
                "description": f"Set up {suggested_platform.replace('_', ' ').title()} for continuous integration",
                "priority": "high"
            })
        
        if not has_deploy_config:
            # Suggest setting up deployment
            suggestions.append({
                "action": "setup_deployment",
                "description": "Set up deployment configuration",
                "priority": "medium"
            })
        
        # Check for potential improvements to existing CI/CD
        if existing_ci:
            for platform in existing_ci:
                if platform == "github_actions":
                    suggestions.append({
                        "action": "analyze_github_actions",
                        "description": "Analyze GitHub Actions workflow for improvements",
                        "priority": "low"
                    })
                elif platform == "gitlab_ci":
                    suggestions.append({
                        "action": "analyze_gitlab_ci",
                        "description": "Analyze GitLab CI configuration for improvements",
                        "priority": "low"
                    })
        
        return suggestions
    
    async def suggest_complex_workflow(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest a complex workflow based on a natural language request.
        
        Args:
            request: Natural language request
            context: Context information
            
        Returns:
            Dictionary with suggested workflow information
        """
        self._logger.info(f"Suggesting complex workflow for: {request}")
        
        if not self._components["complex_workflow_planner"]:
            return {
                "success": False,
                "error": "Complex Workflow Planner component not available"
            }
        
        # Analyze the request to determine the tools needed
        tools_analysis = await self._analyze_tools_in_request(request, context)
        
        # Generate a workflow plan
        try:
            workflow_plan = await self._components["complex_workflow_planner"].plan_complex_workflow(
                request=request,
                context=context,
                max_steps=30
            )
            
            # Don't send the entire context snapshot in the response
            workflow_plan_dict = workflow_plan.dict()
            if "context_snapshot" in workflow_plan_dict:
                del workflow_plan_dict["context_snapshot"]
            
            return {
                "success": True,
                "workflow_plan": workflow_plan_dict,
                "tools_analysis": tools_analysis,
                "step_count": len(workflow_plan.steps),
                "estimated_duration": self._estimate_duration(workflow_plan)
            }
        except Exception as e:
            self._logger.error(f"Error generating workflow plan: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to generate workflow plan: {str(e)}",
                "tools_analysis": tools_analysis
            }
    
    async def _analyze_tools_in_request(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a request to determine which tools are needed.
        
        Args:
            request: Natural language request
            context: Context information
            
        Returns:
            Dictionary with tools analysis
        """
        self._logger.debug(f"Analyzing tools in request: {request}")
        
        # Use AI to analyze the tools needed
        prompt = f"""
Analyze this request to determine which command-line tools would be needed to fulfill it:
"{request}"

Return a JSON object with:
1. primary_tools: List of main CLI tools needed (e.g., git, docker, aws, etc.)
2. supporting_tools: List of additional tools that might be needed
3. complexity: Estimated complexity level ("simple", "moderate", "complex")
4. cross_tool_data_flow: Whether data needs to flow between different tools (true/false)
5. estimated_steps: Rough estimate of number of steps needed
"""

        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            tools_analysis = json.loads(json_str)
            
            # Check tool availability
            if self._components["universal_cli_translator"]:
                available_tools = set()
                
                for tool in tools_analysis.get("primary_tools", []):
                    suggestions = await self._components["universal_cli_translator"].get_tool_suggestions(tool)
                    if tool in suggestions:
                        available_tools.add(tool)
                
                tools_analysis["available_tools"] = list(available_tools)
                tools_analysis["missing_tools"] = [
                    tool for tool in tools_analysis.get("primary_tools", [])
                    if tool not in available_tools
                ]
            
            return tools_analysis
            
        except Exception as e:
            self._logger.error(f"Error analyzing tools in request: {str(e)}")
            return {
                "primary_tools": [],
                "supporting_tools": [],
                "complexity": "unknown",
                "cross_tool_data_flow": False,
                "estimated_steps": 0,
                "error": str(e)
            }
    
    def _estimate_duration(self, workflow_plan: Any) -> int:
        """
        Estimate the duration of a workflow in seconds.
        
        Args:
            workflow_plan: The workflow plan
            
        Returns:
            Estimated duration in seconds
        """
        # If complex_workflow_planner has a method for this, use it
        if hasattr(self._components["complex_workflow_planner"], "_estimate_workflow_duration"):
            return self._components["complex_workflow_planner"]._estimate_workflow_duration(workflow_plan)
        
        # Fallback implementation
        step_count = len(workflow_plan.steps)
        
        # Simple heuristic - 30 seconds per step on average
        return step_count * 30
    
    async def setup_universal_cli_integration(self) -> Dict[str, Any]:
        """
        Setup and initialize Universal CLI Translator integration.
        
        Returns:
            Dictionary with setup results
        """
        self._logger.info("Setting up Universal CLI Translator integration")
        
        if not self._components["universal_cli_translator"]:
            return {
                "success": False,
                "error": "Universal CLI Translator component not available"
            }
        
        # Get common CLI tools suggestions
        common_tools = [
            "git", "docker", "aws", "kubectl", "terraform", "npm", "pip",
            "gcloud", "az", "heroku", "ansible", "vagrant", "ssh", "scp"
        ]
        
        available_tools = set()
        tool_info = {}
        
        for tool in common_tools:
            try:
                suggestions = await self._components["universal_cli_translator"].get_tool_suggestions(tool)
                if tool in suggestions:
                    available_tools.add(tool)
                    
                    # Get tool information
                    from angela.execution.engine import execution_engine
                    try:
                        stdout, stderr, return_code = await execution_engine.execute_command(
                            command=f"{tool} --version",
                            check_safety=True
                        )
                        
                        if return_code == 0:
                            tool_info[tool] = stdout.strip()
                        else:
                            stdout, stderr, return_code = await execution_engine.execute_command(
                                command=f"{tool} -v",
                                check_safety=True
                            )
                            if return_code == 0:
                                tool_info[tool] = stdout.strip()
                    except Exception:
                        pass
            except Exception as e:
                self._logger.debug(f"Error checking tool {tool}: {str(e)}")
        
        return {
            "success": True,
            "available_tools": list(available_tools),
            "tool_info": tool_info,
            "missing_common_tools": [tool for tool in common_tools if tool not in available_tools]
        }
    
    async def execute_cross_tool_workflow(
        self,
        request: str,
        context: Dict[str, Any],
        suggested_tools: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a workflow involving multiple tools.
        
        Args:
            request: Natural language request
            context: Context information
            suggested_tools: Optional list of suggested tools to use
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing cross-tool workflow: {request}")
        
        if not self._ready:
            await self.initialize()
            
            if not self._ready:
                return {
                    "success": False,
                    "error": "Phase 12 integration components not available"
                }
        
        # If no suggested tools provided, analyze the request
        if not suggested_tools:
            tools_analysis = await self._analyze_tools_in_request(request, context)
            suggested_tools = tools_analysis.get("primary_tools", [])
        
        # Execute the workflow
        from angela.context.session import session_manager
        session_manager.add_entity("requested_tools", "workflow", suggested_tools)
        
        # Use the orchestrator to handle the complex workflow
        from angela.orchestrator import orchestrator
        
        result = await orchestrator._process_complex_workflow_request(
            request=request,
            context=context,
            execute=not dry_run,
            dry_run=dry_run
        )
        
        # Add tools information to the result
        result["suggested_tools"] = suggested_tools
        
        return result
    
    async def status(self) -> Dict[str, Any]:
        """
        Get the status of Phase 12 integration.
        
        Returns:
            Dictionary with status information
        """
        if not self._ready:
            try:
                await self.initialize()
            except Exception as e:
                return {
                    "phase": "12",
                    "enabled": False,
                    "description": "Advanced Orchestration & Universal Tool Translation",
                    "error": str(e),
                    "components_available": {
                        name: component is not None
                        for name, component in self._components.items()
                    }
                }
        
        # Get available tools
        available_tools = []
        if self._components["universal_cli_translator"]:
            try:
                common_tools = ["git", "docker", "aws", "kubectl", "terraform", "npm", "pip"]
                for tool in common_tools:
                    suggestions = await self._components["universal_cli_translator"].get_tool_suggestions(tool)
                    if tool in suggestions:
                        available_tools.append(tool)
            except Exception as e:
                self._logger.debug(f"Error getting available tools: {str(e)}")
        
        # Get CI/CD information
        ci_cd_platforms = []
        if self._components["ci_cd_integration"]:
            ci_cd_platforms = self._components["ci_cd_integration"]._supported_platforms
        
        # Get proactive assistant status
        proactive_status = "inactive"
        if self._components["proactive_assistant"]:
            proactive_status = "active" if getattr(self._components["proactive_assistant"], "_active_listening", False) else "inactive"
        
        return {
            "phase": "12",
            "enabled": self._ready,
            "description": "Advanced Orchestration & Universal Tool Translation",
            "components": {
                name: component is not None
                for name, component in self._components.items()
            },
            "available_tools": available_tools,
            "ci_cd_platforms": ci_cd_platforms,
            "proactive_assistant": proactive_status,
            "capabilities": [
                "Universal CLI Translation",
                "Complex Cross-Tool Workflows",
                "Automated CI/CD Pipeline Execution",
                "Enhanced Proactive Assistance"
            ]
        }

# Create a global instance
phase12_integration = Phase12Integration()

# Register it in the service registry
registry.register("phase12_integration", phase12_integration)

# Initialize on module import (async)
async def _init_phase12():
    try:
        await phase12_integration.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize Phase 12 integration: {str(e)}")

# Schedule initialization to run soon without blocking import
import asyncio
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Schedule in running loop
        loop.create_task(_init_phase12())
    else:
        # Run short async task
        loop.run_until_complete(_init_phase12())
except Exception as e:
    logger.debug(f"Could not initialize Phase 12 immediately: {str(e)}")
