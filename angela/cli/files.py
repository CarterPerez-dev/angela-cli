"""
File operation commands for Angela CLI.

This module provides CLI commands for file and directory operations.
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markup import escape
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.filesize import decimal as format_size

from angela.context import context_manager
from angela.execution.filesystem import (
    create_directory, delete_directory, create_file, read_file,
    write_file, delete_file, copy_file, move_file, FileSystemError
)
from angela.execution.rollback import rollback_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Create the file operations app
app = typer.Typer(help="Angela's file operations")


@app.command("ls")
def list_directory(
    path: str = typer.Argument(
        None, help="Directory to list (defaults to current directory)"
    ),
    all: bool = typer.Option(
        False, "--all", "-a", help="Include hidden files"
    ),
    long: bool = typer.Option(
        False, "--long", "-l", help="Show detailed information"
    ),
):
    """List directory contents with enhanced formatting."""
    try:
        dir_path = Path(path) if path else context_manager.cwd
        
        if not dir_path.exists():
            console.print(f"[bold red]Error:[/bold red] Path not found: {dir_path}")
            sys.exit(1)
        
        if not dir_path.is_dir():
            console.print(f"[bold red]Error:[/bold red] Not a directory: {dir_path}")
            sys.exit(1)
        
        # Get directory contents
        contents = context_manager.get_directory_contents(dir_path, include_hidden=all)
        
        if not contents:
            console.print(f"Directory is empty: {dir_path}")
            return
        
        # Display in table format if long listing is requested
        if long:
            table = Table(title=f"Contents of {dir_path}")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Size", style="blue", justify="right")
            table.add_column("Language", style="magenta")
            
            for item in contents:
                name = item["name"]
                
                # Add indicator for directories
                if item["is_dir"]:
                    name = f"{name}/"
                
                # Format size
                size = format_size(item["size"]) if "size" in item else ""
                
                # Get type and language
                item_type = item.get("type", "unknown")
                language = item.get("language", "")
                
                table.add_row(name, item_type, size, language)
            
            console.print(table)
        
        # Simple listing
        else:
            for item in contents:
                name = item["name"]
                
                # Color and format based on type
                if item["is_dir"]:
                    console.print(f"[bold blue]{name}/[/bold blue]", end="  ")
                elif item.get("language"):
                    console.print(f"[green]{name}[/green]", end="  ")
                elif item.get("binary", False):
                    console.print(f"[dim]{name}[/dim]", end="  ")
                else:
                    console.print(name, end="  ")
            
            # End with a newline
            console.print()
        
    except Exception as e:
        logger.exception(f"Error listing directory: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("mkdir")
def make_directory(
    path: str = typer.Argument(..., help="Directory to create"),
    parents: bool = typer.Option(
        True, "--parents/--no-parents", "-p", help="Create parent directories if needed"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without making changes"
    ),
):
    """Create a directory."""
    try:
        # Run the operation
        success = asyncio.run(create_directory(path, parents=parents, dry_run=dry_run))
        
        if success:
            if dry_run:
                console.print(f"[bold blue]DRY RUN:[/bold blue] Would create directory: {path}")
            else:
                console.print(f"[bold green]Created directory:[/bold green] {path}")
        else:
            console.print(f"[bold yellow]Operation cancelled.[/bold yellow]")
            sys.exit(1)
        
    except FileSystemError as e:
        logger.exception(f"Error creating directory: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("rmdir")
def remove_directory(
    path: str = typer.Argument(..., help="Directory to remove"),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="Recursively remove directories and their contents"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Ignore nonexistent files"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without making changes"
    ),
):
    """Remove a directory."""
    try:
        # Run the operation
        success = asyncio.run(delete_directory(
            path, recursive=recursive, force=force, dry_run=dry_run
        ))
        
        if success:
            if dry_run:
                console.print(f"[bold blue]DRY RUN:[/bold blue] Would remove directory: {path}")
            else:
                console.print(f"[bold green]Removed directory:[/bold green] {path}")
        else:
            console.print(f"[bold yellow]Operation cancelled.[/bold yellow]")
            sys.exit(1)
        
    except FileSystemError as e:
        logger.exception(f"Error removing directory: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("touch")
def touch_file(
    path: str = typer.Argument(..., help="File to create or update timestamp"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without making changes"
    ),
):
    """Create a new file or update file timestamp."""
    try:
        # Run the operation (with no content for touch)
        success = asyncio.run(create_file(path, content=None, dry_run=dry_run))
        
        if success:
            if dry_run:
                console.print(f"[bold blue]DRY RUN:[/bold blue] Would touch file: {path}")
            else:
                console.print(f"[bold green]Touched file:[/bold green] {path}")
        else:
            console.print(f"[bold yellow]Operation cancelled.[/bold yellow]")
            sys.exit(1)
        
    except FileSystemError as e:
        logger.exception(f"Error touching file: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("cat")
def cat_file(
    path: str = typer.Argument(..., help="File to display"),
    binary: bool = typer.Option(
        False, "--binary", "-b", help="Display binary content"
    ),
    syntax: bool = typer.Option(
        True, "--syntax/--no-syntax", help="Syntax highlighting"
    ),
):
    """Display file contents."""
    try:
        file_path = Path(path)
        
        # Get file info to determine syntax highlighting
        file_info = context_manager.get_file_info(file_path)
        
        # Read the file
        content = asyncio.run(read_file(path, binary=binary))
        
        # Display the content
        if binary:
            # For binary files, just show a hexdump-like output
            console.print(Panel(
                escape(repr(content[:1000])) + ("..." if len(content) > 1000 else ""),
                title=f"Binary content of {path}",
                subtitle=f"Showing first 1000 bytes of {len(content)} total bytes",
                expand=False
            ))
        elif syntax and file_info.get("language") and not binary:
            # Determine the language for syntax highlighting
            lang = file_info.get("language", "").lower()
            if "python" in lang:
                lang = "python"
            elif "javascript" in lang:
                lang = "javascript"
            elif "html" in lang:
                lang = "html"
            elif "css" in lang:
                lang = "css"
            elif "json" in lang:
                lang = "json"
            elif "yaml" in lang:
                lang = "yaml"
            elif "markdown" in lang:
                lang = "markdown"
            elif "bash" in lang or "shell" in lang:
                lang = "bash"
            else:
                lang = "text"
            
            # Display with syntax highlighting
            console.print(Syntax(
                content,
                lang,
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            ))
        else:
            # Simple text display
            console.print(content)
        
    except FileSystemError as e:
        logger.exception(f"Error reading file: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("rm")
def remove_file(
    path: str = typer.Argument(..., help="File to remove"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Ignore nonexistent files"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without making changes"
    ),
):
    """Remove a file."""
    try:
        # Run the operation
        success = asyncio.run(delete_file(path, force=force, dry_run=dry_run))
        
        if success:
            if dry_run:
                console.print(f"[bold blue]DRY RUN:[/bold blue] Would remove file: {path}")
            else:
                console.print(f"[bold green]Removed file:[/bold green] {path}")
        else:
            console.print(f"[bold yellow]Operation cancelled.[/bold yellow]")
            sys.exit(1)
        
    except FileSystemError as e:
        logger.exception(f"Error removing file: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("cp")
def copy_file_command(
    source: str = typer.Argument(..., help="Source file to copy"),
    destination: str = typer.Argument(..., help="Destination path"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite destination if it exists"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without making changes"
    ),
):
    """Copy a file."""
    try:
        # Run the operation
        success = asyncio.run(copy_file(
            source, destination, overwrite=force, dry_run=dry_run
        ))
        
        if success:
            if dry_run:
                console.print(f"[bold blue]DRY RUN:[/bold blue] Would copy {source} to {destination}")
            else:
                console.print(f"[bold green]Copied:[/bold green] {source} -> {destination}")
        else:
            console.print(f"[bold yellow]Operation cancelled.[/bold yellow]")
            sys.exit(1)
        
    except FileSystemError as e:
        logger.exception(f"Error copying file: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("mv")
def move_file_command(
    source: str = typer.Argument(..., help="Source file to move"),
    destination: str = typer.Argument(..., help="Destination path"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite destination if it exists"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without making changes"
    ),
):
    """Move a file."""
    try:
        # Run the operation
        success = asyncio.run(move_file(
            source, destination, overwrite=force, dry_run=dry_run
        ))
        
        if success:
            if dry_run:
                console.print(f"[bold blue]DRY RUN:[/bold blue] Would move {source} to {destination}")
            else:
                console.print(f"[bold green]Moved:[/bold green] {source} -> {destination}")
        else:
            console.print(f"[bold yellow]Operation cancelled.[/bold yellow]")
            sys.exit(1)
        
    except FileSystemError as e:
        logger.exception(f"Error moving file: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("write")
def write_file_command(
    path: str = typer.Argument(..., help="File to write to"),
    content: str = typer.Option(
        None, "--content", "-c", help="Content to write (if not provided, will prompt)"
    ),
    append: bool = typer.Option(
        False, "--append", "-a", help="Append to file instead of overwriting"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without making changes"
    ),
):
    """Write content to a file."""
    try:
        # If content is not provided, prompt for it
        if content is None:
            console.print(f"Enter content for {path} (press Ctrl+D on a new line to finish):")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            content = "\n".join(lines)
        
        # Run the operation
        success = asyncio.run(write_file(
            path, content, append=append, dry_run=dry_run
        ))
        
        if success:
            if dry_run:
                mode = "append to" if append else "write to"
                console.print(f"[bold blue]DRY RUN:[/bold blue] Would {mode} file: {path}")
            else:
                mode = "Appended to" if append else "Wrote to"
                console.print(f"[bold green]{mode} file:[/bold green] {path}")
        else:
            console.print(f"[bold yellow]Operation cancelled.[/bold yellow]")
            sys.exit(1)
        
    except FileSystemError as e:
        logger.exception(f"Error writing file: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("find")
def find_files(
    pattern: str = typer.Argument(..., help="Pattern to search for"),
    path: str = typer.Option(
        ".", "--path", "-p", help="Directory to search in"
    ),
    include_hidden: bool = typer.Option(
        False, "--hidden", "-a", help="Include hidden files"
    ),
):
    """Find files matching a pattern."""
    try:
        base_dir = Path(path)
        if not base_dir.exists() or not base_dir.is_dir():
            console.print(f"[bold red]Error:[/bold red] Not a valid directory: {path}")
            sys.exit(1)
        
        # Find files matching the pattern
        matches = context_manager.find_files(
            pattern, base_dir=base_dir, include_hidden=include_hidden
        )
        
        if not matches:
            console.print(f"No files found matching pattern: {pattern}")
            return
        
        # Display results
        console.print(f"Found {len(matches)} files matching '{pattern}':")
        
        for match in matches:
            # Get file info
            file_info = context_manager.get_file_info(match)
            
            # Format the output
            if file_info.get("is_dir", False):
                console.print(f"[bold blue]{match}/[/bold blue]")
            elif file_info.get("language"):
                lang = file_info.get("language", "")
                console.print(f"[green]{match}[/green] - [magenta]{lang}[/magenta]")
            else:
                console.print(str(match))
        
    except Exception as e:
        logger.exception(f"Error finding files: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("rollback")
def rollback_command(
    list_only: bool = typer.Option(
        False, "--list", "-l", help="List recent operations without rolling back"
    ),
    operation_id: int = typer.Option(
        None, "--id", help="ID of the specific operation to roll back"
    ),
):
    """Roll back a previous file operation."""
    try:
        # Get recent operations
        operations = asyncio.run(rollback_manager.get_recent_operations())
        
        if not operations:
            console.print("No operations available for rollback.")
            return
        
        # If list_only is specified, just show the operations
        if list_only:
            table = Table(title="Recent Operations")
            table.add_column("ID", style="cyan")
            table.add_column("Timestamp", style="blue")
            table.add_column("Operation", style="green")
            table.add_column("Description")
            table.add_column("Can Rollback", style="magenta")
            
            for op in operations:
                can_rollback = "✓" if op["can_rollback"] else "✗"
                table.add_row(
                    str(op["id"]),
                    op["timestamp"],
                    op["operation_type"],
                    op["description"],
                    can_rollback
                )
            
            console.print(table)
            return
        
        # If no ID is provided, show the list and prompt for one
        if operation_id is None:
            table = Table(title="Recent Operations")
            table.add_column("ID", style="cyan")
            table.add_column("Timestamp", style="blue")
            table.add_column("Description")
            table.add_column("Can Rollback", style="magenta")
            
            for op in operations:
                can_rollback = "✓" if op["can_rollback"] else "✗"
                table.add_row(
                    str(op["id"]),
                    op["timestamp"],
                    op["description"],
                    can_rollback
                )
            
            console.print(table)
            
            # Prompt for the operation ID
            operation_id = int(Prompt.ask("Enter the ID of the operation to roll back"))
        
        # Check if the operation ID is valid
        valid_ids = [op["id"] for op in operations]
        if operation_id not in valid_ids:
            console.print(f"[bold red]Error:[/bold red] Invalid operation ID: {operation_id}")
            sys.exit(1)
        
        # Check if the operation can be rolled back
        operation = next(op for op in operations if op["id"] == operation_id)
        if not operation["can_rollback"]:
            console.print(f"[bold red]Error:[/bold red] Operation cannot be rolled back: {operation['description']}")
            sys.exit(1)
        
        # Confirm the rollback
        confirmed = Confirm.ask(f"Roll back operation: {operation['description']}?")
        if not confirmed:
            console.print("Rollback cancelled.")
            return
        
        # Perform the rollback
        success = asyncio.run(rollback_manager.rollback_operation(operation_id))
        
        if success:
            console.print(f"[bold green]Successfully rolled back:[/bold green] {operation['description']}")
        else:
            console.print(f"[bold red]Failed to roll back operation.[/bold red]")
            sys.exit(1)
        
    except Exception as e:
        logger.exception(f"Error during rollback: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command("info")
def file_info(
    path: str = typer.Argument(
        None, help="File to get information about (defaults to current directory)"
    ),
    preview: bool = typer.Option(
        True, "--preview/--no-preview", help="Show file content preview"
    ),
):
    """Show detailed information about a file or directory."""
    try:
        file_path = Path(path) if path else context_manager.cwd
        
        if not file_path.exists():
            console.print(f"[bold red]Error:[/bold red] Path not found: {file_path}")
            sys.exit(1)
        
        # Get file information
        file_info = context_manager.get_file_info(file_path)
        
        # Display information
        console.print(Panel(
            f"[bold]Path:[/bold] {file_info['path']}\n"
            f"[bold]Type:[/bold] {file_info.get('type', 'unknown')}\n"
            + (f"[bold]Language:[/bold] {file_info.get('language', 'N/A')}\n" if file_info.get('language') else "")
            + (f"[bold]MIME Type:[/bold] {file_info.get('mime_type', 'N/A')}\n" if file_info.get('mime_type') else "")
            + (f"[bold]Size:[/bold] {format_size(file_info.get('size', 0))}\n" if 'size' in file_info else "")
            + (f"[bold]Binary:[/bold] {'Yes' if file_info.get('binary', False) else 'No'}\n" if not file_info.get('is_dir', False) else ""),
            title=f"Information for {file_path.name}",
            expand=False
        ))
        
        # Show content preview for files
        if preview and not file_info.get('is_dir', False) and not file_info.get('binary', False):
            content_preview = context_manager.get_file_preview(file_path)
            
            if content_preview:
                # Try to determine the language for syntax highlighting
                lang = "text"
                if file_info.get("language"):
                    lang_name = file_info.get("language", "").lower()
                    if "python" in lang_name:
                        lang = "python"
                    elif "javascript" in lang_name:
                        lang = "javascript"
                    elif "html" in lang_name:
                        lang = "html"
                    elif "css" in lang_name:
                        lang = "css"
                    elif "json" in lang_name:
                        lang = "json"
                    elif "yaml" in lang_name:
                        lang = "yaml"
                    elif "markdown" in lang_name:
                        lang = "markdown"
                    elif "bash" in lang_name or "shell" in lang_name:
                        lang = "bash"
                
                console.print(Panel(
                    Syntax(
                        content_preview,
                        lang,
                        theme="monokai",
                        line_numbers=True,
                        word_wrap=True
                    ),
                    title="Content Preview",
                    expand=False
                ))
        
    except Exception as e:
        logger.exception(f"Error getting file information: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)
