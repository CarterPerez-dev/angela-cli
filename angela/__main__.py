# angela/__main__.py 
"""
Entry point for Angela CLI.
"""
from angela.components.cli import app
from angela import init_application

if __name__ == "__main__":
    # Initialize all application components
    init_application()
    
    # CLI application
    app()
