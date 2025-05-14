# angela/utils/command_utils.py
"""Utility functions for command processing."""

from typing import Tuple

# Interactive command detection
INTERACTIVE_COMMANDS = [
    "vim", "vi", "nano", "emacs", "pico", "less", "more", 
    "top", "htop", "btop", "iotop", "iftop", "nmon", "glances", "atop",
    "ping", "traceroute", "mtr", "tcpdump", "wireshark", "tshark", "ngrep",
    "tail", "watch", "journalctl", "dmesg", "ssh", "telnet", "nc", "netcat",
    "mysql", "psql", "sqlite3", "mongo", "redis-cli", "gdb", "lldb", "pdb",
    "tmux", "screen"
]

def is_interactive_command(command: str) -> Tuple[bool, str]:
    """
    Check if a command is interactive (taking over the terminal).
    
    Args:
        command: The command to check
        
    Returns:
        Tuple of (is_interactive, base_command)
    """
    base_cmd = command.split()[0] if command.split() else ""
    
    # Base check for common interactive commands
    is_interactive = base_cmd in INTERACTIVE_COMMANDS
    
    # Special cases with flags
    if not is_interactive:
        if base_cmd == "ping" and "-c" not in command:
            is_interactive = True
        elif base_cmd == "tail" and "-f" in command:
            is_interactive = True
        elif base_cmd == "journalctl" and "-f" in command:
            is_interactive = True
        elif base_cmd == "watch":
            is_interactive = True
    
    return (is_interactive, base_cmd)



def display_command_recommendation(command: str) -> None:
    """
    Display a recommendation for interactive commands.
    
    Args:
        command: The interactive command
    """
    from rich.console import Console
    from rich.panel import Panel
    from angela.components.shell.formatter import COLOR_PALETTE, DEFAULT_BOX
    console = Console()
    
    base_cmd = command.split()[0] if command.split() else ""
    
    # Create a recommendation message
    recommendation = f"""
[bold red]Angela doesn't execute terminal-interactive commands like {base_cmd}[/bold red]
[bold red]You can run this command yourself by typing: [/bold red]

    [bold green]► {command} ◄[/bold green]

[bold cyan]This will launch » {base_cmd} « in your terminal[/bold cyan]
"""
    
    # Print the recommendation
    console.print(Panel(
        recommendation,
        title="[bold cyan]Command Recommendation[/bold cyan]",
        border_style=COLOR_PALETTE["border"],
        box=DEFAULT_BOX,
        expand=False
    ))
