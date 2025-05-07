# angela/cli/__init__.py
"""
CLI components for Angela CLI.
"""
from angela.cli.main import app as main_app
from angela.cli.files import app as files_app
from angela.cli.workflows import app as workflows_app
from angela.cli.generation import app as generation_app

# Add subcommands to the main app
main_app.add_typer(files_app, name="files", help="File and directory operations")
main_app.add_typer(workflows_app, name="workflows", help="Workflow management")
main_app.add_typer(generation_app, name="generate", help="Code generation")

# Export the main app
app = main_app
