# angela/shell/formatter.py

import asyncio
import sys
from typing import Optional, List, Dict, Any, Callable, Awaitable
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text

from angela.utils.logging import get_logger

logger = get_logger(__name__)

class OutputType(Enum):
    """Types of command output."""
    STDOUT = "stdout"
    STDERR = "stderr"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"

class TerminalFormatter:
    """
    Rich terminal formatter with support for asynchronous output
    and interactive elements.
    """
    
    def __init__(self):
        """Initialize the terminal formatter."""
        self._console = Console()
        self._logger = logger
    
    def print_command(self, command: str, title: Optional[str] = None) -> None:
        """
        Display a command with syntax highlighting.
        
        Args:
            command: The command to display
            title: Optional title for the panel
        """
        title = title or "Command"
        syntax = Syntax(command, "bash", theme="monokai", word_wrap=True)
        self._console.print(Panel(syntax, title=title, expand=False))
    
    def print_output(
        self, 
        output: str, 
        output_type: OutputType = OutputType.STDOUT,
        title: Optional[str] = None
    ) -> None:
        """
        Display command output with appropriate formatting.
        
        Args:
            output: The output text
            output_type: Type of output
            title: Optional title for the panel
        """
        if not output:
            return
            
        # Set styling based on output type
        if output_type == OutputType.STDERR or output_type == OutputType.ERROR:
            style = "bold red"
            title = title or "Error"
            border_style = "red"
        elif output_type == OutputType.WARNING:
            style = "yellow"
            title = title or "Warning"
            border_style = "yellow"
        elif output_type == OutputType.SUCCESS:
            style = "green"
            title = title or "Success"
            border_style = "green"
        elif output_type == OutputType.INFO:
            style = "blue"
            title = title or "Info"
            border_style = "blue"
        else:  # Default for STDOUT
            style = "white"
            title = title or "Output"
            border_style = "white"
        
        # Create panel with output
        panel = Panel(output, title=title, border_style=border_style, expand=False)
        self._console.print(panel)
    
    def print_error_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Display error analysis with fix suggestions.
        
        Args:
            analysis: The error analysis dictionary
        """
        # Create a table for the error analysis
        table = Table(title="Error Analysis", expand=False)
        table.add_column("Aspect", style="bold cyan")
        table.add_column("Details", style="white")
        
        # Add error summary
        table.add_row("Error", Text(analysis.get("error_summary", "Unknown error"), style="bold red"))
        
        # Add possible cause
        table.add_row("Possible Cause", analysis.get("possible_cause", "Unknown"))
        
        # Add command issues
        if analysis.get("command_issues"):
            issues = "\n".join(f"• {issue}" for issue in analysis["command_issues"])
            table.add_row("Command Issues", issues)
        
        # Add file issues
        if analysis.get("file_issues"):
            file_issues = []
            for issue in analysis["file_issues"]:
                path = issue.get("path", "unknown")
                if "suggestion" in issue:
                    file_issues.append(f"• {path}: {issue['suggestion']}")
                if "similar_files" in issue:
                    similar = ", ".join(issue["similar_files"])
                    file_issues.append(f"  Did you mean: {similar}?")
            
            if file_issues:
                table.add_row("File Issues", "\n".join(file_issues))
        
        # Display the table
        self._console.print(table)
        
        # Display fix suggestions if available
        if analysis.get("fix_suggestions"):
            suggestions = analysis["fix_suggestions"]
            if suggestions:
                self._console.print(Panel(
                    "\n".join(f"• {suggestion}" for suggestion in suggestions),
                    title="Fix Suggestions",
                    border_style="green",
                    expand=False
                ))
    
    async def stream_output(
        self,
        command: str,
        show_spinner: bool = True,
        show_output: bool = True,
        callback: Optional[Callable[[str, OutputType], Awaitable[None]]] = None
    ) -> Tuple[str, str, int]:
        """
        Stream command output asynchronously with rich formatting.
        
        Args:
            command: The command to execute
            show_spinner: Whether to show a spinner
            show_output: Whether to display output
            callback: Optional callback for when output is received
            
        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        # Import here to avoid circular imports
        from angela.execution.engine import execution_engine
        
        stdout_chunks = []
        stderr_chunks = []
        return_code = None
        
        # Set up progress display if requested
        if show_spinner:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Executing command...[/bold blue]"),
                TimeElapsedColumn(),
                console=self._console
            )
        else:
            progress = None
        
        try:
            # Start progress if requested
            if progress:
                progress.start()
                task = progress.add_task("Executing", total=None)
            
            # Create the process
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Set up tasks to read output
            async def read_stream(stream, output_type: OutputType):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                        
                    try:
                        line_str = line.decode('utf-8', errors='replace')
                        
                        # Store the output
                        if output_type == OutputType.STDOUT:
                            stdout_chunks.append(line_str)
                        else:
                            stderr_chunks.append(line_str)
                        
                        # Display if requested
                        if show_output:
                            if output_type == OutputType.STDOUT:
                                self._console.print(line_str, end="")
                            else:
                                self._console.print(f"[bold red]{line_str}[/bold red]", end="")
                        
                        # Call callback if provided
                        if callback:
                            await callback(line_str, output_type)
                            
                    except Exception as e:
                        self._logger.error(f"Error processing output: {str(e)}")
            
            # Create tasks for stdout and stderr
            stdout_task = asyncio.create_task(read_stream(proc.stdout, OutputType.STDOUT))
            stderr_task = asyncio.create_task(read_stream(proc.stderr, OutputType.STDERR))
            
            # Wait for the process to complete
            return_code = await proc.wait()
            
            # Wait for the streams to complete
            await stdout_task
            await stderr_task
            
            # Update progress
            if progress:
                progress.update(task, completed=True)
        
        finally:
            # Clean up progress
            if progress:
                progress.stop()
        
        # Return the collected output
        return "".join(stdout_chunks), "".join(stderr_chunks), return_code
    
    def create_table(
        self, 
        title: str, 
        columns: List[Tuple[str, Optional[str]]]
    ) -> Table:
        """
        Create a rich table.
        
        Args:
            title: The table title
            columns: List of (column_name, style) tuples
            
        Returns:
            A Rich Table object
        """
        table = Table(title=title, expand=False)
        
        for name, style in columns:
            table.add_column(name, style=style)
            
        return table

# Global formatter instance
terminal_formatter = TerminalFormatter()
