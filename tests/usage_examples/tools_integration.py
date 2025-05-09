# tests/usage_examples/tools_integration.py

def test_git_integration():
    """EXAMPLE: Advanced Git operations
    DESCRIPTION: Angela understands Git workflows and can help with complex Git operations.
    COMMAND: squash my last 3 commits into one with the message "Implement user authentication"
    RESULT:
    Executing Git operation:
    1. Identifying the last 3 commits...
    2. Performing interactive rebase...
    
    The following commits will be squashed:
    a1b2c3d - Add login form
    e4f5g6h - Implement authentication backend
    i7j8k9l - Fix login redirect issue
    
    Executing: git reset --soft HEAD~3 && git commit -m "Implement user authentication"
    
    ✓ Successfully squashed 3 commits into one
    """
    pass

def test_package_management():
    """EXAMPLE: Package management help
    DESCRIPTION: Angela can help you manage dependencies across different package managers.
    COMMAND: add jwt authentication to this project
    RESULT:
    I'll add JWT authentication to your Node.js project.
    
    Installing required packages:
    $ npm install jsonwebtoken passport passport-jwt
    
    Added dependencies to package.json:
    ```json
    "dependencies": {
      // existing dependencies...
      "jsonwebtoken": "^9.0.0",
      "passport": "^0.6.0",
      "passport-jwt": "^4.0.1"
    }
    ```
    
    Creating auth configuration...
    Would you like me to create example JWT implementation files? [Y/n]:
    """
    pass

def test_database_operations():
    """EXAMPLE: Database operations help
    DESCRIPTION: Angela can assist with database-related tasks.
    COMMAND: create a migration to add email column to users table
    RESULT:
    Detected SQLAlchemy with Alembic in your Flask application.
    
    Creating migration to add email column to users table:
    $ flask db migrate -m "Add email column to users table"
    
    Generated migration:
    ```python
    # migrations/versions/a1b2c3d4e5f6_add_email_column_to_users_table.py
    
    def upgrade():
        op.add_column('users', sa.Column('email', sa.String(length=120), nullable=True))
        
    def downgrade():
        op.drop_column('users', 'email')
    ```
    
    Apply this migration? [Y/n]:
    """
    pass

def test_ci_cd_integration():
    """EXAMPLE: CI/CD setup assistance
    DESCRIPTION: Angela can help set up continuous integration and deployment.
    COMMAND: set up GitHub Actions CI for my Python project
    RESULT:
    Creating GitHub Actions workflow for Python project.
    
    File: .github/workflows/python-app.yml
    ```yaml
    name: Python application
    
    on:
      push:
        branches: [ main ]
      pull_request:
        branches: [ main ]
    
    jobs:
      build:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: [3.8, 3.9, 3.10]
        
        steps:
        - uses: actions/checkout@v3
        - name: Set up Python ${{ matrix.python-version }}
          uses: actions/setup-python@v4
          with:
            python-version: ${{ matrix.python-version }}
        - name: Install dependencies
          run: |
            python -m pip install --upgrade pip
            pip install flake8 pytest
            if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
        - name: Lint with flake8
          run: |
            flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        - name: Test with pytest
          run: |
            pytest
    ```
    
    Configuration created successfully!
    """
    pass
