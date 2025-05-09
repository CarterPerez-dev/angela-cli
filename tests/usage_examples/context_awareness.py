# tests/usage_examples/context_awareness.py

def test_project_detection():
    """EXAMPLE: Project detection
    DESCRIPTION: Angela can automatically detect your project type and structure.
    COMMAND: what kind of project is this
    RESULT:
    This appears to be a Python project.
    
    Project root: /home/user/projects/my-app
    Structure:
    - 42 Python files
    - Main directories: src, tests, docs
    - Dependencies: flask, pytest, requests
    - Framework: Flask (web application)
    """
    pass

def test_file_references():
    """EXAMPLE: Natural file references
    DESCRIPTION: Refer to files using natural language instead of exact paths.
    COMMAND: show me the main file of this project
    RESULT:
    Resolving "main file" to: src/app.py
    
    ```python
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return "Hello, world!"
    
    if __name__ == '__main__':
        app.run(debug=True)
    ```
    """
    pass

def test_recent_files():
    """EXAMPLE: Recent file history
    DESCRIPTION: Angela keeps track of files you've worked with recently.
    COMMAND: show my recently modified files
    RESULT:
    Recently modified files:
    
    1. src/models/user.py (2 minutes ago)
    2. tests/test_auth.py (15 minutes ago)
    3. config.yml (35 minutes ago)
    4. requirements.txt (1 hour ago)
    """
    pass

def test_dependency_detection():
    """EXAMPLE: Dependency detection
    DESCRIPTION: Angela understands your project dependencies.
    COMMAND: what libraries am I using in this project
    RESULT:
    Dependencies in this Python project:
    
    Runtime dependencies:
    - flask==2.0.1: Web framework
    - sqlalchemy==1.4.23: ORM for database access
    - pyjwt==2.1.0: JWT authentication
    
    Development dependencies:
    - pytest==6.2.5: Testing framework
    - flake8==3.9.2: Linting
    
    Would you like me to check for outdated packages?
    """
    pass
