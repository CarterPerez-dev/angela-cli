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
from angela.context import context_manager
from angela.orchestrator import orchestrator
from angela.execution.engine import execution_engine
from angela.utils.logging import setup_logging, get_logger

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
):
    """Angela: AI-powered command-line assistant"""
    # Set debug mode
    config_manager.config.debug = debug
    
    # Configure logging
    setup_logging(debug=debug)


@app.command()
def request(
    request_text: List[str] = typer.Argument(
        ..., help="The natural language request for Angela."
    ),
    execute: bool = typer.Option(
        False, "--execute", "-e", help="Execute the suggested command."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview command execution without making changes."
    ),
):
    """Send a natural language request to Angela."""
    # Combine all arguments into a single request string
    full_request = " ".join(request_text)
    
    try:
        # Process the request
        result = asyncio.run(orchestrator.process_request(
            full_request, execute=execute, dry_run=dry_run
        ))
        
        # Display the response
        panel_title = "Angela"
        
        if "suggestion" in result:
            suggestion = result["suggestion"]
            
            # Build panel content with command suggestion
            console.print("[bold]I suggest using this command:[/bold]")
            
            # Add the command with syntax highlighting
            command_syntax = Syntax(suggestion.command, "bash", theme="monokai", word_wrap=True)
            console.print(Panel(command_syntax, title="Command", expand=False))
            
            # Show explanation
            console.print("\n[bold]Explanation:[/bold]")
            console.print(suggestion.explanation)
            
            # Show execution results if executed
            if "execution" in result:
                execution = result["execution"]
                console.print("\n[bold]Command Output:[/bold]")
                
                if execution["success"]:
                    if execution["stdout"].strip():
                        output_panel = Panel(
                            execution["stdout"], 
                            title="Output", 
                            expand=False,
                            border_style="green"
                        )
                        console.print(output_panel)
                    else:
                        console.print("[green]Command executed successfully with no output.[/green]")
                else:
                    console.print("[bold red]Command failed[/bold red]")
                    if execution["stderr"].strip():
                        error_panel = Panel(
                            execution["stderr"], 
                            title="Error", 
                            expand=False,
                            border_style="red"
                        )
                        console.print(error_panel)
            
        else:
            # Fall back to simple response if no suggestion
            panel_content = result.get("response", "I couldn't process that request.")
            console.print(Panel(panel_content, title=panel_title, expand=False))
        
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
