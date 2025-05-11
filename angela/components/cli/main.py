# angela/cli/main.py
"""
Main command-line interface for Angela CLI.
"""
import sys
import asyncio
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rich_print

from angela import __version__
from angela.config import config_manager
from angela.api.context import get_context_manager
from angela.orchestrator import orchestrator            
from angela.api.execution import get_execution_engine
from angela.utils.logging import setup_logging, get_logger
from angela.api.shell import get_terminal_formatter, get_output_type_enum
from angela.api.ai import get_error_analyzer
from angela.api.context import get_session_manager

context_manager = get_context_manager()
execution_engine = get_execution_engine()
terminal_formatter = get_terminal_formatter()
OutputType = get_output_type_enum()
error_analyzer = get_error_analyzer()
session_manager = get_session_manager()

# Create the app
app = typer.Typer(help="Angela: AI-powered command-line assistant")
logger = get_logger(__name__)
console = Console()


def version_callback(value: bool):
    """Display version information and exit."""
    if value:
        console.print(f"Angela CLI version: {__version__}")
        sys.exit(0)


@app.callback()
def main(
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug mode"
    ),
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, help="Show version and exit"
    ),
    monitor: bool = typer.Option(
        False, "--monitor", "-m", help="Enable background monitoring for proactive assistance"
    ),
):
    """Angela: AI-powered command-line assistant"""
    # Set debug mode
    config_manager.config.debug = debug
    
    # Configure logging
    setup_logging(debug=debug)
    
    # Start background monitoring if requested
    if monitor:
        # Import here to avoid circular imports
        from angela.monitoring.background import background_monitor
        background_monitor.start_monitoring()


@app.command()
def request(
    request_text: List[str] = typer.Argument(
        ..., help="The natural language request for Angela."
    ),
    suggest_only: bool = typer.Option(
        False, "--suggest-only", "-s", help="Only suggest commands without executing."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview command execution without making changes."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Execute without confirmation, even for risky operations."
    ),
):
    """Send a natural language request to Angela."""
    # Combine all arguments into a single request string
    full_request = " ".join(request_text)
    
    try:
        # If forcing execution, set this in the session
        if force:
            session_manager.add_entity("force_execution", "preference", "true")
        
        # Process the request - note execute=True is now the default
        # Only switch to false if suggest_only is True
        execute = not suggest_only
        
        # Call the orchestrator to process the request
        result = asyncio.run(orchestrator.process_request(
            full_request, execute=execute, dry_run=dry_run
        ))
        
        if "suggestion" in result:
            suggestion = result["suggestion"]
            
            # Display the suggestion with rich formatting
            terminal_formatter.print_command(suggestion.command, title="Command")
            
            # Show confidence if available
            if "confidence" in result:
                confidence = result["confidence"]
                confidence_color = "green" if confidence > 0.8 else "yellow" if confidence > 0.6 else "red"
                console.print(f"[bold]Confidence:[/bold] [{confidence_color}]{confidence:.2f}[/{confidence_color}]")
            
            # Show explanation
            console.print("\n[bold]Explanation:[/bold]")
            console.print(suggestion.explanation)
            
            # Show execution results if executed
            if "execution" in result:
                execution = result["execution"]
                console.print("\n[bold]Command Output:[/bold]")
                
                if execution["success"]:
                    if execution["stdout"].strip():
                        terminal_formatter.print_output(
                            execution["stdout"],
                            OutputType.STDOUT,
                            title="Output"
                        )
                    else:
                        console.print("[green]Command executed successfully with no output.[/green]")
                else:
                    console.print("[bold red]Command failed[/bold red]")
                    if execution["stderr"].strip():
                        terminal_formatter.print_output(
                            execution["stderr"],
                            OutputType.STDERR,
                            title="Error"
                        )
                    
                    # Show error analysis if available
                    if "error_analysis" in result:
                        terminal_formatter.print_error_analysis(result["error_analysis"])
                        
                    # Show fix suggestions if available
                    if "fix_suggestions" in execution:
                        console.print("\n[bold]Suggested fixes:[/bold]")
                        for suggestion in execution["fix_suggestions"]:
                            console.print(f"• {suggestion}")
            
        else:
            # Fall back to simple response if no suggestion
            panel_content = result.get("response", "I couldn't process that request.")
            console.print(Panel(panel_content, title="Angela", expand=False))
        
        # In debug mode, show context information
        if config_manager.config.debug:
            context_text = "\n".join([f"{k}: {v}" for k, v in result["context"].items()])
            rich_print("[bold blue]Context:[/bold blue]")
            rich_print(context_text)
            
    except Exception as e:
        logger.exception("Error processing request")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if config_manager.config.debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command()
def init():
    """Initialize Angela CLI with configuration."""
    console.print("Initializing Angela CLI...")
    
    # Check if API key is already set
    if config_manager.config.api.gemini_api_key:
        console.print("[green]API key already configured.[/green]")
    else:
        console.print("Google Gemini API key is required for Angela to function.")
        api_key = typer.prompt("Enter your Gemini API key", hide_input=True)
        config_manager.config.api.gemini_api_key = api_key
    
    # Configure safety options
    confirm_all = typer.confirm("Require confirmation for all operations?", default=False)
    config_manager.config.user.confirm_all_actions = confirm_all
    
    # Configure project root
    set_project_root = typer.confirm("Set a default project root?", default=False)
    if set_project_root:
        project_root = typer.prompt("Enter the path to your default project root")
        config_manager.config.user.default_project_root = project_root
    
    # Save the configuration
    config_manager.save_config()
    
    console.print("[green]Configuration saved successfully![/green]")
    console.print("\nAngela CLI is now initialized. You can use the following commands:")
    console.print("  [blue]angela <your request>[/blue] - Process a natural language request")
    console.print("  [blue]angela files <command>[/blue] - Perform file operations")
    console.print("  [blue]angela --help[/blue] - Show help")


@app.command("status")
def show_status():
    """Show the status of Angela CLI features and components."""
    from rich.table import Table
    from angela import __version__
    from angela.constants import APP_NAME, APP_DESCRIPTION
    
    # Display general status
    console.print(Panel(
        f"Angela CLI v{__version__}\n"
        f"{APP_DESCRIPTION}",
        title="Status",
        expand=False
    ))
    
    # Display configuration status
    config = config_manager.config
    config_status = Table(title="Configuration Status")
    config_status.add_column("Setting", style="cyan")
    config_status.add_column("Status", style="green")
    
    # Check API key status
    api_key_status = "[green]Configured[/green]" if config.api.gemini_api_key else "[red]Not configured[/red]"
    config_status.add_row("API Key", api_key_status)
    
    # Check configuration directory
    config_dir_status = "[green]Exists[/green]" if config_manager.CONFIG_DIR.exists() else "[red]Not found[/red]"
    config_status.add_row("Config Directory", config_dir_status)
    
    # Check user preferences
    confirm_actions = "Enabled" if config.user.confirm_all_actions else "Standard risk-based"
    config_status.add_row("Confirmations", confirm_actions)
    
    # Check debug mode
    debug_mode = "Enabled" if config.debug else "Disabled"
    config_status.add_row("Debug Mode", debug_mode)
    
    console.print(config_status)
    
    # Display project information if available
    project_type = context_manager.project_type
    project_root = context_manager.project_root
    
    if project_root:
        # Project detected
        project_info = Table(title="Project Information")
        project_info.add_column("Property", style="cyan")
        project_info.add_column("Value", style="green")
        
        project_info.add_row("Project Type", project_type or "Unknown")
        project_info.add_row("Project Root", str(project_root))
        
        # Count files in project
        try:
            file_count = sum(1 for _ in Path(project_root).glob('**/*') if _.is_file())
            project_info.add_row("Files", str(file_count))
        except Exception:
            project_info.add_row("Files", "Error counting")
        
        # Detect source directories
        try:
            source_dirs = []
            common_src_dirs = ['src', 'lib', 'app', 'angela']
            for dir_name in common_src_dirs:
                if (Path(project_root) / dir_name).is_dir():
                    source_dirs.append(dir_name)
            
            if source_dirs:
                project_info.add_row("Source Directories", ", ".join(source_dirs))
        except Exception:
            pass
        
        console.print(project_info)
    else:
        # No project detected
        console.print("[yellow]No project detected in the current directory.[/yellow]")
    
    # Display available components and services
    try:
        from angela.core.registry import registry
        
        services = registry.list_services()
        if services:
            service_table = Table(title="Registered Services")
            service_table.add_column("Service", style="cyan")
            service_table.add_column("Type", style="green")
            
            # Get a subset of interesting services to display
            interesting_services = {
                k: v for k, v in services.items() 
                if not k.startswith('_') and k not in ('app', 'registry')
            }
            
            # Limit to at most 10 services to avoid cluttering the display
            display_count = min(10, len(interesting_services))
            
            for i, (name, service_type) in enumerate(interesting_services.items()):
                if i >= display_count:
                    service_table.add_row(f"... and {len(interesting_services) - display_count} more", "")
                    break
                service_table.add_row(name, service_type.__name__)
            
            console.print(service_table)
    except Exception as e:
        if config.debug:
            console.print(f"[red]Error getting service information: {str(e)}[/red]")
    
    # Display system information
    console.print("\n[bold]System Information:[/bold]")
    console.print(f"• Current Directory: {context_manager.cwd}")
    if project_root:
        console.print(f"• Project Root: {project_root}")
    
    # Show Python version
    import sys
    console.print(f"• Python Version: {sys.version.split()[0]}")
    
    # Show platform
    import platform
    console.print(f"• Platform: {platform.system()} {platform.release()}")



@app.command("--notify", hidden=True)
def notify(
    notification_type: str = typer.Argument(..., help="Type of notification"),
    args: List[str] = typer.Argument(None, help="Additional arguments")
):
    """
    Handle notifications from shell hooks.
    This is an internal command not meant to be called directly by users.
    """
    # Import here to avoid circular imports
    from angela.monitoring.notification_handler import notification_handler
    
    try:
        # Run the notification handler asynchronously
        asyncio.run(notification_handler.handle_notification(notification_type, *args))
    except Exception as e:
        logger.exception(f"Error handling notification: {str(e)}")
        # Swallow the exception to avoid disrupting the shell
        pass
    
    # Always exit cleanly - we don't want to disrupt the shell
    return

@app.command("--completions", hidden=True)
def completions(
    args: List[str] = typer.Argument(None, help="Current command line arguments")
):
    """
    Generate completions for the angela command.
    This is an internal command used by shell completion.
    """
    try:
        # Import here to avoid circular imports
        from angela.shell.completion import completion_handler
        
        # Get the completions
        result = asyncio.run(completion_handler.get_completions(args))
        
        # Print the completions directly to stdout for shell consumption
        print(" ".join(result))
    except Exception as e:
        logger.exception(f"Error generating completions: {str(e)}")
        # Return empty result on error
        print("")
    
    return



@app.command()
def shell():
    """Launch an interactive shell with Angela."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    
    # Create a history file
    history_file = config_manager.CONFIG_DIR / "shell_history.txt"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create session with history
    session = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
    )
    
    console.print(Panel(
        "Welcome to Angela's interactive shell!\n"
        "Type your requests directly and press Enter.\n"
        "Type 'exit' or press Ctrl+D to exit.",
        title="Angela Interactive Shell",
        expand=False
    ))
    
    # Main interaction loop
    while True:
        try:
            # Get input from the user
            text = session.prompt("angela> ")
            
            # Check for exit command
            if text.lower() in ("exit", "quit", "bye"):
                break
            
            # Skip empty input
            if not text.strip():
                continue
            
            # Process the request
            result = asyncio.run(orchestrator.process_request(text))
            
            # Display the response
            if "suggestion" in result:
                suggestion = result["suggestion"]
                
                # Show the command suggestion
                console.print("[bold]I suggest:[/bold]")
                command_syntax = Syntax(suggestion.command, "bash", theme="monokai")
                console.print(Panel(command_syntax, title="Command", expand=False))
                
                # Show explanation
                console.print(suggestion.explanation)
                
                # Ask if the user wants to execute the command
                execute_command = typer.confirm("Execute this command?", default=False)
                if execute_command:
                    # Execute the command
                    stdout, stderr, return_code = asyncio.run(
                        execution_engine.execute_command(suggestion.command)
                    )
                    
                    # Display the results
                    if return_code == 0:
                        if stdout:
                            console.print(Panel(stdout, title="Output", expand=False))
                        else:
                            console.print("[green]Command executed successfully with no output.[/green]")
                    else:
                        console.print("[bold red]Command failed:[/bold red]")
                        if stderr:
                            console.print(Panel(stderr, title="Error", expand=False))
            
            else:
                # Fall back to simple response
                console.print(result.get("response", "I couldn't process that request."))
            
            # Add a separator between interactions
            console.print("─" * console.width)
            
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            continue
        except EOFError:
            # Handle Ctrl+D (exit)
            break
        except Exception as e:
            logger.exception("Error in interactive shell")
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
    
    console.print("Goodbye!")
