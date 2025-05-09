# angela/cli/docker.py
"""
CLI commands for Docker integration in Angela CLI.

This module provides CLI commands for interacting with Docker and Docker Compose
through Angela CLI. It allows users to manage containers, images, and Docker-related
files from the command line.
"""
import asyncio
import os
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from angela.toolchain.docker import docker_integration
from angela.context import context_manager
from angela.utils.logging import get_logger
from angela.execution.engine import execution_engine

logger = get_logger(__name__)
console = Console()

# Create the Typer app for Docker commands
app = typer.Typer(help="Docker and Docker Compose commands")


@app.command("status")
async def docker_status():
    """Show Docker and Docker Compose availability status."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Checking Docker status...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Checking", total=1)
        
        # Check Docker availability
        docker_available = await docker_integration.is_docker_available()
        
        # Check Docker Compose availability
        compose_available = await docker_integration.is_docker_compose_available()
        
        progress.update(task, completed=1)
    
    # Display status
    table = Table(title="Docker Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row(
        "Docker",
        "[green]Available[/green]" if docker_available else "[red]Not Available[/red]"
    )
    table.add_row(
        "Docker Compose",
        "[green]Available[/green]" if compose_available else "[red]Not Available[/red]"
    )
    
    console.print(table)
    
    if not docker_available:
        console.print("[yellow]Docker is not available. Install Docker to use these features.[/yellow]")
    elif not compose_available:
        console.print("[yellow]Docker Compose is not available. Install Docker Compose for multi-container support.[/yellow]")


@app.command("ps")
async def list_containers(
    all_containers: bool = typer.Option(False, "--all", "-a", help="Show all containers (including stopped)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only display container IDs")
):
    """List Docker containers."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Listing containers...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Listing", total=1)
        
        result = await docker_integration.list_containers(all_containers)
        
        progress.update(task, completed=1)
    
    if result["success"]:
        containers = result["containers"]
        
        if not containers:
            console.print("[yellow]No containers found.[/yellow]")
            return
        
        if quiet:
            for container in containers:
                if "id" in container:
                    console.print(container["id"])
        else:
            table = Table(title=f"{'All' if all_containers else 'Running'} Containers")
            
            # Determine columns based on the first container's structure
            if containers:
                first_container = containers[0]
                
                # Common columns
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Name", style="green")
                table.add_column("Image", style="blue")
                table.add_column("Status", style="yellow")
                
                # Additional columns if available
                if "ports" in first_container:
                    table.add_column("Ports", style="magenta")
                
                # Add rows
                for container in containers:
                    # Extract values (handle different formats)
                    container_id = container.get("id", container.get("ID", ""))
                    # Show short ID
                    if len(container_id) > 12:
                        container_id = container_id[:12]
                    
                    name = container.get("names", container.get("Names", "")).lstrip('/')
                    if isinstance(name, list):
                        name = ", ".join(name)
                    
                    image = container.get("image", container.get("Image", ""))
                    status = container.get("status", container.get("Status", ""))
                    
                    # Build row
                    row = [container_id, name, image, status]
                    
                    # Add ports if available
                    if "ports" in first_container:
                        ports = container.get("ports", container.get("Ports", ""))
                        if isinstance(ports, list):
                            ports = ", ".join(ports)
                        row.append(ports)
                    
                    table.add_row(*row)
            
            console.print(table)
    else:
        console.print(f"[red]Error listing containers: {result.get('error', 'Unknown error')}[/red]")


@app.command("logs")
async def show_container_logs(
    container: str = typer.Argument(..., help="Container ID or name"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    tail: Optional[int] = typer.Option(None, "--tail", "-n", help="Number of lines to show from the end"),
    timestamps: bool = typer.Option(False, "--timestamps", "-t", help="Show timestamps")
):
    """Show logs from a Docker container."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Getting logs for container {container}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Getting logs", total=1)
        
        result = await docker_integration.get_container_logs(
            container_id_or_name=container,
            tail=tail,
            follow=follow,
            timestamps=timestamps
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        logs = result.get("logs", "")
        
        if not logs.strip():
            console.print("[yellow]No logs available for this container.[/yellow]")
            return
        
        console.print(Panel(
            logs,
            title=f"Logs for container: {container}",
            expand=False,
            border_style="blue"
        ))
        
        if result.get("truncated", False):
            console.print("[yellow]Log output truncated due to size or streaming timeout.[/yellow]")
    else:
        console.print(f"[red]Error getting container logs: {result.get('error', 'Unknown error')}[/red]")


@app.command("start")
async def start_container(container: str = typer.Argument(..., help="Container ID or name")):
    """Start a Docker container."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Starting container {container}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Starting", total=1)
        
        result = await docker_integration.start_container(container)
        
        progress.update(task, completed=1)
    
    if result["success"]:
        console.print(f"[green]Container {container} started successfully.[/green]")
    else:
        console.print(f"[red]Error starting container: {result.get('error', 'Unknown error')}[/red]")


@app.command("stop")
async def stop_container(
    container: str = typer.Argument(..., help="Container ID or name"),
    timeout: int = typer.Option(10, "--timeout", "-t", help="Timeout in seconds before killing the container")
):
    """Stop a Docker container."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Stopping container {container}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Stopping", total=1)
        
        result = await docker_integration.stop_container(container, timeout)
        
        progress.update(task, completed=1)
    
    if result["success"]:
        console.print(f"[green]Container {container} stopped successfully.[/green]")
    else:
        console.print(f"[red]Error stopping container: {result.get('error', 'Unknown error')}[/red]")


@app.command("restart")
async def restart_container(
    container: str = typer.Argument(..., help="Container ID or name"),
    timeout: int = typer.Option(10, "--timeout", "-t", help="Timeout in seconds before killing the container")
):
    """Restart a Docker container."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Restarting container {container}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Restarting", total=1)
        
        result = await docker_integration.restart_container(container, timeout)
        
        progress.update(task, completed=1)
    
    if result["success"]:
        console.print(f"[green]Container {container} restarted successfully.[/green]")
    else:
        console.print(f"[red]Error restarting container: {result.get('error', 'Unknown error')}[/red]")


@app.command("rm")
async def remove_container(
    container: str = typer.Argument(..., help="Container ID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal of running container"),
    volumes: bool = typer.Option(False, "--volumes", "-v", help="Remove anonymous volumes")
):
    """Remove a Docker container."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Removing container {container}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Removing", total=1)
        
        result = await docker_integration.remove_container(container, force, volumes)
        
        progress.update(task, completed=1)
    
    if result["success"]:
        console.print(f"[green]Container {container} removed successfully.[/green]")
    else:
        console.print(f"[red]Error removing container: {result.get('error', 'Unknown error')}[/red]")


@app.command("images")
async def list_images(
    all_images: bool = typer.Option(False, "--all", "-a", help="Show all images (including intermediates)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only display image IDs")
):
    """List Docker images."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Listing images...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Listing", total=1)
        
        result = await docker_integration.list_images(all_images)
        
        progress.update(task, completed=1)
    
    if result["success"]:
        images = result["images"]
        
        if not images:
            console.print("[yellow]No images found.[/yellow]")
            return
        
        if quiet:
            for image in images:
                if "id" in image:
                    console.print(image["id"])
        else:
            table = Table(title="Docker Images")
            
            # Add columns
            table.add_column("Repository", style="cyan")
            table.add_column("Tag", style="green")
            table.add_column("ID", style="blue", no_wrap=True)
            table.add_column("Created", style="yellow")
            table.add_column("Size", style="magenta")
            
            # Add rows
            for image in images:
                # Extract values (handle different formats)
                repository = image.get("repository", image.get("Repository", "<none>"))
                tag = image.get("tag", image.get("Tag", "<none>"))
                image_id = image.get("id", image.get("ID", ""))
                # Show short ID
                if len(image_id) > 12:
                    image_id = image_id[:12]
                
                created = image.get("created", image.get("Created", ""))
                size = image.get("size", image.get("Size", ""))
                
                table.add_row(repository, tag, image_id, created, size)
            
            console.print(table)
    else:
        console.print(f"[red]Error listing images: {result.get('error', 'Unknown error')}[/red]")


@app.command("rmi")
async def remove_image(
    image: str = typer.Argument(..., help="Image ID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal")
):
    """Remove a Docker image."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Removing image {image}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Removing", total=1)
        
        result = await docker_integration.remove_image(image, force)
        
        progress.update(task, completed=1)
    
    if result["success"]:
        console.print(f"[green]Image {image} removed successfully.[/green]")
    else:
        console.print(f"[red]Error removing image: {result.get('error', 'Unknown error')}[/red]")


@app.command("pull")
async def pull_image(image: str = typer.Argument(..., help="Image name to pull")):
    """Pull a Docker image."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Pulling image {image}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Pulling", total=1)
        
        result = await docker_integration.pull_image(image)
        
        progress.update(task, completed=1)
    
    if result["success"]:
        console.print(f"[green]Image {image} pulled successfully.[/green]")
    else:
        console.print(f"[red]Error pulling image: {result.get('error', 'Unknown error')}[/red]")


@app.command("build")
async def build_image(
    context_path: str = typer.Argument(".", help="Path to build context"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Tag for the built image"),
    dockerfile: Optional[str] = typer.Option(None, "--file", "-f", help="Path to Dockerfile"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Do not use cache when building")
):
    """Build a Docker image."""
    # Resolve path
    path = Path(context_path).absolute()
    if not path.exists() or not path.is_dir():
        console.print(f"[red]Error: Build context does not exist or is not a directory: {path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Building Docker image from {path}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Building", total=1)
        
        result = await docker_integration.build_image(
            context_path=path,
            tag=tag,
            dockerfile=dockerfile,
            no_cache=no_cache
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        image_id = result.get("image_id", "")
        tag_str = f" with tag {tag}" if tag else ""
        
        console.print(f"[green]Image built successfully{tag_str}.[/green]")
        if image_id:
            console.print(f"[green]Image ID: {image_id}[/green]")
    else:
        console.print(f"[red]Error building image: {result.get('error', 'Unknown error')}[/red]")


@app.command("run")
async def run_container(
    image: str = typer.Argument(..., help="Docker image to run"),
    command: Optional[str] = typer.Argument(None, help="Command to run in the container"),
    name: Optional[str] = typer.Option(None, "--name", help="Container name"),
    ports: List[str] = typer.Option([], "--port", "-p", help="Port mappings (host:container)"),
    volumes: List[str] = typer.Option([], "--volume", "-v", help="Volume mappings (host:container)"),
    environment: List[str] = typer.Option([], "--env", "-e", help="Environment variables (KEY=VALUE)"),
    detach: bool = typer.Option(True, "--detach", "-d", help="Run in background"),
    remove: bool = typer.Option(False, "--rm", help="Remove container when it exits"),
    network: Optional[str] = typer.Option(None, "--network", help="Connect to network"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode")
):
    """Run a Docker container."""
    # Parse environment variables
    env_dict = {}
    for env in environment:
        parts = env.split("=", 1)
        if len(parts) == 2:
            env_dict[parts[0]] = parts[1]
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Running container from image {image}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Running", total=1)
        
        result = await docker_integration.run_container(
            image=image,
            command=command,
            name=name,
            ports=ports,
            volumes=volumes,
            environment=env_dict,
            detach=detach,
            remove=remove,
            network=network,
            interactive=interactive
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        if detach:
            container_id = result.get("container_id", "")
            if container_id:
                console.print(f"[green]Container started in detached mode with ID: {container_id}[/green]")
            else:
                console.print(f"[green]Container started in detached mode.[/green]")
        else:
            console.print(f"[green]Container executed successfully.[/green]")
    else:
        console.print(f"[red]Error running container: {result.get('error', 'Unknown error')}[/red]")


@app.command("exec")
async def exec_in_container(
    container: str = typer.Argument(..., help="Container ID or name"),
    command: str = typer.Argument(..., help="Command to execute"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode")
):
    """Execute a command in a running container."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Executing command in container {container}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Executing", total=1)
        
        result = await docker_integration.exec_in_container(
            container_id_or_name=container,
            command=command,
            interactive=interactive
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        output = result.get("output", "")
        if output.strip():
            console.print(Panel(
                output,
                title=f"Command output from {container}",
                expand=False,
                border_style="blue"
            ))
        else:
            console.print(f"[green]Command executed successfully with no output.[/green]")
    else:
        console.print(f"[red]Error executing command: {result.get('error', 'Unknown error')}[/red]")


# Docker Compose commands

@app.command("compose-up")
async def compose_up(
    compose_file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to docker-compose.yml"),
    directory: Optional[str] = typer.Option(None, "--dir", help="Project directory (default: current directory)"),
    detach: bool = typer.Option(True, "--detach", "-d", help="Run in background"),
    build: bool = typer.Option(False, "--build", help="Build images before starting"),
    no_recreate: bool = typer.Option(False, "--no-recreate", help="Don't recreate containers"),
    force_recreate: bool = typer.Option(False, "--force-recreate", help="Force recreate containers"),
    services: List[str] = typer.Argument(None, help="Services to start (default: all)")
):
    """Start services using Docker Compose."""
    # Resolve directory
    if directory:
        dir_path = Path(directory).absolute()
    else:
        dir_path = context_manager.cwd
    
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(f"[red]Error: Project directory does not exist or is not a directory: {dir_path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Starting Docker Compose services...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Starting", total=1)
        
        result = await docker_integration.compose_up(
            compose_file=compose_file,
            project_directory=dir_path,
            detach=detach,
            build=build,
            no_recreate=no_recreate,
            force_recreate=force_recreate,
            services=services
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        console.print(f"[green]Docker Compose services started successfully.[/green]")
        console.print(f"[green]Use 'angela docker compose-ps' to check service status.[/green]")
    else:
        console.print(f"[red]Error starting Docker Compose services: {result.get('error', 'Unknown error')}[/red]")
        
        # Show command for debugging
        if "command" in result:
            console.print(f"[yellow]Command: {result['command']}[/yellow]")


@app.command("compose-down")
async def compose_down(
    compose_file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to docker-compose.yml"),
    directory: Optional[str] = typer.Option(None, "--dir", help="Project directory (default: current directory)"),
    remove_images: bool = typer.Option(False, "--rmi", help="Remove images"),
    remove_volumes: bool = typer.Option(False, "--volumes", "-v", help="Remove volumes"),
    remove_orphans: bool = typer.Option(False, "--remove-orphans", help="Remove orphaned containers")
):
    """Stop and remove Docker Compose services."""
    # Resolve directory
    if directory:
        dir_path = Path(directory).absolute()
    else:
        dir_path = context_manager.cwd
    
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(f"[red]Error: Project directory does not exist or is not a directory: {dir_path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Stopping Docker Compose services...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Stopping", total=1)
        
        result = await docker_integration.compose_down(
            compose_file=compose_file,
            project_directory=dir_path,
            remove_images=remove_images,
            remove_volumes=remove_volumes,
            remove_orphans=remove_orphans
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        console.print(f"[green]Docker Compose services stopped successfully.[/green]")
    else:
        console.print(f"[red]Error stopping Docker Compose services: {result.get('error', 'Unknown error')}[/red]")


@app.command("compose-ps")
async def compose_ps(
    compose_file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to docker-compose.yml"),
    directory: Optional[str] = typer.Option(None, "--dir", help="Project directory (default: current directory)"),
    all_services: bool = typer.Option(False, "--all", "-a", help="Show stopped services"),
    services: List[str] = typer.Argument(None, help="Services to show (default: all)")
):
    """List Docker Compose services."""
    # Resolve directory
    if directory:
        dir_path = Path(directory).absolute()
    else:
        dir_path = context_manager.cwd
    
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(f"[red]Error: Project directory does not exist or is not a directory: {dir_path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Listing Docker Compose services...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Listing", total=1)
        
        result = await docker_integration.compose_ps(
            compose_file=compose_file,
            project_directory=dir_path,
            services=services,
            all_services=all_services
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        if not result.get("services"):
            console.print("[yellow]No Docker Compose services found.[/yellow]")
            return
        
        # Display raw output for simplicity, as format can vary
        console.print(result["raw_output"])
    else:
        console.print(f"[red]Error listing Docker Compose services: {result.get('error', 'Unknown error')}[/red]")


@app.command("compose-logs")
async def compose_logs(
    compose_file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to docker-compose.yml"),
    directory: Optional[str] = typer.Option(None, "--dir", help="Project directory (default: current directory)"),
    follow: bool = typer.Option(False, "--follow", help="Follow log output"),
    tail: Optional[int] = typer.Option(None, "--tail", help="Number of lines to show from the end"),
    timestamps: bool = typer.Option(False, "--timestamps", help="Show timestamps"),
    services: List[str] = typer.Argument(None, help="Services to show logs for (default: all)")
):
    """View logs from Docker Compose services."""
    # Resolve directory
    if directory:
        dir_path = Path(directory).absolute()
    else:
        dir_path = context_manager.cwd
    
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(f"[red]Error: Project directory does not exist or is not a directory: {dir_path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Getting Docker Compose logs...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Getting logs", total=1)
        
        result = await docker_integration.compose_logs(
            compose_file=compose_file,
            project_directory=dir_path,
            services=services,
            follow=follow,
            tail=tail,
            timestamps=timestamps
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        logs = result.get("logs", "")
        
        if not logs.strip():
            console.print("[yellow]No logs available for these services.[/yellow]")
            return
        
        console.print(Panel(
            logs,
            title="Docker Compose Logs",
            expand=False,
            border_style="blue"
        ))
        
        if result.get("truncated", False):
            console.print("[yellow]Log output truncated due to size or streaming timeout.[/yellow]")
    else:
        console.print(f"[red]Error getting Docker Compose logs: {result.get('error', 'Unknown error')}[/red]")


# Dockerfile and docker-compose.yml generation commands

@app.command("generate-dockerfile")
async def generate_dockerfile(
    directory: str = typer.Argument(".", help="Project directory"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing file")
):
    """Generate a Dockerfile for a project."""
    # Resolve directory
    dir_path = Path(directory).absolute()
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(f"[red]Error: Project directory does not exist or is not a directory: {dir_path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Generating Dockerfile for {dir_path}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Generating", total=1)
        
        result = await docker_integration.generate_dockerfile(
            project_directory=dir_path,
            output_file=output,
            overwrite=overwrite
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        dockerfile_path = result["dockerfile_path"]
        content = result.get("content", "")
        
        console.print(f"[green]Dockerfile generated successfully at {dockerfile_path}[/green]")
        
        # Display the content
        console.print(Syntax(
            content,
            "dockerfile",
            theme="monokai",
            word_wrap=True,
            line_numbers=True
        ))
    else:
        if "already exists" in result.get("error", ""):
            console.print(f"[yellow]{result['error']} Use --overwrite to replace it.[/yellow]")
        else:
            console.print(f"[red]Error generating Dockerfile: {result.get('error', 'Unknown error')}[/red]")


@app.command("generate-compose")
async def generate_docker_compose(
    directory: str = typer.Argument(".", help="Project directory"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing file"),
    include_databases: bool = typer.Option(True, "--databases/--no-databases", help="Include detected database services")
):
    """Generate a docker-compose.yml file for a project."""
    # Resolve directory
    dir_path = Path(directory).absolute()
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(f"[red]Error: Project directory does not exist or is not a directory: {dir_path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Generating docker-compose.yml for {dir_path}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Generating", total=1)
        
        result = await docker_integration.generate_docker_compose(
            project_directory=dir_path,
            output_file=output,
            overwrite=overwrite,
            include_databases=include_databases
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        compose_file_path = result["compose_file_path"]
        content = result.get("content", "")
        services = result.get("services_included", [])
        
        console.print(f"[green]docker-compose.yml generated successfully at {compose_file_path}[/green]")
        console.print(f"[green]Services included: {', '.join(services)}[/green]")
        
        # Display the content
        console.print(Syntax(
            content,
            "yaml",
            theme="monokai",
            word_wrap=True,
            line_numbers=True
        ))
    else:
        if "already exists" in result.get("error", ""):
            console.print(f"[yellow]{result['error']} Use --overwrite to replace it.[/yellow]")
        else:
            console.print(f"[red]Error generating docker-compose.yml: {result.get('error', 'Unknown error')}[/red]")


@app.command("generate-dockerignore")
async def generate_dockerignore(
    directory: str = typer.Argument(".", help="Project directory"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing file")
):
    """Generate a .dockerignore file for a project."""
    # Resolve directory
    dir_path = Path(directory).absolute()
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(f"[red]Error: Project directory does not exist or is not a directory: {dir_path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Generating .dockerignore for {dir_path}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Generating", total=1)
        
        result = await docker_integration.generate_dockerignore(
            project_directory=dir_path,
            output_file=output,
            overwrite=overwrite
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        dockerignore_path = result["path"]
        content = result.get("content", "")
        
        console.print(f"[green].dockerignore generated successfully at {dockerignore_path}[/green]")
        
        # Display the content
        console.print(Syntax(
            content,
            "gitignore",
            theme="monokai",
            word_wrap=True,
            line_numbers=True
        ))
    else:
        if "already exists" in result.get("error", ""):
            console.print(f"[yellow]{result['error']} Use --overwrite to replace it.[/yellow]")
        else:
            console.print(f"[red]Error generating .dockerignore: {result.get('error', 'Unknown error')}[/red]")


@app.command("setup")
async def setup_docker_project(
    directory: str = typer.Argument(".", help="Project directory"),
    dockerfile: bool = typer.Option(True, "--dockerfile/--no-dockerfile", help="Generate Dockerfile"),
    compose: bool = typer.Option(True, "--compose/--no-compose", help="Generate docker-compose.yml"),
    dockerignore: bool = typer.Option(True, "--dockerignore/--no-dockerignore", help="Generate .dockerignore"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files"),
    databases: bool = typer.Option(True, "--databases/--no-databases", help="Include detected database services"),
    build: bool = typer.Option(False, "--build", help="Build Docker image after setup")
):
    """Set up a complete Docker environment for a project."""
    # Resolve directory
    dir_path = Path(directory).absolute()
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(f"[red]Error: Project directory does not exist or is not a directory: {dir_path}[/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Setting up Docker environment for {dir_path}...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Setting up", total=1)
        
        result = await docker_integration.setup_docker_project(
            project_directory=dir_path,
            generate_dockerfile=dockerfile,
            generate_compose=compose,
            generate_dockerignore=dockerignore,
            overwrite=overwrite,
            include_databases=databases,
            build_image=build
        )
        
        progress.update(task, completed=1)
    
    if result["success"]:
        files_generated = result.get("files_generated", [])
        console.print(f"[green]Docker environment setup completed successfully.[/green]")
        
        if files_generated:
            console.print("[green]Files generated:[/green]")
            for file_path in files_generated:
                console.print(f"[green]- {file_path}[/green]")
        
        if build and result.get("build_image", {}).get("success", False):
            console.print("[green]Docker image built successfully.[/green]")
        elif build and result.get("build_warnings"):
            console.print(f"[yellow]Warning during image build: {result['build_warnings']}[/yellow]")
    else:
        console.print(f"[red]Error setting up Docker environment: {result.get('error', 'Unknown error')}[/red]")
        
        # Show detailed results if available
        if "dockerfile" in result and not result["dockerfile"].get("success", False):
            console.print(f"[red]Dockerfile error: {result['dockerfile'].get('error', 'Unknown error')}[/red]")
        
        if "docker_compose" in result and not result["docker_compose"].get("success", False):
            console.print(f"[red]docker-compose.yml error: {result['docker_compose'].get('error', 'Unknown error')}[/red]")
        
        if "dockerignore" in result and not result["dockerignore"].get("success", False):
            console.print(f"[red].dockerignore error: {result['dockerignore'].get('error', 'Unknown error')}[/red]")


@app.command("info")
async def info():
    """Display detailed information about the Docker setup."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Getting Docker information...[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Getting info", total=1)
        
        # Check Docker and Docker Compose availability
        docker_available = await docker_integration.is_docker_available()
        compose_available = await docker_integration.is_docker_compose_available()
        
        # Execute docker info command if available
        docker_info_output = ""
        if docker_available:
            stdout, stderr, exit_code = await execution_engine.execute_command(
                "docker info",
                check_safety=True
            )
            if exit_code == 0:
                docker_info_output = stdout
        
        progress.update(task, completed=1)
    
    # Display information
    if docker_available:
        console.print(Panel(
            docker_info_output,
            title="Docker Information",
            expand=False,
            border_style="blue"
        ))
        
        console.print(f"Docker Compose: {'[green]Available[/green]' if compose_available else '[red]Not Available[/red]'}")
    else:
        console.print("[red]Docker is not available. Install Docker to use these features.[/red]")


# Run the app directly when this module is executed
if __name__ == "__main__":
    app()
