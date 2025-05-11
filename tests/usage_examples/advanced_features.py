# tests/usage_examples/advanced_features.py

def test_code_generation():
    """EXAMPLE: Code generation
    DESCRIPTION: Angela can generate code based on natural language descriptions.
    COMMAND: create a Python function that calculates the factorial of a number
    RESULT:
    Creating factorial.py with the following content:
    
    ```python
    def factorial(n):
        \"\"\"
        Calculate the factorial of a number.
        
        Args:
            n: A non-negative integer
            
        Returns:
            The factorial of n (n!)
        \"\"\"
        if n < 0:
            raise ValueError("Factorial is not defined for negative numbers")
        if n == 0 or n == 1:
            return 1
        else:
            return n * factorial(n - 1)
            
    if __name__ == "__main__":
        import sys
        if len(sys.argv) > 1:
            try:
                n = int(sys.argv[1])
                print(f"The factorial of {n} is {factorial(n)}")
            except ValueError as e:
                print(f"Error: {e}")
        else:
            print("Usage: python factorial.py [number]")
    ```
    
    File created successfully!
    """
    pass

def test_docker_integration():
    """EXAMPLE: Docker integration
    DESCRIPTION: Angela can help manage Docker containers and images.
    COMMAND: show running docker containers
    RESULT:
    Executing command: docker ps
    
    CONTAINER ID   IMAGE                  COMMAND                  STATUS          PORTS                    NAMES
    a8f6d3e21b9c   postgres:13            "docker-entrypoint.s…"   Up 2 hours      0.0.0.0:5432->5432/tcp   db
    b7c59e8a3d1f   redis:alpine           "docker-entrypoint.s…"   Up 2 hours      0.0.0.0:6379->6379/tcp   cache
    12d34f56e78g   my-app:latest          "gunicorn app:app"       Up 30 minutes   0.0.0.0:8000->8000/tcp   web
    """
    pass

def test_content_analysis():
    """EXAMPLE: Content analysis and refactoring
    DESCRIPTION: Angela can analyze and refactor code based on best practices.
    COMMAND: refactor the authentication module to use JWT
    RESULT:
    Analyzing authentication module...
    
    I'll refactor auth.py to use JWT instead of session-based authentication.
    Changes include:
    
    1. Add JWT dependencies
    2. Modify login route to return tokens
    3. Create token validation middleware
    4. Update protected routes
    
    Refactoring 3 files:
    - auth.py
    - middleware.py
    - routes.py
    
    Show detailed changes? [Y/n]: 
    """
    pass

def test_project_generation():
    """EXAMPLE: Full project generation
    DESCRIPTION: Angela can create entire project structures based on high-level descriptions.
    COMMAND: create a new Flask REST API project with user authentication and SQLite database
    RESULT:
    Creating Flask REST API project with authentication and SQLite...
    
    Generated project structure:
    flask_api/
    ├── app/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── user.py
    │   ├── routes/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   └── api.py
    │   └── utils/
    │       ├── __init__.py
    │       └── auth_utils.py
    ├── instance/
    ├── tests/
    │   ├── __init__.py
    │   ├── test_auth.py
    │   └── test_api.py
    ├── requirements.txt
    ├── .gitignore
    ├── README.md
    └── run.py
    
    Project created successfully! Would you like me to:
    1. Initialize Git repository
    2. Create virtual environment
    3. Install dependencies
    """
    pass
