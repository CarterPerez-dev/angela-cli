Usage Guide
===========

Basic Syntax
-----------

Angela CLI uses a simple, consistent syntax:

.. code-block:: bash

    angela [options] "your request in natural language"

Common options include:

* ``--dry-run``: Preview commands without executing them
* ``--debug``: Show detailed debug information
* ``--no-color``: Disable colored output
* ``--version``: Show Angela CLI version

Command Categories
----------------

Angela CLI can handle a wide variety of requests across different categories:

File Operations
~~~~~~~~~~~~~

Angela can create, delete, find, and modify files:

.. code-block:: bash

    # Create files
    angela "create a new file called config.js with basic configuration"
    
    # Find files
    angela "find all Python files containing the word 'authenticate'"
    
    # Modify files
    angela "replace all occurrences of 'userService' with 'authService' in src/auth/"
    
    # Read files
    angela "show me the content of the main configuration file"

Shell Commands
~~~~~~~~~~~~

Angela can execute shell commands based on natural language descriptions:

.. code-block:: bash

    # System information
    angela "how much disk space do I have left"
    
    # Process management
    angela "show me all running node processes"
    
    # Network operations
    angela "check if port 3000 is in use"
    
    # File compression
    angela "create a zip archive of the src directory"

Project Context
~~~~~~~~~~~~~

Angela analyzes your project to provide contextual assistance:

.. code-block:: bash

    # Project information
    angela "what dependencies does this project use"
    
    # Framework detection
    angela "what framework is this project using"
    
    # File navigation
    angela "open the main app entry point"
    
    # Add dependencies
    angela "add a logger library to this project"

Version Control (Git)
~~~~~~~~~~~~~~~~~~~

Angela provides intuitive Git operations:

.. code-block:: bash

    # Status and history
    angela "what files have I changed"
    angela "show me the commit history for this file"
    
    # Branching
    angela "create a new branch and switch to it"
    angela "merge the feature branch into main"
    
    # Stashing
    angela "stash my changes temporarily"
    
    # Remote operations
    angela "push my changes to the remote repository"

Docker Operations
~~~~~~~~~~~~~~~

Angela can help manage Docker containers and images:

.. code-block:: bash

    # Container management
    angela "list all running containers"
    angela "stop the database container"
    
    # Image operations
    angela "build a Docker image from the current directory"
    
    # Docker Compose
    angela "start all services defined in docker-compose.yml"
    
    # Dockerfile generation
    angela "create a Dockerfile for a Node.js application"

Multi-Step Workflows
------------------

For complex tasks, Angela breaks operations into steps:

.. code-block:: bash

    angela "create a feature branch, add a new component, and commit the changes"

Angela will:
1. Show you the plan with discrete steps
2. Ask for confirmation before proceeding
3. Execute each step in sequence
4. Report on the success of each step

If a step fails, Angela will:
1. Show the error message
2. Suggest possible fixes
3. Offer options to retry, modify, or skip the step
4. Provide the option to roll back completed steps

Defining Custom Workflows
----------------------

You can define custom workflows for repeated tasks:

.. code-block:: bash

    # Define a workflow
    angela "define a workflow called deploy that runs tests, builds the app, and uploads to the server"
    
    # Run with parameters
    angela "run the deploy workflow with environment=production"
    
    # List available workflows
    angela "show me all my workflows"
    
    # Delete a workflow
    angela "delete the deploy workflow"

Safety Features
-------------

Angela includes several safety features:

Risk Assessment
~~~~~~~~~~~~~

Commands are classified by risk level:
* **Low**: Informational commands (ls, find, etc.)
* **Medium**: File modifications with limited scope
* **High**: Destructive operations with broader scope
* **Critical**: System-level changes with potential for data loss

Higher-risk commands require explicit confirmation.

Command Preview
~~~~~~~~~~~~~

Use ``--dry-run`` to preview commands:

.. code-block:: bash

    angela --dry-run "delete all log files"

Automatic Backups
~~~~~~~~~~~~~~~

Angela automatically backs up files before modifying them:

.. code-block:: bash

    # View backup history
    angela "show recent backups"
    
    # Restore from backup
    angela "restore the last version of config.js"

Transaction Rollback
~~~~~~~~~~~~~~~~~

Multi-step operations are tracked as transactions:

.. code-block:: bash

    # View recent transactions
    angela "show recent transactions"
    
    # Rollback a transaction
    angela "rollback the last transaction"
    
    # Rollback a specific transaction
    angela "rollback transaction abc123"

Advanced Usage
------------

For advanced users, Angela offers additional capabilities:

Code Generation
~~~~~~~~~~~~~

Angela can generate code based on your specifications:

.. code-block:: bash

    angela "create a Python function to calculate Fibonacci numbers"
    angela "generate a React component for a user profile page"

Project Scaffolding
~~~~~~~~~~~~~~~~

Create entire project structures:

.. code-block:: bash

    angela "create a new Express API project with MongoDB integration"

Customization
~~~~~~~~~~~

Customize Angela's behavior:

.. code-block:: bash

    angela "set my preferred language to TypeScript"
    angela "always use yarn instead of npm for Node.js projects"
