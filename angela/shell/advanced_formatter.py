# angela/shell/advanced_formatter.py
"""
Terminal formatter extensions for displaying advanced task plans.

This module extends the terminal_formatter to properly display advanced
task plans with all step types, data flow, and execution results.
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.tree import Tree
from rich.markdown import Markdown
from rich.text import Text
from rich import box


import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Use a forward reference for typing to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from angela.intent.planner import AdvancedTaskPlan, PlanStepType

from angela.utils.logging import get_logger

logger = get_logger(__name__)

console = Console()

async def display_advanced_plan(plan: Any) -> None:
    """
    Display an advanced task plan with rich formatting.
    
    Args:
        plan: The advanced task plan to display
    """
    # ADD this import inside the function
    from angela.intent.planner import AdvancedTaskPlan, PlanStepType
    
    
    header = Panel(
        f"[bold]{plan.description}[/bold]\n\n{plan.goal}",
        title=f"Advanced Plan: {plan.id}",
        border_style="blue"
    )
    console.print(header)
    
    # Create a table for the steps
    table = Table(
        title="Execution Steps",
        box=box.ROUNDED,
        header_style="bold cyan",
        expand=True
    )
    
    # Add columns
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="green")
    table.add_column("Details", style="yellow")
    table.add_column("Risk", style="red")
    table.add_column("Dependencies", style="blue")
    
    # Add rows for each step
    for step_id, step in plan.steps.items():
        # Format risk level
        risk_colors = ["green", "green", "yellow", "red", "red bold"]
        risk_level = min(step.estimated_risk, 4)  # Cap at 4
        risk_text = f"[{risk_colors[risk_level]}]{risk_level}[/{risk_colors[risk_level]}]"
        
        # Format details based on step type
        details = ""
        if step.type == PlanStepType.COMMAND:
            if step.command:
                details = f"Command: {step.command}"
        elif step.type == PlanStepType.CODE:
            details = f"Code: {len(step.code)} chars"
        elif step.type == PlanStepType.FILE:
            if step.file_path:
                operation = getattr(step, "operation", "read/write")
                details = f"{operation.capitalize()}: {step.file_path}"
        elif step.type == PlanStepType.DECISION:
            if step.condition:
                details = f"Condition: {step.condition}"
        elif step.type == PlanStepType.API:
            if step.api_url:
                details = f"{step.api_method} {step.api_url}"
        elif step.type == PlanStepType.LOOP:
            if step.loop_items:
                details = f"Items: {step.loop_items}"
        
        # Format dependencies
        deps = ", ".join(step.dependencies) if step.dependencies else "None"
        
        # Add row
        table.add_row(
            step_id,
            str(step.type.value),
            step.description,
            details,
            risk_text,
            deps
        )
    
    console.print(table)
    
    # Show execution flow with entry points
    flow_panel = Panel(
        f"Entry Points: [bold cyan]{', '.join(plan.entry_points)}[/bold cyan]",
        title="Execution Flow",
        border_style="green"
    )
    console.print(flow_panel)
    
    # Show dependencies as a tree for visualization
    console.print("\n[bold]Dependency Tree:[/bold]")
    
    # Build dependency tree
    tree = Tree("🔄 [bold]Execution Plan[/bold]")
    
    # Add entry points
    entry_node = tree.add("🚀 [bold cyan]Entry Points[/bold cyan]")
    for entry in plan.entry_points:
        entry_branch = entry_node.add(f"[cyan]{entry}[/cyan]")
        _build_dependency_tree(entry_branch, entry, plan)
    
    console.print(tree)

def _build_dependency_tree(node, step_id, plan):
    """
    Recursively build a dependency tree for visualization.
    
    Args:
        node: The current tree node
        step_id: Current step ID
        plan: The advanced task plan
    """
    
    from angela.intent.planner import PlanStepType
    
    
    # Find steps that depend on this step
    for next_id, next_step in plan.steps.items():
        if step_id in next_step.dependencies:
            step_node = node.add(f"[yellow]{next_id}[/yellow]: {next_step.description}")
            # Recursively build the tree
            _build_dependency_tree(step_node, next_id, plan)
    
    # Special handling for decision steps (branches)
    if step_id in plan.steps and plan.steps[step_id].type == PlanStepType.DECISION:
        step = plan.steps[step_id]
        
        if step.true_branch:
            true_node = node.add("[green]True Branch[/green]")
            for branch_step in step.true_branch:
                branch_text = f"[green]{branch_step}[/green]"
                if branch_step in plan.steps:
                    branch_text += f": {plan.steps[branch_step].description}"
                true_node.add(branch_text)
        
        if step.false_branch:
            false_node = node.add("[red]False Branch[/red]")
            for branch_step in step.false_branch:
                branch_text = f"[red]{branch_step}[/red]"
                if branch_step in plan.steps:
                    branch_text += f": {plan.steps[branch_step].description}"
                false_node.add(branch_text)
    
    # Special handling for loop steps
    if step_id in plan.steps and plan.steps[step_id].type == PlanStepType.LOOP:
        step = plan.steps[step_id]
        
        if step.loop_body:
            loop_node = node.add("[blue]Loop Body[/blue]")
            for body_step in step.loop_body:
                body_text = f"[blue]{body_step}[/blue]"
                if body_step in plan.steps:
                    body_text += f": {plan.steps[body_step].description}"
                loop_node.add(body_text)

async def display_execution_results(
    plan: AdvancedTaskPlan, 
    results: Dict[str, Any]
) -> None:
    """
    Display execution results for an advanced task plan.
    
    Args:
        plan: The executed advanced task plan
        results: The execution results
    """
    
    from angela.intent.planner import AdvancedTaskPlan, PlanStepType

    logger.debug(f"Displaying execution results for plan: {plan.id}")
    
    # Create a header
    success = results.get("success", False)
    success_text = "[bold green]SUCCESS[/bold green]" if success else "[bold red]FAILED[/bold red]"
    
    header = Panel(
        f"Plan execution {success_text}\n\n"
        f"Steps completed: [bold]{results.get('steps_completed', 0)}[/bold] / {results.get('steps_total', len(plan.steps))}\n"
        f"Execution time: [bold]{results.get('execution_time', 0):.2f}[/bold] seconds",
        title=f"Execution Results: {plan.id}",
        border_style="green" if success else "red"
    )
    console.print(header)
    
    # Display execution path
    if "execution_path" in results:
        path_text = " → ".join(results["execution_path"])
        path_panel = Panel(
            path_text,
            title="Execution Path",
            border_style="blue"
        )
        console.print(path_panel)
    
    # Display step results in a table
    if "results" in results:
        step_results = results["results"]
        
        # Create table
        table = Table(
            title="Step Results",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True
        )
        
        # Add columns
        table.add_column("Step", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Output", style="yellow")
        table.add_column("Time (s)", style="blue")
        
        # Add rows for each step in execution order
        execution_order = results.get("execution_path", list(step_results.keys()))
        
        for step_id in execution_order:
            if step_id not in step_results:
                continue
                
            result = step_results[step_id]
            
            # Format status
            status = "[green]Success[/green]" if result.get("success", False) else "[red]Failed[/red]"
            
            # Handle retry/recovery
            if result.get("retried", False):
                status += " [yellow](Retried)[/yellow]"
            if result.get("recovery_applied", False):
                status += " [blue](Recovered)[/blue]"
            
            # Format output based on step type
            output = ""
            # Assuming PlanStepType is an Enum and result["type"] is a string matching an enum value
            step_type_str = result.get("type", "") 
            
            if step_type_str == PlanStepType.COMMAND.value:
                # Get first few lines of stdout
                stdout = result.get("stdout", "").strip()
                if stdout:
                    lines = stdout.split("\n")
                    output = lines[0]
                    if len(lines) > 1:
                        output += f"... (+{len(lines)-1} lines)"
            elif step_type_str == PlanStepType.CODE.value:
                # Show execution result or console output
                if "result" in result:
                    output = f"Result: {result['result']}"
                elif "stdout" in result and result["stdout"]:
                    lines = result["stdout"].strip().split("\n")
                    output = lines[0]
                    if len(lines) > 1:
                        output += f"... (+{len(lines)-1} lines)"
            elif step_type_str == PlanStepType.FILE.value:
                # Show operation result
                output = result.get("message", "")
            elif step_type_str == PlanStepType.DECISION.value:
                # Show condition result
                condition_result = result.get("condition_result", False)
                output = f"Condition: [green]True[/green]" if condition_result else "Condition: [red]False[/red]"
                output += f" → {result.get('next_branch', '')}"
            elif step_type_str == PlanStepType.API.value:
                # Show status code and response summary
                status_code = result.get("status_code", 0)
                output = f"Status: {status_code}"
                
                # Add response summary
                if "json" in result:
                    output += f" (JSON response)"
                elif "text" in result:
                    text = result["text"]
                    if len(text) > 30:
                        text = text[:30] + "..."
                    output += f" Response: {text}"
            elif step_type_str == PlanStepType.LOOP.value:
                # Show loop iteration count
                iterations = result.get("iterations", 0)
                output = f"Iterations: {iterations}"
            
            # Format execution time
            exec_time = result.get("execution_time", 0)
            time_text = f"{exec_time:.2f}"
            
            # Determine display string for step_type for the table
            # This part of the original code correctly handles if step_type_str is an enum or string for display
            display_step_type = step_type_str 
            try:
                # If step_type_str matches an enum value, display the value
                # This assumes PlanStepType can be iterated or accessed by value
                # For simplicity, we'll just use step_type_str, assuming it's descriptive enough
                # Or, if PlanStepType was passed around as enum members:
                # actual_enum_member = result.get("type_enum_member_if_available") 
                # display_step_type = str(actual_enum_member.value) if isinstance(actual_enum_member, PlanStepType) else str(step_type_str)
                pass # Using step_type_str directly for the table is often fine.
            except: # Be careful with bare except
                pass


            table.add_row(
                step_id,
                display_step_type, # Use the string type identifier for display
                status,
                output,
                time_text
            )
        
        console.print(table)
    
    # Display detailed outputs for steps of interest
    if "results" in results:
        step_results = results["results"]
        
        # First show any failed step in detail
        failed_step = results.get("failed_step")
        if failed_step and failed_step in step_results:
            console.print(f"\n[bold red]Failed Step: {failed_step}[/bold red]")
            await display_step_details(failed_step, step_results[failed_step], plan)
        
        # Show details for specific step types that typically have interesting output
        for step_id, result in step_results.items():
            if step_id == failed_step:
                continue  # Already displayed
                
            step_type_str = result.get("type", "")
            
            # Show all API responses, loop results, and code outputs with results
            if step_type_str == PlanStepType.API.value or \
               step_type_str == PlanStepType.LOOP.value or \
               (step_type_str == PlanStepType.CODE.value and ("result" in result or "output" in result)): # Check "output" key for code output
                console.print(f"\n[bold cyan]Step Details: {step_id}[/bold cyan]")
                await display_step_details(step_id, result, plan)
    
    # Show variables at the end of execution if available
    if "variables" in results:
        console.print("\n[bold]Final Variables:[/bold]")
        var_table = Table(title="Data Flow Variables", box=box.ROUNDED)
        var_table.add_column("Name", style="cyan")
        var_table.add_column("Value", style="green")
        var_table.add_column("Source", style="blue")
        
        for var_name, var_info in results["variables"].items():
            # Format value based on type
            value = var_info.get("value", "")
            if isinstance(value, dict) or isinstance(value, list):
                import json
                value_str = json.dumps(value, indent=2)
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
            else:
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
            
            var_table.add_row(
                var_name,
                value_str,
                var_info.get("source_step", "initial")
            )
        
        console.print(var_table)

async def display_step_details(
    step_id: str, 
    result: Dict[str, Any],
    plan: Optional[AdvancedTaskPlan] = None
) -> None:
    """
    Display detailed results for a specific step.
    
    Args:
        step_id: ID of the step
        result: The step's execution result
        plan: Optional plan for context
    """
    # Get the step type as a string from the result
    step_type_str = result.get("type", "")
    
    # Get step description from plan if available
    description = ""
    if plan and step_id in plan.steps:
        description = plan.steps[step_id].description
        # If description is available, print it for context
        if description:
            console.print(f"[bold]Description:[/bold] {description}")

    # Format output based on step type string
    if step_type_str == PlanStepType.COMMAND.value:
        # Show command and output
        console.print(f"[bold]Command:[/bold] {result.get('command', '')}")
        
        if result.get("stdout", "").strip():
            syntax = Syntax(
                result["stdout"],
                "bash-session",
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            console.print(Panel(syntax, title="Standard Output", border_style="green"))
        
        if result.get("stderr", "").strip():
            syntax = Syntax(
                result["stderr"],
                "bash-session",
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            console.print(Panel(syntax, title="Error Output", border_style="red"))
    
    elif step_type_str == PlanStepType.CODE.value:
        # Show code and output
        if "code" in result:
            lang = "python"  # Default to Python
            if plan and step_id in plan.steps:
                # Ensure plan.steps[step_id] exists and has 'language' attribute
                step_details = plan.steps.get(step_id)
                if step_details:
                    lang = getattr(step_details, "language", "python")
            
            syntax = Syntax(
                result["code"],
                lang,
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            console.print(Panel(syntax, title="Code", border_style="blue"))
        
        if "stdout" in result and result["stdout"].strip():
            console.print(Panel(result["stdout"], title="Standard Output", border_style="green"))
        
        if "result" in result:
            import json
            if isinstance(result["result"], (dict, list)):
                result_str = json.dumps(result["result"], indent=2)
            else:
                result_str = str(result["result"])
            
            console.print(Panel(result_str, title="Result", border_style="cyan"))
        
        if "error" in result:
            console.print(Panel(result["error"], title="Error", border_style="red"))
            if "traceback" in result:
                console.print(Panel(result["traceback"], title="Traceback", border_style="red"))
    
    elif step_type_str == PlanStepType.FILE.value:
        # Show file operation details
        console.print(f"[bold]File Path:[/bold] {result.get('file_path', '')}")
        operation = "read/write" # Default operation
        if plan and step_id in plan.steps:
            step_details = plan.steps.get(step_id)
            if step_details:
                operation = getattr(step_details, 'operation', 'read/write')
        console.print(f"[bold]Operation:[/bold] {operation}")
        
        if "content" in result:
            # For read operations
            content = result["content"]
            if len(content) > 500:
                content = content[:500] + "...\n(truncated)"
            
            syntax = Syntax(
                content,
                "text", # Assuming text, could be improved if file type is known
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            console.print(Panel(syntax, title="File Content", border_style="green"))
        
        if "message" in result:
            console.print(f"[bold]Result:[/bold] {result['message']}")
    
    elif step_type_str == PlanStepType.DECISION.value:
        # Show decision details
        console.print(f"[bold]Condition:[/bold] {result.get('condition', '')}")
        condition_result = result.get("condition_result", False)
        console.print(f"[bold]Evaluated:[/bold] {'[green]True[/green]' if condition_result else '[red]False[/red]'}")
        
        if plan and step_id in plan.steps:
            step = plan.steps.get(step_id)
            if step:
                if condition_result and step.true_branch:
                    console.print(f"[bold]True Branch taken:[/bold] {', '.join(step.true_branch)}")
                elif not condition_result and step.false_branch:
                    console.print(f"[bold]False Branch taken:[/bold] {', '.join(step.false_branch)}")
    
    elif step_type_str == PlanStepType.API.value:
        # Show API call details
        console.print(f"[bold]URL:[/bold] {result.get('url', '')}")
        console.print(f"[bold]Method:[/bold] {result.get('method', 'GET')}")
        console.print(f"[bold]Status Code:[/bold] {result.get('status_code', 0)}")
        
        # Show headers
        if "headers" in result and isinstance(result["headers"], dict):
            header_table = Table(title="Response Headers", box=box.SIMPLE)
            header_table.add_column("Header", style="cyan")
            header_table.add_column("Value", style="green")
            
            for header, value in result["headers"].items():
                header_table.add_row(header, str(value))
            
            console.print(header_table)
        
        # Show JSON response if available
        if "json" in result:
            import json
            json_str = json.dumps(result["json"], indent=2)
            
            syntax = Syntax(
                json_str,
                "json",
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            console.print(Panel(syntax, title="JSON Response", border_style="green"))
        elif "text" in result:
            # Show text response
            text = result["text"]
            
            # Try to detect content type
            is_json_like = text.strip().startswith('{') and text.strip().endswith('}')
            is_xml_like = text.strip().startswith('<') and text.strip().endswith('>')
            is_html_like = '<html' in text.lower() and '</html>' in text.lower()
            
            syntax_type = "json" if is_json_like else "xml" if is_xml_like or is_html_like else "text"
            
            syntax = Syntax(
                text,
                syntax_type,
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            console.print(Panel(syntax, title="Response Body", border_style="green"))
    
    elif step_type_str == PlanStepType.LOOP.value:
        # Show loop details
        loop_items_desc = ""
        if plan and step_id in plan.steps:
            step_details = plan.steps.get(step_id)
            if step_details:
                loop_items_desc = getattr(step_details, 'loop_items', '')
        console.print(f"[bold]Loop Items Description:[/bold] {loop_items_desc}")
        console.print(f"[bold]Iterations Executed:[/bold] {result.get('iterations', 0)}")
        
        if "loop_results" in result and isinstance(result["loop_results"], list):
            loop_results = result["loop_results"]
            
            # Create a table for iteration results
            loop_table = Table(title="Loop Iterations", box=box.SIMPLE)
            loop_table.add_column("Index", style="cyan")
            loop_table.add_column("Item", style="green")
            loop_table.add_column("Status", style="yellow")
            
            for iteration in loop_results:
                if not isinstance(iteration, dict): continue # Skip malformed iteration results

                # Format item based on type
                item = iteration.get("item", "")
                if isinstance(item, (dict, list)):
                    import json
                    item_str = json.dumps(item)
                    if len(item_str) > 30:
                        item_str = item_str[:27] + "..."
                else:
                    item_str = str(item)
                    if len(item_str) > 30:
                        item_str = item_str[:27] + "..."
                
                # Format status
                status = "[green]Success[/green]" if iteration.get("success", False) else "[red]Failed[/red]"
                
                loop_table.add_row(
                    str(iteration.get("index", "?")), # Use '?' if index is missing
                    item_str,
                    status
                )
            
            if loop_table.rows:
                console.print(loop_table)
            else:
                console.print("[italic]No iteration results to display.[/italic]")
        else:
            console.print("[italic]No loop iteration results available.[/italic]")
    else:
        # Fallback for unknown or unhandled step types
        console.print(f"[yellow]Details for step type '{step_type_str}' are not specifically formatted.[/yellow]")
        # Generic display of result dictionary for debugging
        import json
        try:
            result_dump = json.dumps(result, indent=2, default=str) # Use default=str for non-serializable items
            console.print(Panel(result_dump, title=f"Raw Result Data for Step {step_id}", border_style="yellow"))
        except Exception as e:
            console.print(f"[red]Could not serialize raw result data: {e}[/red]")
            

async def display_step_error(
    step_id: str,
    error: str,
    step_type: str,
    description: str
) -> None:
    """
    Display an error that occurred during step execution.
    
    Args:
        step_id: ID of the failed step
        error: Error message
        step_type: Type of the step
        description: Step description
    """
    error_panel = Panel(
        f"[bold]{description}[/bold]\n\n"
        f"Step Type: {step_type}\n"
        f"Error: {error}",
        title=f"Step Error: {step_id}",
        border_style="red"
    )
    console.print(error_panel)

# Add the new methods to terminal_formatter
terminal_formatter.display_advanced_plan = display_advanced_plan
terminal_formatter.display_execution_results = display_execution_results
terminal_formatter.display_step_details = display_step_details
terminal_formatter.display_step_error = display_step_error


logger.info("Extended terminal formatter with advanced task plan display capabilities")
