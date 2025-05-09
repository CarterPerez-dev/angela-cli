# angela/cli/file_extensions.py
"""
CLI extensions for file resolution and activity tracking.

This module extends the files command with advanced file resolution features.
"""
import asyncio
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rich_print

from angela.context.enhancer import context_enhancer
from angela.context import context_manager, file_resolver, file_activity_tracker, ActivityType
from angela.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Create a Typer app for files extensions
app = typer.Typer(name="files", help="Advanced file operations")


@app.command("resolve")
def resolve_file(
    reference: str = typer.Argument(..., help="File reference to resolve"),
    scope: str = typer.Option(
        "all", "--scope", "-s", 
        help="Search scope (project, directory, all)"
    ),
):
    """Resolve a file reference to an actual file path."""
    # Get the current context
    context = context_manager.get_context_dict()
    
    # Convert scope
    search_scope = None
    if scope == "project":
        search_scope = "project"
    elif scope == "directory":
        search_scope = "directory"
    
    # Run the resolver
    try:
        path = asyncio.run(file_resolver.resolve_reference(
            reference,
            context,
            search_scope=search_scope
        ))
        
        if path:
            # Show the resolved path
            console.print(Panel(
                f"Resolved '[bold]{reference}[/bold]' to:\n[green]{path}[/green]",
                title="File Resolution",
                border_style="green"
            ))
            
            # Track as viewed file
            file_activity_tracker.track_file_viewing(path, None, {
                "reference": reference,
                "resolved_via": "cli"
            })
        else:
            # Show not found message
            console.print(Panel(
                f"Could not resolve '[bold]{reference}[/bold]' to a file or directory.",
                title="File Resolution",
                border_style="yellow"
            ))
            
            # Show suggestions based on the scope
            if search_scope == "project" and context.get("project_root"):
                # Suggest listing files in project
                console.print("Try using 'angela files find' to search for files in the project.")
            elif search_scope == "directory":
                # Suggest listing files in directory
                console.print("Try using 'angela files ls' to list files in the current directory.")
            else:
                # Suggest other scopes
                console.print("Try using '--scope project' or '--scope directory' to narrow the search.")
    
    except Exception as e:
        logger.exception(f"Error resolving file reference: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@app.command("extract")
def extract_references(
    text: str = typer.Argument(..., help="Text containing file references"),
):
    """Extract and resolve file references from text."""
    # Get the current context
    context = context_manager.get_context_dict()
    
    # Run the extractor
    try:
        references = asyncio.run(file_resolver.extract_references(text, context))
        
        if references:
            # Create a table for the results
            table = Table(title="Extracted File References")
            table.add_column("Reference", style="cyan")
            table.add_column("Resolved Path", style="green")
            table.add_column("Status", style="yellow")
            
            for reference, path in references:
                if path:
                    status = "[green]Found[/green]"
                    path_str = str(path)
                    
                    # Track as viewed file
                    file_activity_tracker.track_file_viewing(path, None, {
                        "reference": reference,
                        "extracted_via": "cli"
                    })
                else:
                    status = "[yellow]Not Found[/yellow]"
                    path_str = "[italic]Not resolved[/italic]"
                
                table.add_row(reference, path_str, status)
            
            console.print(table)
        else:
            # Show not found message
            console.print(Panel(
                f"No file references found in the text.",
                title="File References",
                border_style="yellow"
            ))
    
    except Exception as e:
        logger.exception(f"Error extracting file references: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@app.command("recent")
def recent_files(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of files to show"),
    activity_type: Optional[str] = typer.Option(
        None, "--type", "-t", 
        help="Filter by activity type (viewed, created, modified, deleted)"
    ),
):
    """Show recently accessed files."""
    try:
        # Convert activity type
        activity_types = None
        if activity_type:
            try:
                activity_types = [ActivityType(activity_type)]
            except ValueError:
                console.print(f"[yellow]Invalid activity type: {activity_type}[/yellow]")
                console.print("Available types: viewed, created, modified, deleted")
                return
        
        # Get recent activities
        activities = file_activity_tracker.get_recent_activities(
            limit=limit,
            activity_types=activity_types
        )
        
        if activities:
            # Create a table for the results
            table = Table(title=f"Recent File Activities (Last {len(activities)})")
            table.add_column("File", style="cyan")
            table.add_column("Activity", style="green")
            table.add_column("Time", style="yellow")
            table.add_column("Command", style="blue")
            
            for activity in activities:
                # Format the file name and path
                file_name = activity.get("name", "unknown")
                file_path = activity.get("path", "unknown")
                file_str = f"{file_name}\n[dim]{file_path}[/dim]"
                
                # Format activity type
                activity_type = activity.get("activity_type", "unknown")
                if activity_type == "viewed":
                    activity_str = "[blue]Viewed[/blue]"
                elif activity_type == "created":
                    activity_str = "[green]Created[/green]"
                elif activity_type == "modified":
                    activity_str = "[yellow]Modified[/yellow]"
                elif activity_type == "deleted":
                    activity_str = "[red]Deleted[/red]"
                else:
                    activity_str = activity_type.capitalize()
                
                # Format time
                time_str = activity.get("datetime", "unknown")
                if "T" in time_str:
                    time_str = time_str.replace("T", " ").split(".")[0]  # Simplify timestamp
                
                # Format command (truncate if too long)
                command = activity.get("command", "")
                if command and len(command) > 40:
                    command = command[:37] + "..."
                
                table.add_row(file_str, activity_str, time_str, command)
            
            console.print(table)
        else:
            # Show no activities message
            console.print(Panel(
                f"No file activities tracked yet.",
                title="Recent Files",
                border_style="yellow"
            ))
            
            # Show help message
            console.print("File activities are tracked when you interact with files using Angela.")
            console.print("Try viewing or manipulating some files first.")
    
    except Exception as e:
        logger.exception(f"Error retrieving recent files: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@app.command("active")
def most_active_files(
    limit: int = typer.Option(5, "--limit", "-n", help="Number of files to show"),
):
    """Show most actively used files."""
    try:
        # Get most active files
        active_files = file_activity_tracker.get_most_active_files(limit=limit)
        
        if active_files:
            # Create a table for the results
            table = Table(title=f"Most Active Files (Top {len(active_files)})")
            table.add_column("File", style="cyan")
            table.add_column("Activity Count", style="green")
            table.add_column("Last Activity", style="yellow")
            table.add_column("Activity Types", style="blue")
            
            for file_info in active_files:
                # Format the file name and path
                file_name = file_info.get("name", "unknown")
                file_path = file_info.get("path", "unknown")
                file_str = f"{file_name}\n[dim]{file_path}[/dim]"
                
                # Format activity count
                count = file_info.get("count", 0)
                
                # Format last activity time
                last_activity = file_info.get("last_activity", 0)
                if last_activity:
                    from datetime import datetime
                    time_str = datetime.fromtimestamp(last_activity).isoformat()
                    if "T" in time_str:
                        time_str = time_str.replace("T", " ").split(".")[0]  # Simplify timestamp
                else:
                    time_str = "Unknown"
                
                # Format activity types
                activities = file_info.get("activities", [])
                activities_str = ", ".join(a.capitalize() for a in activities)
                
                table.add_row(file_str, str(count), time_str, activities_str)
            
            console.print(table)
        else:
            # Show no activities message
            console.print(Panel(
                f"No file activities tracked yet.",
                title="Most Active Files",
                border_style="yellow"
            ))
            
            # Show help message
            console.print("File activities are tracked when you interact with files using Angela.")
            console.print("Try viewing or manipulating some files first.")
    
    except Exception as e:
        logger.exception(f"Error retrieving most active files: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@app.command("project")
def show_project_info():
    """Show detected project information."""
    try:
        # Get the current context
        context = context_manager.get_context_dict()
        
        # Check if in a project
        if not context.get("project_root"):
            console.print(Panel(
                "Not currently in a project directory.",
                title="Project Information",
                border_style="yellow"
            ))
            return
        
        # Get enhanced project info
        from angela.context.enhancer import context_enhancer
        
        # Enrich context
        enriched = asyncio.run(context_enhancer.enrich_context(context))
        project_info = enriched.get("enhanced_project", {})
        
        if project_info:
            # Create a panel for the project information
            project_type = project_info.get("type", "Unknown")
            project_root = context.get("project_root", "Unknown")
            
            content = f"[bold]Project Type:[/bold] {project_type}\n"
            content += f"[bold]Project Root:[/bold] {project_root}\n\n"
            
            # Add frameworks if available
            if project_info.get("frameworks"):
                frameworks = list(project_info["frameworks"].keys())
                content += f"[bold]Frameworks:[/bold] {', '.join(frameworks)}\n"
            
            # Add dependencies if available
            if project_info.get("dependencies") and project_info["dependencies"].get("top_dependencies"):
                deps = project_info["dependencies"]["top_dependencies"]
                content += f"[bold]Top Dependencies:[/bold] {', '.join(deps[:5])}"
                if len(deps) > 5:
                    content += f" and {len(deps) - 5} more"
                content += f" (Total: {project_info['dependencies'].get('total', 0)})\n"
            
            # Add important files if available
            if project_info.get("important_files") and project_info["important_files"].get("paths"):
                files = project_info["important_files"]["paths"]
                content += f"[bold]Important Files:[/bold]\n"
                for f in files[:5]:
                    content += f"• {f}\n"
                if len(files) > 5:
                    content += f"• ... and {len(files) - 5} more\n"
            
            # Add structure info if available
            if project_info.get("structure"):
                structure = project_info["structure"]
                content += f"\n[bold]Project Structure:[/bold]\n"
                content += f"• Total Files: {structure.get('total_files', 'Unknown')}\n"
                
                if structure.get("main_directories"):
                    content += f"• Main Directories: {', '.join(structure['main_directories'])}\n"
                
                if structure.get("file_counts"):
                    content += f"• Top File Types:\n"
                    sorted_types = sorted(
                        structure["file_counts"].items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )
                    for ext, count in sorted_types[:5]:
                        content += f"  - {ext}: {count}\n"
            
            console.print(Panel(
                content,
                title=f"Project Information: {project_type}",
                border_style="green",
                expand=False
            ))
        else:
            # Show no project info message
            console.print(Panel(
                f"No enhanced project information available.",
                title="Project Information",
                border_style="yellow"
            ))
            
            # Show basic project info
            console.print(f"[bold]Project Root:[/bold] {context.get('project_root', 'Unknown')}")
            console.print(f"[bold]Project Type:[/bold] {context.get('project_type', 'Unknown')}")
    
    except Exception as e:
        logger.exception(f"Error retrieving project information: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
