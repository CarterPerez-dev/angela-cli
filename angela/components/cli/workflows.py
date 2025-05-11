# angela/cli/workflows.py
"""
Workflow management commands for Angela CLI.

This module provides CLI commands for creating, running, and managing workflows.
"""
import sys
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm

from angela.workflows.manager import workflow_manager
from angela.context import context_manager
from angela.shell.formatter import terminal_formatter
from angela.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Create the workflow commands app
app = typer.Typer(help="Manage Angela workflows")


# Define this at module level to replace await_func
def run_async(coro):
    """Run an async function from a synchronous context.
    
    This function handles getting the appropriate event loop
    rather than creating a new one with asyncio.run(), which causes
    problems when called from an async context.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@app.command("list")
def list_workflows(
    tag: Optional[str] = typer.Option(
        None, "--tag", "-t", help="Filter workflows by tag"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed information"
    ),
):
    """List available workflows."""
    try:
        # Get workflows
        workflows = workflow_manager.list_workflows(tag)
        
        if not workflows:
            if tag:
                console.print(f"No workflows found with tag: {tag}")
            else:
                console.print("No workflows defined yet. Use 'angela workflows create' to define one.")
            return
        
        # Create table for workflows
        table = Table(title="Available Workflows")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Steps", style="magenta", justify="right")
        
        if verbose:
            table.add_column("Tags", style="blue")
            table.add_column("Created", style="green")
        
        # Add workflows to table
        for workflow in workflows:
            if verbose:
                tags = ", ".join(workflow.tags) if workflow.tags else ""
                created = workflow.created.strftime("%Y-%m-%d %H:%M")
                table.add_row(
                    workflow.name,
                    workflow.description,
                    str(len(workflow.steps)),
                    tags,
                    created
                )
            else:
                table.add_row(
                    workflow.name,
                    workflow.description,
                    str(len(workflow.steps))
                )
        
        # Display the table
        console.print(table)
        
    except Exception as e:
        logger.exception(f"Error listing workflows: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("export")
def export_workflow(
    name: str = typer.Argument(
        ..., help="Name of the workflow to export"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output path for the exported workflow"
    ),
):
    """Export a workflow to a shareable package."""
    try:
        # Get the workflow sharing manager
        from angela.workflows.sharing import workflow_sharing_manager
        
        # Export the workflow using run_async instead of asyncio.run()
        result = run_async(workflow_sharing_manager.export_workflow(
            workflow_name=name,
            output_path=output
        ))
        
        if result["success"]:
            console.print(f"[bold green]Workflow '{name}' exported successfully![/bold green]")
            console.print(f"Output path: {result['output_path']}")
        else:
            console.print(f"[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
    except Exception as e:
        logger.exception(f"Error exporting workflow: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("import")
def import_workflow(
    path: Path = typer.Argument(
        ..., help="Path to the workflow package to import"
    ),
    rename: Optional[str] = typer.Option(
        None, "--rename", "-r", help="New name for the imported workflow"
    ),
    replace: bool = typer.Option(
        False, "--replace", help="Replace existing workflow with same name"
    ),
):
    """Import a workflow from a package."""
    try:
        # Get the workflow sharing manager
        from angela.workflows.sharing import workflow_sharing_manager
        
        # Import the workflow using run_async instead of asyncio.run()
        result = run_async(workflow_sharing_manager.import_workflow(
            workflow_path=path,
            rename=rename,
            replace_existing=replace
        ))
        
        if result["success"]:
            console.print(f"[bold green]Workflow imported successfully as '{result['workflow']}'![/bold green]")
        else:
            console.print(f"[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
    except Exception as e:
        logger.exception(f"Error importing workflow: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("create")
def create_workflow(
    name: str = typer.Argument(..., help="Name for the workflow"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Description of the workflow"
    ),
    from_file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Load workflow definition from a file"
    ),
):
    """Create a new workflow."""
    try:
        # Get description if not provided
        if not description:
            description = Prompt.ask("Enter workflow description")
        
        steps = []
        
        if from_file:
            # Load workflow definition from file
            if not from_file.exists():
                console.print(f"[bold red]Error:[/bold red] File not found: {from_file}")
                sys.exit(1)
            
            # Read the file
            with open(from_file, "r") as f:
                workflow_text = f.read()
            
            # Get context
            context = context_manager.get_context_dict()
            
            # Define workflow from file content using run_async instead of asyncio.run()
            workflow = run_async(workflow_manager.define_workflow_from_natural_language(
                name=name,
                description=description,
                natural_language=workflow_text,
                context=context
            ))
        else:
            # Interactive workflow creation
            console.print("Enter the steps for your workflow. Each step should be a shell command.")
            console.print("Press [bold cyan]Enter[/bold cyan] on an empty line when finished.")
            
            step_num = 1
            while True:
                command = Prompt.ask(f"Step {step_num} command", default="")
                if not command:
                    break
                
                explanation = Prompt.ask(f"Step {step_num} explanation", default="")
                optional = Confirm.ask(f"Is step {step_num} optional?", default=False)
                requires_confirmation = Confirm.ask(f"Does step {step_num} require confirmation?", default=False)
                
                steps.append({
                    "command": command,
                    "explanation": explanation,
                    "optional": optional,
                    "requires_confirmation": requires_confirmation
                })
                
                step_num += 1
            
            # Need at least one step
            if not steps:
                console.print("[bold red]Error:[/bold red] Workflow must have at least one step.")
                sys.exit(1)
            
            # Define the workflow using run_async instead of asyncio.run()
            workflow = run_async(workflow_manager.define_workflow(
                name=name,
                description=description,
                steps=steps
            ))
        
        # Display the created workflow using run_async instead of await_func
        run_async(terminal_formatter.display_workflow(workflow))
        
        console.print(f"[bold green]Workflow '{name}' created successfully![/bold green]")
        console.print(f"Run it with: [bold cyan]angela workflows run {name}[/bold cyan]")
        
    except Exception as e:
        logger.exception(f"Error creating workflow: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("run")
def run_workflow(
    name: str = typer.Argument(..., help="Name of the workflow to run"),
    variable: List[str] = typer.Option(
        [], "--var", "-v", help="Variable value in format NAME=VALUE"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without executing"
    ),
):
    """Run a workflow."""
    try:
        # Check if workflow exists
        workflow = workflow_manager.get_workflow(name)
        if not workflow:
            console.print(f"[bold red]Error:[/bold red] Workflow '{name}' not found.")
            
            # Show available workflows
            available = workflow_manager.list_workflows()
            if available:
                console.print("\nAvailable workflows:")
                for w in available:
                    console.print(f"  - {w.name}")
            else:
                console.print("\nNo workflows defined yet. Use 'angela workflows create' to define one.")
                
            sys.exit(1)
        
        # Parse variables
        variables = {}
        for var in variable:
            if "=" in var:
                key, value = var.split("=", 1)
                variables[key] = value
            else:
                console.print(f"[bold yellow]Warning:[/bold yellow] Ignoring invalid variable format: {var}")
        
        # Get context
        context = context_manager.get_context_dict()
        
        # Display the workflow using run_async instead of await_func
        run_async(terminal_formatter.display_workflow(workflow, variables))
        
        # Confirm execution
        if not dry_run:
            if not Confirm.ask("Execute this workflow?", default=True):
                console.print("Workflow execution cancelled.")
                return
        
        # Execute the workflow using run_async instead of asyncio.run()
        result = run_async(workflow_manager.execute_workflow(
            workflow_name=name,
            variables=variables,
            context=context,
            dry_run=dry_run
        ))
        
        # Display results
        if result["success"]:
            status = "[bold green]Workflow executed successfully![/bold green]"
            if dry_run:
                status = "[bold blue]Dry run completed successfully![/bold blue]"
            console.print(status)
        else:
            console.print("[bold red]Workflow execution failed.[/bold red]")
            
            if result.get("error"):
                console.print(f"Error: {result['error']}")
        
    except Exception as e:
        logger.exception(f"Error running workflow: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("delete")
def delete_workflow(
    name: str = typer.Argument(..., help="Name of the workflow to delete"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Delete without confirmation"
    ),
):
    """Delete a workflow."""
    try:
        # Check if workflow exists
        workflow = workflow_manager.get_workflow(name)
        if not workflow:
            console.print(f"[bold red]Error:[/bold red] Workflow '{name}' not found.")
            sys.exit(1)
        
        # Confirm deletion
        if not force:
            if not Confirm.ask(f"Are you sure you want to delete workflow '{name}'?", default=False):
                console.print("Deletion cancelled.")
                return
        
        # Delete the workflow
        workflow_manager.delete_workflow(name)
        
        console.print(f"[bold green]Workflow '{name}' deleted successfully.[/bold green]")
        
    except Exception as e:
        logger.exception(f"Error deleting workflow: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("show")
def show_workflow(
    name: str = typer.Argument(..., help="Name of the workflow to show"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed information"
    ),
):
    """Show details of a workflow."""
    try:
        # Get the workflow
        workflow = workflow_manager.get_workflow(name)
        if not workflow:
            console.print(f"[bold red]Error:[/bold red] Workflow '{name}' not found.")
            sys.exit(1)
        
        # Display the workflow using run_async instead of await_func
        run_async(terminal_formatter.display_workflow(workflow))
        
        # Show additional details if verbose
        if verbose:
            console.print("\n[bold]Additional Details:[/bold]")
            console.print(f"Created: {workflow.created.strftime('%Y-%m-%d %H:%M:%S')}")
            console.print(f"Last Modified: {workflow.modified.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if workflow.tags:
                console.print(f"Tags: {', '.join(workflow.tags)}")
            
            if workflow.author:
                console.print(f"Author: {workflow.author}")
            
            if workflow.variables:
                console.print("\n[bold]Variables:[/bold]")
                for var_name, var_desc in workflow.variables.items():
                    console.print(f"  {var_name}: {var_desc}")
        
    except Exception as e:
        logger.exception(f"Error showing workflow: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)

