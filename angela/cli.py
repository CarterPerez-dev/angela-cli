# angela/cli.py
"""
Command-line interface for Angela CLI.
"""
iimport sys
import asyncio
from typing import List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich import print as rich_print

from angela import __version__
from angela.config import config_manager
from angela.orchestrator import orchestrator
from angela.utils.logging import setup_logging, get_logger

# Keep existing app definition and version_callback

@app.command()
def request(
    request_text: List[str] = typer.Argument(
        ..., help="The natural language request for Angela."
    ),
    execute: bool = typer.Option(
        False, "--execute", "-e", help="Execute the suggested command."
    ),
):
    """Send a natural language request to Angela."""
    # Combine all arguments into a single request string
    full_request = " ".join(request_text)
    
    try:
        # Process the request
        result = asyncio.run(orchestrator.process_request(full_request, execute))
        
        # Display the response
        panel_title = Text("Angela", style="bold green")
        
        if "suggestion" in result:
            suggestion = result["suggestion"]
            
            # Build panel content with command suggestion
            panel_content = Text()
            panel_content.append("I suggest using this command:\n\n", style="bold")
            
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
            panel_content = Text(result.get("response", "I couldn't process that request."))
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
    """
    Initialize Angela CLI with configuration.
    """
    console.print("Initializing Angela CLI...")
    
    # Check if API key is already set
    if config_manager.config.api.gemini_api_key:
        console.print("[green]API key already configured.[/green]")
    else:
        console.print("Google Gemini API key is required for Angela to function.")
        api_key = typer.prompt("Enter your Gemini API key", hide_input=True)
        config_manager.config.api.gemini_api_key = api_key
    
    # Save the configuration
    config_manager.save_config()
    
    console.print("[green]Configuration saved successfully![/green]")
    console.print("\nTo install shell integration, run the installation script:")
    console.print("[blue]  bash scripts/install.sh[/blue]")


if __name__ == "__main__":
    app()
