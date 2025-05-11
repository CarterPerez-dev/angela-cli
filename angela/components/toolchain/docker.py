# angela/components/toolchain/docker.py
"""
Docker toolchain integration for Angela CLI.

This module provides functionality for interacting with Docker and Docker Compose,
including container management, image operations, and Dockerfile generation.
"""
import asyncio
import json
import os
import re
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union, Set

from angela.utils.logging import get_logger
# Updated imports to use API layer
from angela.api.execution import get_execution_engine
from angela.api.context import get_context_manager
from angela.api.safety import get_command_risk_classifier

logger = get_logger(__name__)

# Constants for Docker file templates
DOCKERFILE_TEMPLATES = {
    "python": """FROM python:{python_version}-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

{expose_port}

CMD ["python", "{entry_point}"]
""",
    "node": """FROM node:{node_version}-alpine

WORKDIR /app

COPY package.json {package_lock} ./
RUN npm install {production_flag}

COPY . .

{expose_port}

CMD ["npm", "start"]
""",
    "golang": """FROM golang:{go_version}-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o main {main_file}

FROM alpine:latest

WORKDIR /app
COPY --from=builder /app/main .

{expose_port}

CMD ["./main"]
""",
    "java": """FROM maven:{maven_version}-jdk-{java_version} AS builder

WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline

COPY src ./src
RUN mvn package -DskipTests

FROM openjdk:{java_version}-jre-slim

WORKDIR /app
COPY --from=builder /app/target/{jar_file} app.jar

{expose_port}

CMD ["java", "-jar", "app.jar"]
""",
    "ruby": """FROM ruby:{ruby_version}-alpine

WORKDIR /app

COPY Gemfile Gemfile.lock ./
RUN bundle install --jobs 4 --retry 3

COPY . .

{expose_port}

CMD ["ruby", "{entry_point}"]
"""
}

DOCKER_COMPOSE_TEMPLATE = """version: '3'

services:
{services}
{networks}
{volumes}
"""

SERVICE_TEMPLATE = """  {service_name}:
    image: {image}
    build:
      context: {context}
      dockerfile: {dockerfile}
    {ports}
    {environment}
    {volumes}
    {depends_on}
    {networks}
"""

class DockerIntegration:
    """
    Integration with Docker and Docker Compose.
    
    Provides methods for interacting with Docker and Docker Compose,
    including command execution, file generation, and status checking.
    """
    
    def __init__(self):
        """Initialize Docker integration."""
        self._logger = logger
    
    async def is_docker_available(self) -> bool:
        """
        Check if Docker is available on the system.
        
        Returns:
            True if Docker is available, False otherwise
        """
        try:
            # Get execution engine from API
            execution_engine = get_execution_engine()
            
            stdout, stderr, exit_code = await execution_engine.execute_command(
                "docker --version",
                check_safety=True
            )
            return exit_code == 0
        except Exception as e:
            self._logger.error(f"Error checking Docker availability: {str(e)}")
            return False
    
    async def is_docker_compose_available(self) -> bool:
        """
        Check if Docker Compose is available on the system.
        
        Returns:
            True if Docker Compose is available, False otherwise
        """
        try:
            # Get execution engine from API
            execution_engine = get_execution_engine()
            
            # Try docker compose (v2) command first
            stdout, stderr, exit_code = await execution_engine.execute_command(
                "docker compose version",
                check_safety=True
            )
            if exit_code == 0:
                return True
            
            # Fall back to docker-compose (v1) command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                "docker-compose --version",
                check_safety=True
            )
            return exit_code == 0
        except Exception as e:
            self._logger.error(f"Error checking Docker Compose availability: {str(e)}")
            return False
    
    async def get_docker_compose_command(self) -> str:
        """
        Get the appropriate Docker Compose command (v1 or v2).
        
        Returns:
            String with the appropriate command
        """
        try:
            # Check if docker compose (v2) is available
            stdout, stderr, exit_code = await execution_engine.execute_command(
                "docker compose version",
                check_safety=True
            )
            if exit_code == 0:
                return "docker compose"
            
            # Fall back to docker-compose (v1)
            return "docker-compose"
        except Exception as e:
            self._logger.error(f"Error determining Docker Compose command: {str(e)}")
            return "docker compose"  # Default to v2 compose
    
    #
    # Container Management
    #
    
    async def list_containers(self, all_containers: bool = False) -> Dict[str, Any]:
        """
        List Docker containers.
        
        Args:
            all_containers: Whether to list all containers (including stopped)
            
        Returns:
            Dictionary with container list and status information
        """
        self._logger.info(f"Listing {'all' if all_containers else 'running'} Docker containers")
        
        try:
            # Get execution engine from API
            execution_engine = get_execution_engine()
            
            # Build command
            command = "docker ps --format json"
            if all_containers:
                command += " --all"
            
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True
            )
            
                if exit_code != 0:
                    return {
                        "success": False,
                        "error": f"Error listing containers: {stderr}",
                        "containers": []
                    }
                
                # Parse tabular output
                lines = stdout.strip().split('\n')
                if len(lines) <= 1:  # Only header, no containers
                    return {
                        "success": True,
                        "containers": [],
                        "count": 0
                    }
                
                # Skip header
                lines = lines[1:]
                
                # Parse container lines
                for line in lines:
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 7:
                        container = {
                            "id": parts[0],
                            "image": parts[1],
                            "command": parts[2],
                            "created": parts[3],
                            "status": parts[4],
                            "ports": parts[5] if len(parts) > 5 else "",
                            "names": parts[6] if len(parts) > 6 else ""
                        }
                        containers.append(container)
            else:
                # Parse JSON output for newer Docker versions
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            container = json.loads(line)
                            containers.append(container)
                        except json.JSONDecodeError as e:
                            self._logger.error(f"Error parsing container JSON: {str(e)}")
            
            return {
                "success": True,
                "containers": containers,
                "count": len(containers)
            }
        except Exception as e:
            self._logger.exception(f"Error listing containers: {str(e)}")
            return {
                "success": False,
                "error": f"Error listing containers: {str(e)}",
                "containers": []
            }
    
    async def get_container_details(self, container_id_or_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific container.
        
        Args:
            container_id_or_name: Container ID or name
            
        Returns:
            Dictionary with container details
        """
        self._logger.info(f"Getting details for container: {container_id_or_name}")
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                f"docker inspect {container_id_or_name}",
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error inspecting container: {stderr}"
                }
            
            # Parse container details
            try:
                details = json.loads(stdout)
                if not details or not isinstance(details, list):
                    return {
                        "success": False,
                        "error": "Invalid container details format"
                    }
                
                # Get first item (there should be only one)
                container_info = details[0]
                
                # Extract useful information
                result = {
                    "success": True,
                    "id": container_info.get("Id", ""),
                    "name": container_info.get("Name", "").lstrip('/'),
                    "image": container_info.get("Config", {}).get("Image", ""),
                    "state": container_info.get("State", {}),
                    "network_settings": container_info.get("NetworkSettings", {}),
                    "mounts": container_info.get("Mounts", []),
                    "config": container_info.get("Config", {}),
                    "created": container_info.get("Created", ""),
                    "full_details": container_info
                }
                
                return result
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Error parsing container details: {str(e)}"
                }
        except Exception as e:
            self._logger.exception(f"Error getting container details: {str(e)}")
            return {
                "success": False,
                "error": f"Error getting container details: {str(e)}"
            }
    
    async def start_container(self, container_id_or_name: str) -> Dict[str, Any]:
        """
        Start a Docker container.
        
        Args:
            container_id_or_name: Container ID or name
            
        Returns:
            Dictionary with operation status
        """
        self._logger.info(f"Starting container: {container_id_or_name}")
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                f"docker start {container_id_or_name}",
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error starting container: {stderr}"
                }
            
            return {
                "success": True,
                "message": f"Container {container_id_or_name} started successfully",
                "output": stdout.strip()
            }
        except Exception as e:
            self._logger.exception(f"Error starting container: {str(e)}")
            return {
                "success": False,
                "error": f"Error starting container: {str(e)}"
            }
    
    async def stop_container(self, container_id_or_name: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Stop a Docker container.
        
        Args:
            container_id_or_name: Container ID or name
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary with operation status
        """
        self._logger.info(f"Stopping container: {container_id_or_name}")
        
        try:
            # Build command
            command = f"docker stop {container_id_or_name}"
            if timeout is not None:
                command += f" --time {timeout}"
            
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error stopping container: {stderr}"
                }
            
            return {
                "success": True,
                "message": f"Container {container_id_or_name} stopped successfully",
                "output": stdout.strip()
            }
        except Exception as e:
            self._logger.exception(f"Error stopping container: {str(e)}")
            return {
                "success": False,
                "error": f"Error stopping container: {str(e)}"
            }
    
    async def restart_container(self, container_id_or_name: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Restart a Docker container.
        
        Args:
            container_id_or_name: Container ID or name
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary with operation status
        """
        self._logger.info(f"Restarting container: {container_id_or_name}")
        
        try:
            # Build command
            command = f"docker restart {container_id_or_name}"
            if timeout is not None:
                command += f" --time {timeout}"
            
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error restarting container: {stderr}"
                }
            
            return {
                "success": True,
                "message": f"Container {container_id_or_name} restarted successfully",
                "output": stdout.strip()
            }
        except Exception as e:
            self._logger.exception(f"Error restarting container: {str(e)}")
            return {
                "success": False,
                "error": f"Error restarting container: {str(e)}"
            }
    
    async def remove_container(
        self, 
        container_id_or_name: str, 
        force: bool = False,
        remove_volumes: bool = False
    ) -> Dict[str, Any]:
        """
        Remove a Docker container.
        
        Args:
            container_id_or_name: Container ID or name
            force: Force removal of running container
            remove_volumes: Remove anonymous volumes
            
        Returns:
            Dictionary with operation status
        """
        self._logger.info(f"Removing container: {container_id_or_name}")
        
        try:
            # Build command
            command = f"docker rm {container_id_or_name}"
            if force:
                command += " --force"
            if remove_volumes:
                command += " --volumes"
            
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error removing container: {stderr}"
                }
            
            return {
                "success": True,
                "message": f"Container {container_id_or_name} removed successfully",
                "output": stdout.strip()
            }
        except Exception as e:
            self._logger.exception(f"Error removing container: {str(e)}")
            return {
                "success": False,
                "error": f"Error removing container: {str(e)}"
            }
    
    async def get_container_logs(
        self, 
        container_id_or_name: str, 
        tail: Optional[int] = None,
        follow: bool = False,
        timestamps: bool = False,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get logs from a Docker container.
        
        Args:
            container_id_or_name: Container ID or name
            tail: Number of lines to show from the end
            follow: Follow log output
            timestamps: Show timestamps
            since: Show logs since timestamp
            until: Show logs until timestamp
            
        Returns:
            Dictionary with container logs
        """
        self._logger.info(f"Getting logs for container: {container_id_or_name}")
        
        # Build command
        command = f"docker logs {container_id_or_name}"
        if tail is not None:
            command += f" --tail {tail}"
        if timestamps:
            command += " --timestamps"
        if since:
            command += f" --since {since}"
        if until:
            command += f" --until {until}"
        
        try:
            if follow:
                # For follow mode, we need to stream the output
                # This is a simplified implementation - a more complex one would use
                # a proper streaming mechanism with callbacks
                command += " --follow"
                
                # Limit to 30 seconds maximum for safety
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    # Wait for up to 30 seconds
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=30
                    )
                    stdout_str = stdout.decode('utf-8', errors='replace')
                    stderr_str = stderr.decode('utf-8', errors='replace')
                    
                    return {
                        "success": process.returncode == 0,
                        "logs": stdout_str,
                        "error": stderr_str if process.returncode != 0 else None,
                        "followed": True,
                        "truncated": False
                    }
                except asyncio.TimeoutError:
                    # Kill the process after timeout
                    process.kill()
                    return {
                        "success": True,
                        "logs": "Log streaming timeout after 30 seconds",
                        "followed": True,
                        "truncated": True
                    }
            else:
                # For non-follow mode, just execute the command
                stdout, stderr, exit_code = await execution_engine.execute_command(
                    command,
                    check_safety=True
                )
                
                if exit_code != 0:
                    return {
                        "success": False,
                        "error": f"Error getting container logs: {stderr}"
                    }
                
                return {
                    "success": True,
                    "logs": stdout,
                    "followed": False
                }
        except Exception as e:
            self._logger.exception(f"Error getting container logs: {str(e)}")
            return {
                "success": False,
                "error": f"Error getting container logs: {str(e)}"
            }
    
    async def run_container(
        self,
        image: str,
        command: Optional[str] = None,
        name: Optional[str] = None,
        ports: Optional[List[str]] = None,
        volumes: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = True,
        remove: bool = False,
        network: Optional[str] = None,
        interactive: bool = False
    ) -> Dict[str, Any]:
        """
        Run a Docker container.
        
        Args:
            image: Docker image to run
            command: Command to run in the container
            name: Name for the container
            ports: Port mappings (host:container)
            volumes: Volume mappings (host:container)
            environment: Environment variables
            detach: Run container in background
            remove: Remove container when it exits
            network: Connect to network
            interactive: Run container with interactive mode
            
        Returns:
            Dictionary with operation status
        """
        self._logger.info(f"Running container from image: {image}")
        
        # Build command
        docker_command = "docker run"
        
        if detach:
            docker_command += " --detach"
        if remove:
            docker_command += " --rm"
        if interactive:
            docker_command += " --interactive --tty"
        
        # Add name if provided
        if name:
            docker_command += f" --name {name}"
        
        # Add network if provided
        if network:
            docker_command += f" --network {network}"
        
        # Add port mappings
        if ports:
            for port_mapping in ports:
                docker_command += f" --publish {port_mapping}"
        
        # Add volume mappings
        if volumes:
            for volume_mapping in volumes:
                docker_command += f" --volume {volume_mapping}"
        
        # Add environment variables
        if environment:
            for key, value in environment.items():
                docker_command += f" --env {key}={value}"
        
        # Add image
        docker_command += f" {image}"
        
        # Add command if provided
        if command:
            docker_command += f" {command}"
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                docker_command,
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error running container: {stderr}",
                    "command": docker_command
                }
            
            container_id = stdout.strip()
            
            return {
                "success": True,
                "message": f"Container started successfully{'in detached mode' if detach else ''}",
                "container_id": container_id,
                "command": docker_command
            }
        except Exception as e:
            self._logger.exception(f"Error running container: {str(e)}")
            return {
                "success": False,
                "error": f"Error running container: {str(e)}",
                "command": docker_command
            }
    
    async def exec_in_container(
        self,
        container_id_or_name: str,
        command: str,
        interactive: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a command in a running container.
        
        Args:
            container_id_or_name: Container ID or name
            command: Command to execute
            interactive: Run in interactive mode
            
        Returns:
            Dictionary with execution result
        """
        self._logger.info(f"Executing command in container {container_id_or_name}: {command}")
        
        # Build docker exec command
        docker_command = f"docker exec"
        if interactive:
            docker_command += " --interactive --tty"
        
        docker_command += f" {container_id_or_name} {command}"
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                docker_command,
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error executing command in container: {stderr}",
                    "command": docker_command
                }
            
            return {
                "success": True,
                "output": stdout,
                "command": docker_command
            }
        except Exception as e:
            self._logger.exception(f"Error executing command in container: {str(e)}")
            return {
                "success": False,
                "error": f"Error executing command in container: {str(e)}",
                "command": docker_command
            }
    
    #
    # Image Management
    #
    
    async def list_images(self, show_all: bool = False) -> Dict[str, Any]:
        """
        List Docker images.
        
        Args:
            show_all: Whether to show all images (including intermediate)
            
        Returns:
            Dictionary with image list
        """
        self._logger.info("Listing Docker images")
        
        try:
            # Build command
            command = "docker images --format json"
            if show_all:
                command += " --all"
            
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error listing images: {stderr}",
                    "images": []
                }
            
            # Parse image information
            images = []
            
            # Handle older Docker versions that don't support --format json
            if not stdout.strip().startswith('[') and not stdout.strip().startswith('{'):
                # Fall back to regular format parsing
                fallback_command = f"docker images{' --all' if show_all else ''}"
                stdout, stderr, exit_code = await execution_engine.execute_command(
                    fallback_command,
                    check_safety=True
                )
                
                if exit_code != 0:
                    return {
                        "success": False,
                        "error": f"Error listing images: {stderr}",
                        "images": []
                    }
                
                # Parse tabular output
                lines = stdout.strip().split('\n')
                if len(lines) <= 1:  # Only header, no images
                    return {
                        "success": True,
                        "images": [],
                        "count": 0
                    }
                
                # Skip header
                lines = lines[1:]
                
                # Parse image lines
                for line in lines:
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 5:
                        image = {
                            "repository": parts[0],
                            "tag": parts[1],
                            "id": parts[2],
                            "created": parts[3],
                            "size": parts[4]
                        }
                        images.append(image)
            else:
                # Parse JSON output for newer Docker versions
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            image = json.loads(line)
                            images.append(image)
                        except json.JSONDecodeError as e:
                            self._logger.error(f"Error parsing image JSON: {str(e)}")
            
            return {
                "success": True,
                "images": images,
                "count": len(images)
            }
        except Exception as e:
            self._logger.exception(f"Error listing images: {str(e)}")
            return {
                "success": False,
                "error": f"Error listing images: {str(e)}",
                "images": []
            }
    
    async def build_image(
        self,
        context_path: Union[str, Path],
        tag: Optional[str] = None,
        dockerfile: Optional[str] = None,
        build_args: Optional[Dict[str, str]] = None,
        no_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Build a Docker image.
        
        Args:
            context_path: Path to build context
            tag: Tag for the built image
            dockerfile: Path to Dockerfile (relative to context_path)
            build_args: Build arguments
            no_cache: Do not use cache when building
            
        Returns:
            Dictionary with build result
        """
        self._logger.info(f"Building Docker image from context: {context_path}")
        
        # Ensure context path exists
        context_path_obj = Path(context_path)
        if not context_path_obj.exists() or not context_path_obj.is_dir():
            return {
                "success": False,
                "error": f"Build context does not exist or is not a directory: {context_path}"
            }
        
        # Build command
        command = f"docker build {context_path_obj}"
        
        if tag:
            command += f" --tag {tag}"
        
        if dockerfile:
            command += f" --file {dockerfile}"
        
        if build_args:
            for key, value in build_args.items():
                command += f" --build-arg {key}={value}"
        
        if no_cache:
            command += " --no-cache"
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error building image: {stderr}",
                    "command": command
                }
            
            # Parse image ID from output
            image_id = None
            for line in stdout.splitlines():
                if line.strip().startswith("Successfully built "):
                    image_id = line.strip().split(" ")[-1]
                    break
            
            return {
                "success": True,
                "message": "Image built successfully",
                "image_id": image_id,
                "tag": tag,
                "output": stdout,
                "command": command
            }
        except Exception as e:
            self._logger.exception(f"Error building image: {str(e)}")
            return {
                "success": False,
                "error": f"Error building image: {str(e)}",
                "command": command
            }
    
    async def remove_image(
        self,
        image_id_or_name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Remove a Docker image.
        
        Args:
            image_id_or_name: Image ID or name
            force: Force removal
            
        Returns:
            Dictionary with removal result
        """
        self._logger.info(f"Removing Docker image: {image_id_or_name}")
        
        # Build command
        command = f"docker rmi {image_id_or_name}"
        if force:
            command += " --force"
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error removing image: {stderr}",
                    "command": command
                }
            
            return {
                "success": True,
                "message": f"Image {image_id_or_name} removed successfully",
                "output": stdout.strip(),
                "command": command
            }
        except Exception as e:
            self._logger.exception(f"Error removing image: {str(e)}")
            return {
                "success": False,
                "error": f"Error removing image: {str(e)}",
                "command": command
            }
    
    async def pull_image(self, image_name: str) -> Dict[str, Any]:
        """
        Pull a Docker image from a registry.
        
        Args:
            image_name: Image name to pull
            
        Returns:
            Dictionary with pull result
        """
        self._logger.info(f"Pulling Docker image: {image_name}")
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                f"docker pull {image_name}",
                check_safety=True
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error pulling image: {stderr}"
                }
            
            return {
                "success": True,
                "message": f"Image {image_name} pulled successfully",
                "output": stdout.strip()
            }
        except Exception as e:
            self._logger.exception(f"Error pulling image: {str(e)}")
            return {
                "success": False,
                "error": f"Error pulling image: {str(e)}"
            }
    
    #
    # Docker Compose
    #
    
    async def compose_up(
        self,
        compose_file: Optional[Union[str, Path]] = None,
        project_directory: Optional[Union[str, Path]] = None,
        detach: bool = True,
        build: bool = False,
        no_recreate: bool = False,
        force_recreate: bool = False,
        services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Start containers using Docker Compose.
        
        Args:
            compose_file: Path to docker-compose.yml (default: docker-compose.yml in project_directory)
            project_directory: Project directory (default: current directory)
            detach: Run in background
            build: Build images before starting
            no_recreate: Don't recreate containers
            force_recreate: Force recreate containers
            services: List of services to start (default: all)
            
        Returns:
            Dictionary with operation result
        """
        self._logger.info(f"Starting services with Docker Compose")
        
        # Get appropriate Docker Compose command
        compose_command = await self.get_docker_compose_command()
        
        # Determine project directory
        if project_directory is None:
            # Get context manager from API
            context_manager = get_context_manager()
            project_directory = context_manager.cwd
        else:
            project_directory = Path(project_directory)
        
        # Build command
        command = f"{compose_command}"
        
        if compose_file:
            command += f" -f {compose_file}"
        
        command += " up"
        
        if detach:
            command += " -d"
        
        if build:
            command += " --build"
        
        if no_recreate:
            command += " --no-recreate"
        
        if force_recreate:
            command += " --force-recreate"
        
        # Add services if specified
        if services:
            command += " " + " ".join(services)
        
        try:
            # Get execution engine from API
            execution_engine = get_execution_engine()
            
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True,
                working_dir=str(project_directory)
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error starting Docker Compose services: {stderr}",
                    "command": command,
                    "working_dir": str(project_directory)
                }
            
            return {
                "success": True,
                "message": "Docker Compose services started successfully",
                "output": stdout,
                "command": command,
                "working_dir": str(project_directory)
            }
        except Exception as e:
            self._logger.exception(f"Error starting Docker Compose services: {str(e)}")
            return {
                "success": False,
                "error": f"Error starting Docker Compose services: {str(e)}",
                "command": command,
                "working_dir": str(project_directory)
            }
    
    async def compose_down(
        self,
        compose_file: Optional[Union[str, Path]] = None,
        project_directory: Optional[Union[str, Path]] = None,
        remove_images: bool = False,
        remove_volumes: bool = False,
        remove_orphans: bool = False
    ) -> Dict[str, Any]:
        """
        Stop and remove containers, networks, volumes, and images created by compose up.
        
        Args:
            compose_file: Path to docker-compose.yml (default: docker-compose.yml in project_directory)
            project_directory: Project directory (default: current directory)
            remove_images: Remove images
            remove_volumes: Remove volumes
            remove_orphans: Remove containers for services not defined in the Compose file
            
        Returns:
            Dictionary with operation result
        """
        self._logger.info(f"Stopping services with Docker Compose")
        
        # Get appropriate Docker Compose command
        compose_command = await self.get_docker_compose_command()
        
        # Determine project directory
        if project_directory is None:
            project_directory = context_manager.cwd
        else:
            project_directory = Path(project_directory)
        
        # Build command
        command = f"{compose_command}"
        
        if compose_file:
            command += f" -f {compose_file}"
        
        command += " down"
        
        if remove_images:
            command += " --rmi all"
        
        if remove_volumes:
            command += " --volumes"
        
        if remove_orphans:
            command += " --remove-orphans"
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True,
                working_dir=str(project_directory)
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error stopping Docker Compose services: {stderr}",
                    "command": command,
                    "working_dir": str(project_directory)
                }
            
            return {
                "success": True,
                "message": "Docker Compose services stopped successfully",
                "output": stdout,
                "command": command,
                "working_dir": str(project_directory)
            }
        except Exception as e:
            self._logger.exception(f"Error stopping Docker Compose services: {str(e)}")
            return {
                "success": False,
                "error": f"Error stopping Docker Compose services: {str(e)}",
                "command": command,
                "working_dir": str(project_directory)
            }
    
    async def compose_logs(
        self,
        compose_file: Optional[Union[str, Path]] = None,
        project_directory: Optional[Union[str, Path]] = None,
        services: Optional[List[str]] = None,
        follow: bool = False,
        tail: Optional[int] = None,
        timestamps: bool = False
    ) -> Dict[str, Any]:
        """
        View logs from Docker Compose services.
        
        Args:
            compose_file: Path to docker-compose.yml (default: docker-compose.yml in project_directory)
            project_directory: Project directory (default: current directory)
            services: List of services to show logs for (default: all)
            follow: Follow log output
            tail: Number of lines to show from the end
            timestamps: Show timestamps
            
        Returns:
            Dictionary with logs
        """
        self._logger.info(f"Getting logs from Docker Compose services")
        
        # Get appropriate Docker Compose command
        compose_command = await self.get_docker_compose_command()
        
        # Determine project directory
        if project_directory is None:
            project_directory = context_manager.cwd
        else:
            project_directory = Path(project_directory)
        
        # Build command
        command = f"{compose_command}"
        
        if compose_file:
            command += f" -f {compose_file}"
        
        command += " logs"
        
        if follow:
            command += " --follow"
        
        if tail is not None:
            command += f" --tail={tail}"
        
        if timestamps:
            command += " --timestamps"
        
        # Add services if specified
        if services:
            command += " " + " ".join(services)
        
        try:
            if follow:
                # For follow mode, we need to stream the output
                # This is a simplified implementation
                
                # Limit to 30 seconds maximum for safety
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(project_directory)
                )
                
                try:
                    # Wait for up to 30 seconds
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=30
                    )
                    stdout_str = stdout.decode('utf-8', errors='replace')
                    stderr_str = stderr.decode('utf-8', errors='replace')
                    
                    return {
                        "success": process.returncode == 0,
                        "logs": stdout_str,
                        "error": stderr_str if process.returncode != 0 else None,
                        "followed": True,
                        "truncated": False,
                        "command": command,
                        "working_dir": str(project_directory)
                    }
                except asyncio.TimeoutError:
                    # Kill the process after timeout
                    process.kill()
                    return {
                        "success": True,
                        "logs": "Log streaming timeout after 30 seconds",
                        "followed": True,
                        "truncated": True,
                        "command": command,
                        "working_dir": str(project_directory)
                    }
            else:
                # Execute command
                stdout, stderr, exit_code = await execution_engine.execute_command(
                    command,
                    check_safety=True,
                    working_dir=str(project_directory)
                )
                
                if exit_code != 0:
                    return {
                        "success": False,
                        "error": f"Error getting Docker Compose logs: {stderr}",
                        "command": command,
                        "working_dir": str(project_directory)
                    }
                
                return {
                    "success": True,
                    "logs": stdout,
                    "command": command,
                    "working_dir": str(project_directory)
                }
        except Exception as e:
            self._logger.exception(f"Error getting Docker Compose logs: {str(e)}")
            return {
                "success": False,
                "error": f"Error getting Docker Compose logs: {str(e)}",
                "command": command,
                "working_dir": str(project_directory)
            }
    
    async def compose_ps(
        self,
        compose_file: Optional[Union[str, Path]] = None,
        project_directory: Optional[Union[str, Path]] = None,
        services: Optional[List[str]] = None,
        all_services: bool = False
    ) -> Dict[str, Any]:
        """
        List Docker Compose services.
        
        Args:
            compose_file: Path to docker-compose.yml (default: docker-compose.yml in project_directory)
            project_directory: Project directory (default: current directory)
            services: List of services to show (default: all)
            all_services: Show stopped services
            
        Returns:
            Dictionary with services list
        """
        self._logger.info(f"Listing Docker Compose services")
        
        # Get appropriate Docker Compose command
        compose_command = await self.get_docker_compose_command()
        
        # Determine project directory
        if project_directory is None:
            project_directory = context_manager.cwd
        else:
            project_directory = Path(project_directory)
        
        # Build command
        command = f"{compose_command}"
        
        if compose_file:
            command += f" -f {compose_file}"
        
        command += " ps"
        
        if all_services:
            command += " --all"
        
        # Add services if specified
        if services:
            command += " " + " ".join(services)
        
        try:
            # Execute command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True,
                working_dir=str(project_directory)
            )
            
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Error listing Docker Compose services: {stderr}",
                    "command": command,
                    "working_dir": str(project_directory)
                }
            
            # Parse service information
            services_info = []
            
            # Skip empty output
            if not stdout.strip():
                return {
                    "success": True,
                    "services": [],
                    "count": 0,
                    "command": command,
                    "working_dir": str(project_directory)
                }
            
            # Parse table output (format varies between compose versions)
            lines = stdout.strip().split('\n')
            if len(lines) <= 1:  # Only header, no services
                return {
                    "success": True,
                    "services": [],
                    "count": 0,
                    "command": command,
                    "working_dir": str(project_directory)
                }
            
            # Try to parse as a table with header
            header = lines[0]
            data_lines = lines[1:]
            
            for line in data_lines:
                # Different compose versions have different formats
                # Try to extract at least name and state
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 2:
                    service = {"name": parts[0]}
                    
                    # Detect format
                    if "Up" in line or "Exit" in line:
                        # Search for status like "Up 2 hours" or "Exit (1) 5 minutes ago"
                        status_match = re.search(r'(Up|Exit \(\d+\))[^,]*', line)
                        if status_match:
                            service["status"] = status_match.group(0)
                    
                    # Add all parts with labels if we can identify them
                    if len(header.split()) >= len(parts):
                        header_parts = re.split(r'\s{2,}', header.strip())
                        for i, value in enumerate(parts):
                            if i < len(header_parts):
                                key = header_parts[i].lower().replace(' ', '_')
                                service[key] = value
                    
                    services_info.append(service)
            
            return {
                "success": True,
                "services": services_info,
                "count": len(services_info),
                "raw_output": stdout,
                "command": command,
                "working_dir": str(project_directory)
            }
        except Exception as e:
            self._logger.exception(f"Error listing Docker Compose services: {str(e)}")
            return {
                "success": False,
                "error": f"Error listing Docker Compose services: {str(e)}",
                "command": command,
                "working_dir": str(project_directory)
            }
    
    #
    # Dockerfile Generation
    #
    
    async def detect_project_type(
        self, 
        project_directory: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Detect the type of project in a directory.
        
        Args:
            project_directory: Path to the project directory
            
        Returns:
            Dictionary with project type and details
        """
        self._logger.info(f"Detecting project type in: {project_directory}")
        
        project_dir = Path(project_directory)
        if not project_dir.exists() or not project_dir.is_dir():
            return {
                "success": False,
                "error": f"Project directory does not exist or is not a directory: {project_directory}"
            }
        
        # Look for common project markers
        markers = {
            "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
            "node": ["package.json", "yarn.lock", "package-lock.json"],
            "golang": ["go.mod", "go.sum"],
            "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
            "ruby": ["Gemfile", "Gemfile.lock"],
            "php": ["composer.json", "composer.lock"],
            "dotnet": ["*.csproj", "*.fsproj", "*.vbproj"]
        }
        
        # Check for each marker
        detected_types = {}
        
        for project_type, files in markers.items():
            for file_pattern in files:
                # Handle glob patterns
                if "*" in file_pattern:
                    matching_files = list(project_dir.glob(file_pattern))
                    if matching_files:
                        detected_types[project_type] = {
                            "marker_file": str(matching_files[0].relative_to(project_dir)),
                            "confidence": 0.9
                        }
                        break
                else:
                    file_path = project_dir / file_pattern
                    if file_path.exists():
                        detected_types[project_type] = {
                            "marker_file": file_pattern,
                            "confidence": 0.9
                        }
                        break
        
        # If nothing detected, try to infer from file extensions
        if not detected_types:
            extensions = {}
            
            # Count file extensions
            for file_path in project_dir.glob("**/*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext:
                        extensions[ext] = extensions.get(ext, 0) + 1
            
            # Map extensions to project types
            extension_types = {
                ".py": "python",
                ".js": "node",
                ".ts": "node",
                ".jsx": "node",
                ".tsx": "node",
                ".go": "golang",
                ".java": "java",
                ".rb": "ruby",
                ".php": "php",
                ".cs": "dotnet",
                ".fs": "dotnet",
                ".vb": "dotnet"
            }
            
            # Count by project type
            type_counts = {}
            for ext, count in extensions.items():
                if ext in extension_types:
                    project_type = extension_types[ext]
                    type_counts[project_type] = type_counts.get(project_type, 0) + count
            
            # Sort by count
            if type_counts:
                most_common = max(type_counts.items(), key=lambda x: x[1])
                detected_types[most_common[0]] = {
                    "inferred_from_extensions": True,
                    "file_count": most_common[1],
                    "confidence": 0.7
                }
        
        # Detect versions for the project
        version_info = {}
        for project_type in detected_types.keys():
            if project_type == "python":
                version_info["python_version"] = await self._detect_python_version(project_dir)
            elif project_type == "node":
                version_info["node_version"] = await self._detect_node_version(project_dir)
            elif project_type == "golang":
                version_info["go_version"] = await self._detect_go_version(project_dir)
            elif project_type == "java":
                java_info = await self._detect_java_version(project_dir)
                version_info.update(java_info)
            elif project_type == "ruby":
                version_info["ruby_version"] = await self._detect_ruby_version(project_dir)
        
        # Determine the most likely project type
        result = {
            "success": True,
            "detected_types": detected_types,
            "version_info": version_info
        }
        
        if detected_types:
            # Find the type with highest confidence
            best_type = max(detected_types.items(), key=lambda x: x[1]["confidence"])
            result["primary_type"] = best_type[0]
            result["details"] = best_type[1]
        else:
            result["primary_type"] = "unknown"
        
        return result
    
    async def _detect_python_version(self, project_dir: Path) -> str:
        """
        Detect Python version used in a project.
        
        Args:
            project_dir: Path to the project directory
            
        Returns:
            Python version string
        """
        # Check for explicit version in pyproject.toml
        pyproject_path = project_dir / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, 'r') as f:
                    content = f.read()
                    # Look for requires-python or python_requires
                    requires_match = re.search(r'(requires-python|python_requires)\s*=\s*["\']([^"\']+)["\']', content)
                    if requires_match:
                        version_req = requires_match.group(2)
                        # Extract a simple version number from the requirement
                        version_match = re.search(r'(\d+\.\d+)', version_req)
                        if version_match:
                            return version_match.group(1)
            except Exception as e:
                self._logger.error(f"Error reading pyproject.toml: {str(e)}")
        
        # Check .python-version file
        python_version_file = project_dir / ".python-version"
        if python_version_file.exists():
            try:
                with open(python_version_file, 'r') as f:
                    version = f.read().strip()
                    if version:
                        return version
            except Exception as e:
                self._logger.error(f"Error reading .python-version: {str(e)}")
        
        # Default to 3.10 if no specific version found
        return "3.10"
    
    async def _detect_node_version(self, project_dir: Path) -> str:
        """
        Detect Node.js version used in a project.
        
        Args:
            project_dir: Path to the project directory
            
        Returns:
            Node.js version string
        """
        # Check package.json for engines field
        package_json_path = project_dir / "package.json"
        if package_json_path.exists():
            try:
                with open(package_json_path, 'r') as f:
                    data = json.load(f)
                    if "engines" in data and "node" in data["engines"]:
                        # Extract a simple version number from the requirement
                        version_req = data["engines"]["node"]
                        version_match = re.search(r'(\d+\.\d+)', version_req)
                        if version_match:
                            return version_match.group(1)
            except Exception as e:
                self._logger.error(f"Error reading package.json: {str(e)}")
        
        # Check .nvmrc file
        nvmrc_file = project_dir / ".nvmrc"
        if nvmrc_file.exists():
            try:
                with open(nvmrc_file, 'r') as f:
                    version = f.read().strip()
                    if version:
                        # Clean up version string
                        version = version.lstrip('v')
                        version_match = re.search(r'(\d+\.\d+)', version)
                        if version_match:
                            return version_match.group(1)
            except Exception as e:
                self._logger.error(f"Error reading .nvmrc: {str(e)}")
        
        # Default to 18 if no specific version found
        return "18"
    
    async def _detect_go_version(self, project_dir: Path) -> str:
        """
        Detect Go version used in a project.
        
        Args:
            project_dir: Path to the project directory
            
        Returns:
            Go version string
        """
        # Check go.mod file
        go_mod_path = project_dir / "go.mod"
        if go_mod_path.exists():
            try:
                with open(go_mod_path, 'r') as f:
                    content = f.read()
                    # Look for go directive
                    go_match = re.search(r'go\s+(\d+\.\d+)', content)
                    if go_match:
                        return go_match.group(1)
            except Exception as e:
                self._logger.error(f"Error reading go.mod: {str(e)}")
        
        # Default to 1.19 if no specific version found
        return "1.19"
    
    async def _detect_java_version(self, project_dir: Path) -> Dict[str, str]:
        """
        Detect Java version and build tool used in a project.
        
        Args:
            project_dir: Path to the project directory
            
        Returns:
            Dictionary with java_version and build tool info
        """
        result = {
            "java_version": "17",  # Default
            "maven_version": "3.8"  # Default
        }
        
        # Check for Maven pom.xml
        pom_path = project_dir / "pom.xml"
        if pom_path.exists():
            result["build_tool"] = "maven"
            try:
                with open(pom_path, 'r') as f:
                    content = f.read()
                    # Look for Java version
                    java_match = re.search(r'<java.version>(\d+)</java.version>', content)
                    if java_match:
                        result["java_version"] = java_match.group(1)
                    
                    # Look for Maven compiler source
                    compiler_match = re.search(r'<maven.compiler.source>(\d+)</maven.compiler.source>', content)
                    if compiler_match:
                        result["java_version"] = compiler_match.group(1)
                    
                    # Try to find jar file name
                    artifact_match = re.search(r'<artifactId>([^<]+)</artifactId>', content)
                    if artifact_match:
                        result["jar_file"] = f"{artifact_match.group(1)}.jar"
            except Exception as e:
                self._logger.error(f"Error reading pom.xml: {str(e)}")
        
        # Check for Gradle build file
        gradle_path = project_dir / "build.gradle"
        if gradle_path.exists():
            result["build_tool"] = "gradle"
            try:
                with open(gradle_path, 'r') as f:
                    content = f.read()
                    # Look for Java version
                    java_match = re.search(r'sourceCompatibility\s*=\s*[\'"](\d+)[\'"]', content)
                    if java_match:
                        result["java_version"] = java_match.group(1)
            except Exception as e:
                self._logger.error(f"Error reading build.gradle: {str(e)}")
        
        return result
    
    async def _detect_ruby_version(self, project_dir: Path) -> str:
        """
        Detect Ruby version used in a project.
        
        Args:
            project_dir: Path to the project directory
            
        Returns:
            Ruby version string
        """
        # Check .ruby-version file
        ruby_version_file = project_dir / ".ruby-version"
        if ruby_version_file.exists():
            try:
                with open(ruby_version_file, 'r') as f:
                    version = f.read().strip()
                    if version:
                        return version
            except Exception as e:
                self._logger.error(f"Error reading .ruby-version: {str(e)}")
        
        # Check Gemfile
        gemfile_path = project_dir / "Gemfile"
        if gemfile_path.exists():
            try:
                with open(gemfile_path, 'r') as f:
                    content = f.read()
                    # Look for ruby directive
                    ruby_match = re.search(r'ruby\s+[\'"](\d+\.\d+\.\d+)[\'"]', content)
                    if ruby_match:
                        return ruby_match.group(1)
            except Exception as e:
                self._logger.error(f"Error reading Gemfile: {str(e)}")
        
        # Default to 3.1 if no specific version found
        return "3.1"
    
    async def detect_services(self, project_directory: Union[str, Path]) -> Dict[str, Any]:
        """
        Detect potential services in a project.
        
        Args:
            project_directory: Path to the project directory
            
        Returns:
            Dictionary with detected services
        """
        self._logger.info(f"Detecting services in project: {project_directory}")
        
        project_dir = Path(project_directory)
        if not project_dir.exists() or not project_dir.is_dir():
            return {
                "success": False,
                "error": f"Project directory does not exist or is not a directory: {project_directory}"
            }
        
        # Get project type
        project_type_info = await self.detect_project_type(project_dir)
        if not project_type_info["success"]:
            return project_type_info
        
        primary_type = project_type_info["primary_type"]
        version_info = project_type_info["version_info"]
        
        # Detect entry points based on project type
        entry_points = await self._detect_entry_points(project_dir, primary_type)
        
        # Detect ports used by the application
        ports = await self._detect_ports(project_dir, primary_type)
        
        # Detect dependencies that might indicate additional services
        dependencies = await self._detect_dependencies(project_dir, primary_type)
        
        # Detect databases
        databases = await self._detect_databases(project_dir, primary_type, dependencies)
        
        # Build services map
        services = {}
        
        # Main service for the project
        services["app"] = {
            "type": primary_type,
            "entry_point": entry_points.get("main"),
            "ports": ports.get("app", []),
            "build": {
                "context": ".",
                "dockerfile": "Dockerfile"
            }
        }
        
        # Add additional services based on dependencies
        for db_name, db_info in databases.items():
            services[db_name] = {
                "type": "database",
                "image": db_info["image"],
                "ports": db_info["ports"],
                "volumes": db_info["volumes"],
                "environment": db_info["environment"]
            }
        
        # Detect other services based on dockerfiles or compose files
        for docker_dir in project_dir.glob("**/[Dd]ocker"):
            if docker_dir.is_dir():
                for service_dir in docker_dir.glob("*"):
                    if service_dir.is_dir() and service_dir.name not in services:
                        dockerfile = service_dir / "Dockerfile"
                        if dockerfile.exists():
                            services[service_dir.name] = {
                                "type": "custom",
                                "build": {
                                    "context": str(service_dir.relative_to(project_dir)),
                                    "dockerfile": "Dockerfile"
                                }
                            }
        
        return {
            "success": True,
            "primary_type": primary_type,
            "version_info": version_info,
            "entry_points": entry_points,
            "ports": ports,
            "dependencies": dependencies,
            "databases": databases,
            "services": services
        }
    
    async def _detect_entry_points(
        self, 
        project_dir: Path, 
        project_type: str
    ) -> Dict[str, str]:
        """
        Detect entry points for a project.
        
        Args:
            project_dir: Path to the project directory
            project_type: Type of the project
            
        Returns:
            Dictionary with entry points
        """
        entry_points = {"main": None}
        
        if project_type == "python":
            # Check for common Python entry points
            candidates = [
                "app.py", "main.py", "run.py", "server.py", "api.py",
                "src/app.py", "src/main.py", "src/server.py"
            ]
            
            for candidate in candidates:
                candidate_path = project_dir / candidate
                if candidate_path.exists():
                    entry_points["main"] = candidate
                    break
            
            # Check for Flask or Django apps
            if (project_dir / "wsgi.py").exists():
                entry_points["main"] = "wsgi.py"
            elif (project_dir / "manage.py").exists():
                entry_points["main"] = "manage.py"
        
        elif project_type == "node":
            # Check package.json for main or scripts.start
            package_json_path = project_dir / "package.json"
            if package_json_path.exists():
                try:
                    with open(package_json_path, 'r') as f:
                        data = json.load(f)
                        if "main" in data:
                            entry_points["main"] = data["main"]
                        elif "scripts" in data and "start" in data["scripts"]:
                            # Use the start script
                            entry_points["main"] = "npm start"
                except Exception as e:
                    self._logger.error(f"Error reading package.json: {str(e)}")
            
            # Check common Node.js entry points
            if not entry_points["main"]:
                candidates = [
                    "index.js", "server.js", "app.js", "main.js",
                    "src/index.js", "src/server.js", "src/app.js"
                ]
                
                for candidate in candidates:
                    candidate_path = project_dir / candidate
                    if candidate_path.exists():
                        entry_points["main"] = candidate
                        break
        
        elif project_type == "golang":
            # Check for main.go
            candidates = [
                "main.go", "cmd/main.go", "cmd/app/main.go", "cmd/server/main.go"
            ]
            
            for candidate in candidates:
                candidate_path = project_dir / candidate
                if candidate_path.exists():
                    entry_points["main"] = candidate
                    break
        
        elif project_type == "ruby":
            # Check for common Ruby entry points
            candidates = [
                "app.rb", "main.rb", "server.rb", "config.ru"
            ]
            
            for candidate in candidates:
                candidate_path = project_dir / candidate
                if candidate_path.exists():
                    entry_points["main"] = candidate
                    break
        
        # If no entry point found, use a reasonable default
        if not entry_points["main"]:
            if project_type == "python":
                entry_points["main"] = "app.py"
            elif project_type == "node":
                entry_points["main"] = "index.js"
            elif project_type == "golang":
                entry_points["main"] = "main.go"
            elif project_type == "java":
                entry_points["main"] = "src/main/java/Main.java"
            elif project_type == "ruby":
                entry_points["main"] = "app.rb"
        
        return entry_points
    
    async def _detect_ports(
        self, 
        project_dir: Path, 
        project_type: str
    ) -> Dict[str, List[int]]:
        """
        Detect ports used by the application.
        
        Args:
            project_dir: Path to the project directory
            project_type: Type of the project
            
        Returns:
            Dictionary with ports information
        """
        ports = {
            "app": []
        }
        
        # Common default ports
        default_ports = {
            "http": 8080,
            "https": 8443,
            "django": 8000,
            "flask": 5000,
            "express": 3000,
            "react": 3000,
            "vue": 8080,
            "angular": 4200,
            "mongodb": 27017,
            "mysql": 3306,
            "postgresql": 5432,
            "redis": 6379
        }
        
        # Add default port based on project type
        if project_type == "python":
            # Look for common Python web frameworks
            try:
                # Read requirements.txt to check dependencies
                req_file = project_dir / "requirements.txt"
                if req_file.exists():
                    with open(req_file, 'r') as f:
                        requirements = f.read()
                        if "django" in requirements.lower():
                            ports["app"].append(default_ports["django"])
                        elif "flask" in requirements.lower():
                            ports["app"].append(default_ports["flask"])
                        elif "fastapi" in requirements.lower():
                            ports["app"].append(default_ports["http"])
            except Exception as e:
                self._logger.error(f"Error analyzing requirements: {str(e)}")
        
        elif project_type == "node":
            # Default to Express port
            ports["app"].append(default_ports["express"])
            
            # Check package.json for dependencies
            package_json_path = project_dir / "package.json"
            if package_json_path.exists():
                try:
                    with open(package_json_path, 'r') as f:
                        data = json.load(f)
                        dependencies = data.get("dependencies", {})
                        
                        if "react" in dependencies:
                            if "express" not in dependencies:
                                ports["app"] = [default_ports["react"]]
                        elif "vue" in dependencies:
                            ports["app"] = [default_ports["vue"]]
                        elif "angular" in dependencies:
                            ports["app"] = [default_ports["angular"]]
                except Exception as e:
                    self._logger.error(f"Error reading package.json: {str(e)}")
        
        # Look for port references in code files
        detected_ports = await self._scan_for_ports(project_dir)
        if detected_ports:
            # Add detected ports to app ports
            for port in detected_ports:
                if port not in ports["app"]:
                    ports["app"].append(port)
        
        # If no ports detected, use a sensible default
        if not ports["app"]:
            ports["app"].append(default_ports["http"])
        
        return ports
    
    async def _scan_for_ports(self, project_dir: Path) -> List[int]:
        """
        Scan project files for port specifications.
        
        Args:
            project_dir: Path to the project directory
            
        Returns:
            List of detected ports
        """
        detected_ports = set()
        
        # Pattern for common port assignments
        port_patterns = [
            r'(?:PORT|port)\s*=\s*(\d+)',
            r'\.listen\(\s*(\d+)',
            r'port\s*:\s*(\d+)',
            r'port=(\d+)',
            r'"port":\s*(\d+)',
            r"'port':\s*(\d+)",
            r'EXPOSE\s+(\d+)'
        ]
        
        # Limit scanning to common config and source files to avoid binary files
        # and reduce processing time
        file_patterns = [
            "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.go", "*.rb", "*.java",
            "*.yml", "*.yaml", "*.json", "*.env", "*.toml", "*.ini", "Dockerfile"
        ]
        
        for pattern in file_patterns:
            for file_path in project_dir.glob(f"**/{pattern}"):
                if file_path.is_file() and file_path.stat().st_size < 1000000:  # Skip large files
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for port_pattern in port_patterns:
                                matches = re.findall(port_pattern, content)
                                for match in matches:
                                    try:
                                        port = int(match)
                                        if 1 <= port <= 65535:  # Valid port range
                                            detected_ports.add(port)
                                    except ValueError:
                                        pass
                    except Exception as e:
                        # Skip files with encoding or access issues
                        pass
        
        return list(sorted(detected_ports))
    
    async def _detect_dependencies(
        self, 
        project_dir: Path, 
        project_type: str
    ) -> Dict[str, List[str]]:
        """
        Detect dependencies for a project.
        
        Args:
            project_dir: Path to the project directory
            project_type: Type of the project
            
        Returns:
            Dictionary with dependencies
        """
        dependencies = {
            "databases": [],
            "messaging": [],
            "cache": []
        }
        
        # Database keywords to look for
        database_keywords = {
            "mongodb": ["mongodb", "mongoose", "pymongo"],
            "mysql": ["mysql", "sequelize", "mysql-connector"],
            "postgresql": ["postgresql", "postgres", "pg", "psycopg2", "sqlalchemy"],
            "sqlite": ["sqlite", "sqlite3"],
            "redis": ["redis"],
            "elasticsearch": ["elasticsearch", "elastic"],
            "cassandra": ["cassandra"]
        }
        
        # Messaging systems
        messaging_keywords = {
            "rabbitmq": ["rabbitmq", "amqp"],
            "kafka": ["kafka"],
            "activemq": ["activemq"],
            "sqs": ["sqs", "aws-sdk"]
        }
        
        # Cache systems
        cache_keywords = {
            "redis": ["redis"],
            "memcached": ["memcached", "memcache"]
        }
        
        if project_type == "python":
            # Check requirements.txt
            req_file = project_dir / "requirements.txt"
            if req_file.exists():
                try:
                    with open(req_file, 'r') as f:
                        requirements = f.read().lower()
                        
                        # Check for database dependencies
                        for db, keywords in database_keywords.items():
                            if any(keyword in requirements for keyword in keywords):
                                dependencies["databases"].append(db)
                        
                        # Check for messaging dependencies
                        for msg, keywords in messaging_keywords.items():
                            if any(keyword in requirements for keyword in keywords):
                                dependencies["messaging"].append(msg)
                        
                        # Check for cache dependencies
                        for cache, keywords in cache_keywords.items():
                            if any(keyword in requirements for keyword in keywords):
                                dependencies["cache"].append(cache)
                except Exception as e:
                    self._logger.error(f"Error analyzing requirements: {str(e)}")
        
        elif project_type == "node":
            # Check package.json
            package_json_path = project_dir / "package.json"
            if package_json_path.exists():
                try:
                    with open(package_json_path, 'r') as f:
                        data = json.load(f)
                        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                        deps_str = " ".join(deps.keys()).lower()
                        
                        # Check for database dependencies
                        for db, keywords in database_keywords.items():
                            if any(keyword in deps_str for keyword in keywords):
                                dependencies["databases"].append(db)
                        
                        # Check for messaging dependencies
                        for msg, keywords in messaging_keywords.items():
                            if any(keyword in deps_str for keyword in keywords):
                                dependencies["messaging"].append(msg)
                        
                        # Check for cache dependencies
                        for cache, keywords in cache_keywords.items():
                            if any(keyword in deps_str for keyword in keywords):
                                dependencies["cache"].append(cache)
                except Exception as e:
                    self._logger.error(f"Error reading package.json: {str(e)}")
        
        # Remove duplicates (e.g. redis can be both database and cache)
        for category in dependencies:
            dependencies[category] = list(set(dependencies[category]))
        
        return dependencies
    
    async def _detect_databases(
        self, 
        project_dir: Path, 
        project_type: str,
        dependencies: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect databases used by the project.
        
        Args:
            project_dir: Path to the project directory
            project_type: Type of the project
            dependencies: Detected dependencies
            
        Returns:
            Dictionary with database configurations
        """
        databases = {}
        
        # Map database names to configurations
        db_configs = {
            "mongodb": {
                "image": "mongo:6",
                "ports": ["27017:27017"],
                "volumes": ["mongodb_data:/data/db"],
                "environment": {
                    "MONGO_INITDB_ROOT_USERNAME": "root",
                    "MONGO_INITDB_ROOT_PASSWORD": "example"
                }
            },
            "mysql": {
                "image": "mysql:8",
                "ports": ["3306:3306"],
                "volumes": ["mysql_data:/var/lib/mysql"],
                "environment": {
                    "MYSQL_ROOT_PASSWORD": "example",
                    "MYSQL_DATABASE": "app"
                }
            },
            "postgresql": {
                "image": "postgres:14",
                "ports": ["5432:5432"],
                "volumes": ["postgres_data:/var/lib/postgresql/data"],
                "environment": {
                    "POSTGRES_PASSWORD": "example",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_DB": "app"
                }
            },
            "redis": {
                "image": "redis:7",
                "ports": ["6379:6379"],
                "volumes": ["redis_data:/data"],
                "command": "redis-server --appendonly yes"
            },
            "elasticsearch": {
                "image": "elasticsearch:8.6.0",
                "ports": ["9200:9200", "9300:9300"],
                "volumes": ["elasticsearch_data:/usr/share/elasticsearch/data"],
                "environment": {
                    "discovery.type": "single-node",
                    "ES_JAVA_OPTS": "-Xms512m -Xmx512m"
                }
            }
        }
        
        # Add detected databases
        for db in dependencies.get("databases", []):
            if db in db_configs:
                databases[db] = db_configs[db]
        
        # Add Redis if it's used as a cache
        if "redis" in dependencies.get("cache", []) and "redis" not in databases:
            databases["redis"] = db_configs["redis"]
        
        return databases
    
    async def generate_dockerfile(
        self,
        project_directory: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a Dockerfile for a project.
        
        Args:
            project_directory: Path to the project directory
            output_file: Path to output Dockerfile (default: <project_directory>/Dockerfile)
            overwrite: Whether to overwrite existing Dockerfile
            
        Returns:
            Dictionary with result information
        """
        self._logger.info(f"Generating Dockerfile for project: {project_directory}")
        
        project_dir = Path(project_directory)
        if not project_dir.exists() or not project_dir.is_dir():
            return {
                "success": False,
                "error": f"Project directory does not exist or is not a directory: {project_directory}"
            }
        
        # Determine output file
        if output_file is None:
            output_file = project_dir / "Dockerfile"
        else:
            output_file = Path(output_file)
        
        # Check if file already exists
        if output_file.exists() and not overwrite:
            return {
                "success": False,
                "error": f"Dockerfile already exists at {output_file}. Use overwrite=True to replace it."
            }
        
        # Detect project type
        project_info = await self.detect_project_type(project_dir)
        if not project_info["success"]:
            return project_info
        
        project_type = project_info["primary_type"]
        version_info = project_info["version_info"]
        
        # Detect entry points
        entry_points = await self._detect_entry_points(project_dir, project_type)
        
        # Detect ports
        ports_info = await self._detect_ports(project_dir, project_type)
        app_ports = ports_info.get("app", [8080])  # Default to 8080 if no ports detected
        
        # Generate Dockerfile content based on project type
        dockerfile_content = ""
        
        if project_type == "python":
            # Get Python version
            python_version = version_info.get("python_version", "3.10")
            
            # Format EXPOSE statement
            expose_port = ""
            if app_ports:
                expose_port = f"EXPOSE {app_ports[0]}"
            
            # Get entry point file
            entry_point = entry_points.get("main", "app.py")
            
            # Generate Dockerfile
            dockerfile_content = DOCKERFILE_TEMPLATES["python"].format(
                python_version=python_version,
                entry_point=entry_point,
                expose_port=expose_port
            )
        
        elif project_type == "node":
            # Get Node.js version
            node_version = version_info.get("node_version", "18")
            
            # Format EXPOSE statement
            expose_port = ""
            if app_ports:
                expose_port = f"EXPOSE {app_ports[0]}"
            
            # Check for package lock file
            package_lock = ""
            if (project_dir / "package-lock.json").exists():
                package_lock = "package-lock.json"
            elif (project_dir / "yarn.lock").exists():
                package_lock = "yarn.lock"
            
            # Determine if it's a production build
            production_flag = "--production"
            
            # Generate Dockerfile
            dockerfile_content = DOCKERFILE_TEMPLATES["node"].format(
                node_version=node_version,
                package_lock=package_lock,
                expose_port=expose_port,
                production_flag=production_flag
            )
        
        elif project_type == "golang":
            # Get Go version
            go_version = version_info.get("go_version", "1.19")
            
            # Format EXPOSE statement
            expose_port = ""
            if app_ports:
                expose_port = f"EXPOSE {app_ports[0]}"
            
            # Get main file
            main_file = entry_points.get("main", "main.go")
            
            # Generate Dockerfile
            dockerfile_content = DOCKERFILE_TEMPLATES["golang"].format(
                go_version=go_version,
                main_file=main_file,
                expose_port=expose_port
            )
        
        elif project_type == "java":
            # Get Java version
            java_version = version_info.get("java_version", "17")
            maven_version = version_info.get("maven_version", "3.8")
            jar_file = version_info.get("jar_file", "app.jar")
            
            # Format EXPOSE statement
            expose_port = ""
            if app_ports:
                expose_port = f"EXPOSE {app_ports[0]}"
            
            # Generate Dockerfile
            dockerfile_content = DOCKERFILE_TEMPLATES["java"].format(
                java_version=java_version,
                maven_version=maven_version,
                jar_file=jar_file,
                expose_port=expose_port
            )
        
        elif project_type == "ruby":
            # Get Ruby version
            ruby_version = version_info.get("ruby_version", "3.1")
            
            # Format EXPOSE statement
            expose_port = ""
            if app_ports:
                expose_port = f"EXPOSE {app_ports[0]}"
            
            # Get entry point file
            entry_point = entry_points.get("main", "app.rb")
            
            # Generate Dockerfile
            dockerfile_content = DOCKERFILE_TEMPLATES["ruby"].format(
                ruby_version=ruby_version,
                entry_point=entry_point,
                expose_port=expose_port
            )
        
        else:
            return {
                "success": False,
                "error": f"Unsupported project type: {project_type}",
                "suggestion": "Try specifying a different project type or creating a custom Dockerfile."
            }
        
        # Write Dockerfile
        try:
            with open(output_file, 'w') as f:
                f.write(dockerfile_content)
            
            return {
                "success": True,
                "message": f"Dockerfile generated successfully at {output_file}",
                "dockerfile_path": str(output_file),
                "project_type": project_type,
                "entry_point": entry_points.get("main"),
                "ports": app_ports,
                "content": dockerfile_content
            }
        except Exception as e:
            self._logger.exception(f"Error writing Dockerfile: {str(e)}")
            return {
                "success": False,
                "error": f"Error writing Dockerfile: {str(e)}"
            }
    
    async def generate_docker_compose(
        self,
        project_directory: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
        include_databases: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a docker-compose.yml file for a project.
        
        Args:
            project_directory: Path to the project directory
            output_file: Path to output file (default: <project_directory>/docker-compose.yml)
            overwrite: Whether to overwrite existing file
            include_databases: Whether to include detected database services
            
        Returns:
            Dictionary with result information
        """
        self._logger.info(f"Generating docker-compose.yml for project: {project_directory}")
        
        project_dir = Path(project_directory)
        if not project_dir.exists() or not project_dir.is_dir():
            return {
                "success": False,
                "error": f"Project directory does not exist or is not a directory: {project_directory}"
            }
        
        # Determine output file
        if output_file is None:
            output_file = project_dir / "docker-compose.yml"
        else:
            output_file = Path(output_file)
        
        # Check if file already exists
        if output_file.exists() and not overwrite:
            return {
                "success": False,
                "error": f"docker-compose.yml already exists at {output_file}. Use overwrite=True to replace it."
            }
        
        # Detect services
        services_info = await self.detect_services(project_dir)
        if not services_info["success"]:
            return services_info
        
        detected_services_map = services_info["services"] # Renamed to avoid conflict
        
        # Generate docker-compose.yml content
        compose_services_dict: Dict[str, Any] = {} # Use a dictionary to build services
        compose_networks_dict: Dict[str, Any] = {"app-network": {"driver": "bridge"}}
        compose_volumes_dict: Dict[str, Any] = {}
        
        # Check if Dockerfile exists for the main app
        app_dockerfile_exists = (project_dir / "Dockerfile").exists()
        
        # App service
        app_service_config = detected_services_map.get("app", {})
        app_service_name = "app" # Default app service name
        
        if app_service_config:
            app_entry: Dict[str, Any] = {}
            if app_dockerfile_exists:
                app_entry["build"] = {
                    "context": ".",
                    "dockerfile": "Dockerfile"
                }
                # If building, image name is usually not set here, or set to what it will be tagged as
            elif app_service_config.get("image"): # If no Dockerfile, but image specified
                app_entry["image"] = app_service_config["image"]

            if not app_entry.get("build") and not app_entry.get("image"):
                self._logger.warning("App service has neither Dockerfile nor explicit image. Skipping app service in compose.")
            else:
                app_ports_list = app_service_config.get("ports", [8080] if app_dockerfile_exists else [])
                if app_ports_list:
                    app_entry["ports"] = [f"{p}:{p}" for p in app_ports_list]
                
                app_entry["networks"] = ["app-network"]
                # Add other app_service_config like environment, volumes if defined
                if app_service_config.get("environment"):
                    app_entry["environment"] = app_service_config.get("environment")
                if app_service_config.get("volumes"):
                    app_entry["volumes"] = app_service_config.get("volumes")
                
                compose_services_dict[app_service_name] = app_entry

        # Generate database services
        depends_on_list_for_app = []
        if include_databases:
            databases = services_info.get("databases", {})
            for db_name, db_info in databases.items():
                db_entry: Dict[str, Any] = {"image": db_info["image"]}
                
                if db_info.get("ports"):
                    db_entry["ports"] = db_info["ports"] # Assuming they are already in "HOST:CONTAINER" format
                
                db_volume_definitions = db_info.get("volumes", [])
                if db_volume_definitions:
                    db_entry["volumes"] = db_volume_definitions
                    for vol_def in db_volume_definitions:
                        # Extract volume name if it's a named volume definition like "mydata:/data/db"
                        vol_name_match = re.match(r"([^:]+):", vol_def)
                        if vol_name_match:
                            compose_volumes_dict[vol_name_match.group(1)] = {} # Empty definition for named volume

                if db_info.get("environment"):
                    db_entry["environment"] = db_info["environment"]
                
                if db_info.get("command"): # For Redis example
                    db_entry["command"] = db_info["command"]

                db_entry["networks"] = ["app-network"]
                compose_services_dict[db_name] = db_entry
                depends_on_list_for_app.append(db_name)
        
        # Update app service with depends_on if needed
        if app_service_name in compose_services_dict and depends_on_list_for_app:
            compose_services_dict[app_service_name]["depends_on"] = depends_on_list_for_app
        
        # Final compose structure
        final_compose_structure: Dict[str, Any] = {"version": '3.8'} # Use a common recent version
        if compose_services_dict:
            final_compose_structure["services"] = compose_services_dict
        if compose_networks_dict:
            final_compose_structure["networks"] = compose_networks_dict
        if compose_volumes_dict:
            final_compose_structure["volumes"] = compose_volumes_dict
        
        # Write docker-compose.yml
        try:
            with open(output_file, 'w') as f:
                yaml.dump(final_compose_structure, f, sort_keys=False, default_flow_style=False)
            
            return {
                "success": True,
                "message": f"docker-compose.yml generated successfully at {output_file}",
                "compose_file_path": str(output_file),
                "services_included": list(compose_services_dict.keys()),
                "content": yaml.dump(final_compose_structure, sort_keys=False, default_flow_style=False)
            }
        except Exception as e:
            self._logger.exception(f"Error writing docker-compose.yml: {str(e)}")
            return {
                "success": False,
                "error": f"Error writing docker-compose.yml: {str(e)}"
            }

    async def generate_dockerignore(
        self,
        project_directory: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a .dockerignore file for a project.
        
        Args:
            project_directory: Path to the project directory
            output_file: Path to output file (default: <project_directory>/.dockerignore)
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with result information
        """
        self._logger.info(f"Generating .dockerignore for project: {project_directory}")
        
        project_dir = Path(project_directory)
        if not project_dir.exists() or not project_dir.is_dir():
            return {
                "success": False,
                "error": f"Project directory does not exist or is not a directory: {project_directory}"
            }
        
        # Determine output file
        if output_file is None:
            output_file = project_dir / ".dockerignore"
        else:
            output_file = Path(output_file)
        
        # Check if file already exists
        if output_file.exists() and not overwrite:
            return {
                "success": False,
                "error": f".dockerignore already exists at {output_file}. Use overwrite=True to replace it."
            }
        
        # Detect project type
        project_info = await self.detect_project_type(project_dir)
        project_type = project_info["primary_type"]
        
        # Common files to ignore
        common_ignores = [
            "**/.git",
            "**/.gitignore",
            "**/.vscode",
            "**/.idea",
            "**/__pycache__",
            "**/node_modules",
            "**/dist",
            "**/build",
            "**/.env",
            "**/.DS_Store",
            "**/*.log",
            "**/*.swp",
            "**/*.swo",
            "Dockerfile",
            "docker-compose.yml",
            "README.md",
            ".dockerignore"
        ]
        
        # Type-specific ignores
        type_specific_ignores = {
            "python": [
                "**/*.pyc",
                "**/*.pyo",
                "**/*.pyd",
                "**/.Python",
                "**/env/",
                "**/venv/",
                "**/.venv/",
                "**/.pytest_cache/",
                "**/.coverage",
                "**/htmlcov/",
                "**/pytestdebug.log"
            ],
            "node": [
                "**/npm-debug.log",
                "**/yarn-debug.log",
                "**/yarn-error.log",
                "**/.pnpm-debug.log",
                "**/coverage/",
                "**/.next/",
                "**/out/",
                "**/docs/",
                "**/.eslintcache"
            ],
            "golang": [
                "**/vendor/",
                "**/*.test",
                "**/coverage.txt",
                "**/coverage.html"
            ],
            "java": [
                "**/target/",
                "**/.gradle/",
                "**/gradle-app.setting",
                "**/.gradletasknamecache",
                "**/bin/",
                "**/out/",
                "**/*.class",
                "**/*.jar"
            ],
            "ruby": [
                "**/.bundle/",
                "**/vendor/bundle",
                "**/lib/bundler/man/",
                "**/.rubocop-*",
                "**/*.gem",
                "**/coverage/"
            ]
        }
        
        # Combine common and type-specific ignores
        ignores = common_ignores.copy()
        if project_type in type_specific_ignores:
            ignores.extend(type_specific_ignores[project_type])
        
        # Sort and remove duplicates
        ignores = sorted(set(ignores))
        
        # Generate .dockerignore content
        content = "\n".join(ignores) + "\n"
        
        # Write .dockerignore
        try:
            with open(output_file, 'w') as f:
                f.write(content)
            
            return {
                "success": True,
                "message": f".dockerignore generated successfully at {output_file}",
                "path": str(output_file),
                "content": content
            }
        except Exception as e:
            self._logger.exception(f"Error writing .dockerignore: {str(e)}")
            return {
                "success": False,
                "error": f"Error writing .dockerignore: {str(e)}"
            }

    async def setup_docker_project(
        self,
        project_directory: Union[str, Path],
        generate_dockerfile: bool = True,
        generate_compose: bool = True,
        generate_dockerignore: bool = True,
        overwrite: bool = False,
        include_databases: bool = True,
        build_image: bool = False
    ) -> Dict[str, Any]:
        """
        Set up a complete Docker environment for a project.
        
        Args:
            project_directory: Path to the project directory
            generate_dockerfile: Whether to generate a Dockerfile
            generate_compose: Whether to generate a docker-compose.yml
            generate_dockerignore: Whether to generate a .dockerignore
            overwrite: Whether to overwrite existing files
            include_databases: Whether to include detected database services
            build_image: Whether to build the Docker image after setup
            
        Returns:
            Dictionary with setup results
        """
        self._logger.info(f"Setting up Docker environment for project: {project_directory}")
        
        project_dir = Path(project_directory)
        if not project_dir.exists() or not project_dir.is_dir():
            return {
                "success": False,
                "error": f"Project directory does not exist or is not a directory: {project_directory}"
            }
        
        results = {
            "success": True,
            "project_directory": str(project_dir),
            "files_generated": []
        }
        
        # Generate Dockerfile if requested
        if generate_dockerfile:
            dockerfile_result = await self.generate_dockerfile(
                project_dir,
                overwrite=overwrite
            )
            results["dockerfile"] = dockerfile_result
            
            if dockerfile_result["success"]:
                results["files_generated"].append(dockerfile_result["dockerfile_path"])
            else:
                # Non-fatal error if file exists and overwrite is False
                if "already exists" in dockerfile_result.get("error", ""):
                    results["dockerfile"]["skipped"] = True
                else:
                    # Fatal error for other issues
                    results["success"] = False
        
        # Generate docker-compose.yml if requested
        if generate_compose:
            compose_result = await self.generate_docker_compose(
                project_dir,
                overwrite=overwrite,
                include_databases=include_databases
            )
            results["docker_compose"] = compose_result
            
            if compose_result["success"]:
                results["files_generated"].append(compose_result["compose_file_path"])
            else:
                # Non-fatal error if file exists and overwrite is False
                if "already exists" in compose_result.get("error", ""):
                    results["docker_compose"]["skipped"] = True
                else:
                    # Fatal error for other issues
                    results["success"] = False
        
        # Generate .dockerignore if requested
        if generate_dockerignore:
            dockerignore_result = await self.generate_dockerignore(
                project_dir,
                overwrite=overwrite
            )
            results["dockerignore"] = dockerignore_result
            
            if dockerignore_result["success"]:
                results["files_generated"].append(dockerignore_result["path"])
            else:
                # Non-fatal error if file exists and overwrite is False
                if "already exists" in dockerignore_result.get("error", ""):
                    results["dockerignore"]["skipped"] = True
                else:
                    # Fatal error for other issues
                    results["success"] = False
        
        # Build Docker image if requested and Dockerfile was generated
        if build_image and results["success"] and results.get("dockerfile", {}).get("success", False):
            build_result = await self.build_image(
                context_path=project_dir,
                tag="app:latest"
            )
            results["build_image"] = build_result
            
            if not build_result["success"]:
                # Non-fatal error
                results["build_warnings"] = build_result.get("error", "Unknown build error")
        
        return results

# Global Docker integration instance
docker_integration = DockerIntegration()
