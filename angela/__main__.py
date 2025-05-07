# angela/__main__.py 
"""
Entry point for Angela CLI.
"""
from angela.cli import app
from angela import init_application

if __name__ == "__main__":
    # Initialize all application components
    init_application()
    
    # Start the CLI application
    app()
