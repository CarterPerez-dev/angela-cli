# angela/shell/formatter.py
"""
Rich terminal formatting for Angela CLI.

This module provides enhanced terminal output formatting with
support for async operations and interactive elements.
"""
import asyncio
import sys
from typing import Optional, List, Dict, Any, Callable, Awaitable, Tuple, Set
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.layout import Layout
from rich.tree import Tree
from rich import box
from angela.intent.planner import AdvancedTaskPlan, PlanStepType

_console = Console(record=True, width=100)


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
    
    async def display_task_plan(self, plan: Any) -> None:
        """
        Display a task plan with rich interactive visualization.
        
        Args:
            plan: The task plan to display
        """
        # Create a table for the plan steps
        table = Table(title=f"Plan for: {plan.goal}", box=box.ROUNDED)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Command", style="green")
        table.add_column("Explanation", style="white")
        table.add_column("Risk", style="yellow", no_wrap=True)
        table.add_column("Dependencies", style="magenta", no_wrap=True)
        
        # Risk level names
        risk_names = ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        risk_styles = ["green", "blue", "yellow", "red", "bold red"]
        
        # Add steps to the table
        for i, step in enumerate(plan.steps):
            risk_idx = step.estimated_risk if 0 <= step.estimated_risk < len(risk_names) else 0
            risk_name = risk_names[risk_idx]
            risk_style = risk_styles[risk_idx]
            
            # Format dependencies
            deps = ", ".join([str(d+1) for d in step.dependencies]) if step.dependencies else "None"
            
            # Create syntax object
            syntax = Syntax(step.command, "bash", theme="monokai", word_wrap=True)
            
            # Render to string instead of using .markup
            _console.record = True
            _console.print(syntax)
            syntax_str = _console.export_text(styles=True)
            _console.record = False
            
            table.add_row(
                str(i + 1),
                syntax_str,
                step.explanation,
                f"[{risk_style}]{risk_name}[/{risk_style}]",
                deps
            )
        
        # Display the table
        self._console.print("\n")
        self._console.print(Panel(
            "I've created a plan to accomplish your goal. Here are the steps I'll take:",
            title="Task Plan",
            border_style="blue"
        ))
        self._console.print(table)
        
        # Create a dependency visualization if there are non-trivial dependencies
        has_dependencies = any(step.dependencies for step in plan.steps)
        if has_dependencies:
            await self._display_dependency_graph(plan)
    
    async def _display_dependency_graph(self, plan: Any) -> None:
        """
        Display a visual representation of the dependency graph.
        
        Args:
            plan: The task plan with dependencies
        """
        # Create a dependency tree
        tree = Tree("Execution Flow", guide_style="bold blue")
        
        # Track processed steps
        processed = set()
        
        # Add steps with no dependencies first (roots)
        roots = []
        for i, step in enumerate(plan.steps):
            if not step.dependencies:
                roots.append(i)
                node = tree.add(f"Step {i+1}: {step.command[:30]}..." if len(step.command) > 30 else step.command)
                processed.add(i)
                
                # Add children recursively
                self._add_dependency_children(node, i, plan, processed)
        
        # Check if any steps were not processed (in case of circular dependencies)
        if len(processed) < len(plan.steps):
            for i, step in enumerate(plan.steps):
                if i not in processed:
                    node = tree.add(f"Step {i+1}: {step.command[:30]}..." if len(step.command) > 30 else step.command)
                    processed.add(i)
                    
                    # Add children recursively
                    self._add_dependency_children(node, i, plan, processed)
        
        # Display the tree
        self._console.print("\n[bold blue]Dependency Graph:[/bold blue]")
        self._console.print(tree)
    
    def _add_dependency_children(
        self, 
        parent_node: Any, 
        step_idx: int, 
        plan: Any, 
        processed: Set[int]
    ) -> None:
        """
        Recursively add children to a dependency node.
        
        Args:
            parent_node: The parent tree node
            step_idx: The index of the current step
            plan: The task plan
            processed: Set of already processed steps
        """
        # Find steps that depend on this one
        for i, step in enumerate(plan.steps):
            if step_idx in step.dependencies and i not in processed:
                node = parent_node.add(f"Step {i+1}: {step.command[:30]}..." 
                                       if len(step.command) > 30 else step.command)
                processed.add(i)
                
                # Recurse
                self._add_dependency_children(node, i, plan, processed)
    
    async def display_multi_step_execution(
        self, 
        plan: Any, 
        results: List[Dict[str, Any]]
    ) -> None:
        """
        Display the results of a multi-step execution.
        
        Args:
            plan: The task plan that was executed
            results: The execution results for each step
        """
        # Create a table for the execution results
        table = Table(title="Execution Results", box=box.ROUNDED)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Command", style="green")
        table.add_column("Status", style="white", no_wrap=True)
        table.add_column("Output", style="white")
        
        # Add results to the table
        for i, result in enumerate(results):
            # Get the command
            command = result.get("command", plan.steps[i].command if i < len(plan.steps) else "Unknown")
            
            # Get status
            status = "[green]Success[/green]" if result.get("success", False) else "[red]Failed[/red]"
            
            # Get output (combine stdout and stderr)
            stdout = result.get("stdout", "").strip()
            stderr = result.get("stderr", "").strip()
            
            # Truncate output if too long
            output = stdout
            if stderr:
                if output:
                    output += "\n"
                output += f"[red]{stderr}[/red]"
            
            if len(output) > 100:
                output = output[:97] + "..."
            
            table.add_row(
                str(i + 1),
                Syntax(command, "bash", theme="monokai", word_wrap=True).markup,
                status,
                output
            )
        
        # Display the table
        self._console.print("\n")
        self._console.print(Panel(
            "Execution results for your multi-step task:",
            title="Multi-Step Execution",
            border_style="blue"
        ))
        self._console.print(table)
        
        # Display summary
        success_count = sum(1 for r in results if r.get("success", False))
        total_count = len(results)
        
        if success_count == total_count:
            self._console.print(f"[bold green]All {total_count} steps completed successfully![/bold green]")
        else:
            self._console.print(f"[bold yellow]{success_count} of {total_count} steps completed successfully[/bold yellow]")
            
            # Show which steps failed
            failed_steps = [i+1 for i, r in enumerate(results) if not r.get("success", False)]
            if failed_steps:
                self._console.print(f"[bold red]Failed steps: {', '.join(map(str, failed_steps))}[/bold red]")
    
    async def display_workflow(self, workflow: Any, variables: Dict[str, Any] = None) -> None:
        """
        Display a workflow with rich formatting.
        
        Args:
            workflow: The workflow to display
            variables: Optional variables for the workflow
        """
        # Create a table for the workflow steps
        table = Table(title=f"Workflow: {workflow.name}", box=box.ROUNDED)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Command", style="green")
        table.add_column("Explanation", style="white")
        table.add_column("Options", style="yellow")
        
        # Add steps to the table
        for i, step in enumerate(workflow.steps):
            # Apply variable substitution if variables provided
            command = step.command
            if variables:
                for var_name, var_value in variables.items():
                    # Remove leading $ if present
                    clean_name = var_name[1:] if var_name.startswith('$') else var_name
                    
                    # Substitute ${VAR} syntax
                    command = command.replace(f"${{{clean_name}}}", str(var_value))
                    
                    # Substitute $VAR syntax
                    command = command.replace(f"${clean_name}", str(var_value))
            
            options = []
            if step.optional:
                options.append("Optional")
            if step.requires_confirmation:
                options.append("Requires Confirmation")
            
            table.add_row(
                str(i + 1),
                Syntax(command, "bash", theme="monokai", word_wrap=True).markup,
                step.explanation,
                ", ".join(options) if options else ""
            )
        
        # Display the table
        self._console.print("\n")
        self._console.print(Panel(
            workflow.description,
            title=f"Workflow: {workflow.name}",
            border_style="blue"
        ))
        self._console.print(table)
        
        # Display variables if provided
        if variables:
            var_table = Table(title="Variables", box=box.SIMPLE)
            var_table.add_column("Name", style="cyan")
            var_table.add_column("Value", style="green")
            
            for var_name, var_value in variables.items():
                var_table.add_row(var_name, str(var_value))
            
            self._console.print(var_table)
    
    async def display_file_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Display file content analysis results.
        
        Args:
            analysis: The analysis results
        """
        self._console.print("\n")
        self._console.print(Panel(
            f"Analysis of {analysis.get('path', 'file')}",
            title="File Analysis",
            border_style="blue"
        ))
        
        # Display language and type info
        file_type = analysis.get("type", "unknown")
        language = analysis.get("language")
        
        if language:
            self._console.print(f"[bold]File type:[/bold] {file_type} ({language})")
        else:
            self._console.print(f"[bold]File type:[/bold] {file_type}")
        
        # Display the analysis text
        self._console.print("\n[bold]Analysis:[/bold]")
        self._console.print(analysis.get("analysis", "No analysis available"))
    
    async def display_file_manipulation(self, manipulation: Dict[str, Any]) -> None:
        """
        Display file manipulation results with diff.
        
        Args:
            manipulation: The manipulation results
        """
        self._console.print("\n")
        self._console.print(Panel(
            f"Changes to {manipulation.get('path', 'file')}",
            title="File Manipulation",
            border_style="blue"
        ))
        
        # Display the instruction
        self._console.print(f"[bold]Instruction:[/bold] {manipulation.get('instruction', 'Unknown')}")
        
        # Display the diff
        self._console.print("\n[bold]Changes:[/bold]")
        syntax = Syntax(manipulation.get("diff", "No changes"), "diff", theme="monokai")
        self._console.print(syntax)
        
        # Show whether changes were applied
        if manipulation.get("changes_applied", False):
            self._console.print("[bold green]Changes have been applied to the file.[/bold green]")
        elif manipulation.get("dry_run", False):
            self._console.print("[bold blue]Dry run: Changes were not applied to the file.[/bold blue]")
        else:
            self._console.print("[bold yellow]Changes were not applied to the file.[/bold yellow]")
    
    async def display_file_search_results(self, search_results: Dict[str, Any]) -> None:
        """
        Display file search results.
        
        Args:
            search_results: The search results
        """
        self._console.print("\n")
        self._console.print(Panel(
            f"Search results in {search_results.get('path', 'file')}",
            title="File Search",
            border_style="blue"
        ))
        
        # Display the query
        self._console.print(f"[bold]Query:[/bold] {search_results.get('query', 'Unknown')}")
        
        # Display match count
        match_count = search_results.get("match_count", 0)
        self._console.print(f"[bold]Found {match_count} matches[/bold]")
        
        # Display matches
        if match_count > 0:
            matches = search_results.get("matches", [])
            
            for i, match in enumerate(matches, 1):
                self._console.print(f"\n[bold cyan]Match #{i}[/bold cyan] (Lines {match.get('line_start', '?')}-{match.get('line_end', '?')})")
                
                # Display the content with context
                syntax = Syntax(match.get("content", ""), search_results.get("language", "text"), theme="monokai", line_numbers=True)
                self._console.print(syntax)
                
                # Display explanation
                if "explanation" in match:
                    self._console.print(f"[italic]{match['explanation']}[/italic]")
    
    def print_suggestion(self, suggestion: Dict[str, Any], with_confidence: bool = True) -> None:
        """
        Print a command suggestion with rich formatting.
        
        Args:
            suggestion: The command suggestion
            with_confidence: Whether to show confidence score
        """
        self._console.print("\n")
        
        # Extract suggestion components
        command = suggestion.get("command", "")
        explanation = suggestion.get("explanation", "")
        confidence = suggestion.get("confidence", 0.0)
        
        # Display the command
        self.print_command(command)
        
        # Show confidence if requested
        if with_confidence:
            confidence_color = "green" if confidence > 0.8 else "yellow" if confidence > 0.6 else "red"
            self._console.print(f"[bold]Confidence:[/bold] [{confidence_color}]{confidence:.2f}[/{confidence_color}]")
        
        # Show explanation
        self._console.print("\n[bold]Explanation:[/bold]")
        self._console.print(explanation)
    
    def print_proactive_suggestion(self, suggestion: str, source: str = "AI") -> None:
        """
        Print a proactive suggestion.
        
        Args:
            suggestion: The suggestion text
            source: The source of the suggestion
        """
        self._console.print("\n")
        self._console.print(Panel(
            suggestion,
            title=f"Suggestion from {source}",
            border_style="green",
            expand=False
        ))



# Global formatter instance
terminal_formatter = TerminalFormatter()
