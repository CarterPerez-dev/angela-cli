"""
Command-line interface module for Angela CLI.
"""

from angela.cli.main import app
from angela.cli.files import app as files_app
from angela.cli.workflows import app as workflows_app

# Add subcommands
app.add_typer(files_app, name="files", help="File operations")
app.add_typer(workflows_app, name="workflows", help="Workflow management")
