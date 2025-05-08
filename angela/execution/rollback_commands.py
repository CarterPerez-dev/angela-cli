# angela/cli/rollback_commands.py
"""
CLI commands for enhanced rollback functionality.
"""
import asyncio
import typer
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rich_print
from rich.prompt import Confirm
from rich.syntax import Syntax

from angela.execution.rollback import rollback_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(help="Rollback commands for undoing operations")

@app.command("list", help="List recent operations that can be rolled back")
def list_operations(
    limit: int = typer.Option(10, help="Maximum number of operations to show"),
    transactions: bool = typer.Option(False, help="Show transactions instead of individual operations")
):
    """List recent operations or transactions that can be rolled back."""
    if transactions:
        # Show transactions
        transaction_list = asyncio.run(rollback_manager.get_recent_transactions(limit))
        
        if not transaction_list:
            console.print("[yellow]No transactions found.[/yellow]")
            return
        
        # Create a table for the transactions
        table = Table(title="Recent Transactions")
        table.add_column("ID", style="cyan")
        table.add_column("Timestamp", style="green")
        table.add_column("Description", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Operations", style="blue")
        table.add_column("Can Rollback", style="red")
        
        # Add rows for each transaction
        for transaction in transaction_list:
            table.add_row(
                transaction["id"],
                transaction["timestamp"],
                transaction["description"],
                transaction["status"],
                str(transaction["operation_count"]),
                "✓" if transaction["can_rollback"] else "✗"
            )
        
        # Display the table
        console.print(table)
        
        # Show usage hint
        console.print("\n[bold]Use the following command to roll back a transaction:[/bold]")
        console.print("  [blue]angela rollback transaction <ID>[/blue]")
    
    else:
        # Show individual operations
        operation_list = asyncio.run(rollback_manager.get_recent_operations(limit))
        
        if not operation_list:
            console.print("[yellow]No operations found.[/yellow]")
            return
        
        # Create a table for the operations
        table = Table(title="Recent Operations")
        table.add_column("ID", style="cyan")
        table.add_column("Timestamp", style="green")
        table.add_column("Type", style="white")
        table.add_column("Description", style="blue")
        table.add_column("Can Rollback", style="red")
        table.add_column("Transaction", style="yellow")
        
        # Add rows for each operation
        for operation in operation_list:
            transaction_info = operation.get("transaction")
            transaction_desc = f"{transaction_info['description']} ({transaction_info['status']})" if transaction_info else "None"
            
            table.add_row(
                str(operation["id"]),
                operation["timestamp"],
                operation["operation_type"],
                operation["description"],
                "✓" if operation["can_rollback"] else "✗",
                transaction_desc
            )
        
        # Display the table
        console.print(table)
        
        # Show usage hint
        console.print("\n[bold]Use the following command to roll back an operation:[/bold]")
        console.print("  [blue]angela rollback operation <ID>[/blue]")


@app.command("operation", help="Roll back a specific operation")
def rollback_operation(
    operation_id: int = typer.Argument(..., help="ID of the operation to roll back"),
    force: bool = typer.Option(False, help="Skip confirmation prompt")
):
    """Roll back a specific operation by ID."""
    # Get operation details
    operation_list = asyncio.run(rollback_manager.get_recent_operations(100))
    
    # Find the operation
    operation = None
    for op in operation_list:
        if op["id"] == operation_id:
            operation = op
            break
    
    if not operation:
        console.print(f"[red]Operation with ID {operation_id} not found.[/red]")
        return
    
    # Check if the operation can be rolled back
    if not operation["can_rollback"]:
        console.print("[red]This operation cannot be rolled back.[/red]")
        return
    
    # Display operation details
    console.print(Panel(
        f"[bold]Type:[/bold] {operation['operation_type']}\n"
        f"[bold]Description:[/bold] {operation['description']}\n"
        f"[bold]Timestamp:[/bold] {operation['timestamp']}",
        title="Operation Details",
        expand=False
    ))
    
    # Get confirmation
    if not force and not Confirm.ask("Are you sure you want to roll back this operation?"):
        console.print("[yellow]Rollback cancelled.[/yellow]")
        return
    
    # Execute the rollback
    with console.status("[bold green]Rolling back operation...[/bold green]"):
        success = asyncio.run(rollback_manager.rollback_operation(operation_id))
    
    # Show the result
    if success:
        console.print("[green]Operation successfully rolled back.[/green]")
    else:
        console.print("[red]Failed to roll back operation.[/red]")


@app.command("transaction", help="Roll back an entire transaction")
def rollback_transaction(
    transaction_id: str = typer.Argument(..., help="ID of the transaction to roll back"),
    force: bool = typer.Option(False, help="Skip confirmation prompt")
):
    """Roll back all operations in a transaction."""
    # Get transaction details
    transaction_list = asyncio.run(rollback_manager.get_recent_transactions(100))
    
    # Find the transaction
    transaction = None
    for tx in transaction_list:
        if tx["id"] == transaction_id:
            transaction = tx
            break
    
    if not transaction:
        console.print(f"[red]Transaction with ID {transaction_id} not found.[/red]")
        return
    
    # Check if the transaction can be rolled back
    if not transaction["can_rollback"]:
        console.print("[red]This transaction cannot be rolled back.[/red]")
        return
    
    # Display transaction details
    console.print(Panel(
        f"[bold]Description:[/bold] {transaction['description']}\n"
        f"[bold]Status:[/bold] {transaction['status']}\n"
        f"[bold]Timestamp:[/bold] {transaction['timestamp']}\n"
        f"[bold]Operation count:[/bold] {transaction['operation_count']}",
        title="Transaction Details",
        expand=False
    ))
    
    # Get confirmation
    if not force and not Confirm.ask("Are you sure you want to roll back this entire transaction?"):
        console.print("[yellow]Rollback cancelled.[/yellow]")
        return
    
    # Execute the rollback
    with console.status("[bold green]Rolling back transaction...[/bold green]"):
        result = asyncio.run(rollback_manager.rollback_transaction(transaction_id))
    
    # Show the result
    if result["success"]:
        console.print(f"[green]Transaction successfully rolled back. {result['rolled_back']} operations reverted.[/green]")
    else:
        console.print(f"[red]Transaction rollback failed or partially succeeded. "
                     f"{result['rolled_back']} operations reverted, {result['failed']} operations failed.[/red]")
        
        # Show details of failed operations
        if result["failed"] > 0 and "results" in result:
            failed_ops = [r for r in result["results"] if not r["success"]]
            
            if failed_ops:
                console.print("\n[bold]Failed operations:[/bold]")
                for op in failed_ops:
                    console.print(f"- ID {op['operation_id']}: {op['description']} - {op.get('error', 'Unknown error')}")


@app.command("last", help="Roll back the most recent operation or transaction")
def rollback_last(
    transaction: bool = typer.Option(False, help="Roll back the last transaction instead of the last operation"),
    force: bool = typer.Option(False, help="Skip confirmation prompt")
):
    """Roll back the most recent operation or transaction."""
    if transaction:
        # Get the most recent transaction
        transactions = asyncio.run(rollback_manager.get_recent_transactions(1))
        
        if not transactions:
            console.print("[yellow]No transactions found.[/yellow]")
            return
        
        # Use the first (most recent) transaction
        transaction_id = transactions[0]["id"]
        
        # Call the rollback_transaction function
        rollback_transaction(transaction_id, force)
    else:
        # Get the most recent operation
        operations = asyncio.run(rollback_manager.get_recent_operations(1))
        
        if not operations:
            console.print("[yellow]No operations found.[/yellow]")
            return
        
        # Use the first (most recent) operation
        operation_id = operations[0]["id"]
        
        # Call the rollback_operation function
        rollback_operation(operation_id, force)


# To be used for integration with the main CLI
def register_commands(parent_app: typer.Typer):
    """Register rollback commands with a parent Typer app."""
    parent_app.add_typer(app, name="rollback", help="Commands for rolling back operations")
