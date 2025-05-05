# angela/cli.py
"""
Command-line interface for Angela CLI.
"""
import sys
from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rich_print

from angela import __version__
from angela.config import config_manager
from angela.orchestrator import orchestrator
from angela.utils.logging import setup_logging, get_logger

app = typer.Typer(
    name="angela",
    help="AI-powered command-line assistant integrated into your terminal shell",
    add_completion=False,
)

console = Console()
logger = get_logger(__name__)


def version_callback(value: bool):
    """Callback for --version flag."""
    if value:
        console.print(f"Angela CLI version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, help="Show version and exit."
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug mode with verbose logging."
    ),
):
    """
    Angela CLI - Your AI-powered command-line assistant.
    """
    # Set up logging first
    setup_logging(debug=debug)
    
    # Load configuration
    config_manager.load_config()
    
    # Override debug setting from command line if specified
    if debug:
        config_manager.config.debug = True


@app.command()
def request(
    request_text: List[str] = typer.Argument(
        ..., help="The natural language request for Angela."
    )
):
    """
    Send a natural language request to Angela.
    """
    # Combine all arguments into a single request string
    full_request = " ".join(request_text)
    
    try:
        # Process the request
        result = orchestrator.process_request(full_request)
        
        # Display the response
        panel_title = Text("Angela", style="bold green")
        panel_content = Text(result["response"])
        
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
