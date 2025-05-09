Examples
========

This page provides more detailed examples of how to use Angela CLI for various tasks.

Basic File Operations
-------------------

Working with files and directories is a common task. Angela CLI makes it easy with natural language commands.

Creating Files
~~~~~~~~~~~~

.. code-block:: bash

    angela "create a new file called config.json with a basic empty JSON structure"

This will create a file with content like:

.. code-block:: json

    {
      
    }

Finding Files
~~~~~~~~~~~

.. code-block:: bash

    angela "find all JavaScript files modified in the last week"

This translates to a command like:

.. code-block:: bash

    find . -name "*.js" -mtime -7 -type f

Creating Directory Structures
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "create a project structure with src, test, and docs directories"

This creates the appropriate directory structure with a single command.

Version Control (Git)
-------------------

Angela CLI provides an intuitive interface to Git commands.

Repository Status
~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "what's the status of my git repo"

Viewing Changes
~~~~~~~~~~~~~

.. code-block:: bash

    angela "show me what changes I've made to the auth module"

Creating Feature Branches
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "create a new feature branch called user-profile based on the develop branch"

Interactive Staging
~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "help me stage specific changes to user.js"

Angela CLI will help you interactively select which changes to stage.

Stashing Changes
~~~~~~~~~~~~~~

.. code-block:: bash

    angela "stash my changes with a descriptive message"

Remote Operations
~~~~~~~~~~~~~~

.. code-block:: bash

    angela "push my changes to the remote and set up tracking"

Advanced Git
~~~~~~~~~~

.. code-block:: bash

    angela "find which commit introduced a bug in the login functionality"

Multi-Step Workflows
------------------

Angela CLI excels at breaking down complex tasks into sequences of steps.

Project Setup
~~~~~~~~~~~

.. code-block:: bash

    angela "set up a new React project, initialize git, add linting config, and make an initial commit"

Feature Development
~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "create a feature branch, implement a user profile component, test it, and commit the changes"

Database Schema Updates
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "create a migration to add user preferences table, run it, and update the models"

Deployment Sequence
~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "prepare for release by updating version number, creating a tag, building the app, and pushing to production"

Docker Integration
----------------

Angela CLI can help you work with Docker more effectively.

Container Management
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "show me all my running containers"
    angela "restart the database container"
    angela "view logs for the web container"

Building Images
~~~~~~~~~~~~~

.. code-block:: bash

    angela "build a Docker image for this Node application"

Docker Compose
~~~~~~~~~~~~

.. code-block:: bash

    angela "start the development environment with Docker Compose"
    angela "rebuild just the backend service"

Dockerfile Generation
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "create a Dockerfile for this Python application"

Code Generation
-------------

Angela CLI can generate code snippets and even entire components.

Functions and Methods
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "create a JavaScript function that validates email addresses"

Classes and Components
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "generate a React component for a user settings form"

API Endpoints
~~~~~~~~~~~

.. code-block:: bash

    angela "create an Express route handler for user authentication"

Configuration Files
~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "generate a webpack config for a React project with SASS support"

Safety and Rollbacks
------------------

Angela CLI includes powerful safety features to protect you from mistakes.

Previewing Commands
~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela --dry-run "delete all temporary files"

This shows what would happen without actually executing the command.

Backing Up Files
~~~~~~~~~~~~~~

.. code-block:: bash

    angela "safely update the database configuration file"

Angela automatically creates backups before making changes.

Viewing Backup History
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "show me recent backups"

Rolling Back Changes
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "rollback the changes I just made to config.js"

Transaction Rollback
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "rollback the last multistep operation"

This restores all files changed in a multi-step operation.

Developer Tools Integration
-------------------------

Angela CLI integrates with various developer tools.

Package Management
~~~~~~~~~~~~~~~

.. code-block:: bash

    angela "add express and cors to dependencies"
    angela "update all outdated packages"

Testing
~~~~~

.. code-block:: bash

    angela "run tests for the auth module"
    angela "generate unit tests for the user model"

Build Tools
~~~~~~~~~

.. code-block:: bash

    angela "build the project in production mode"
    angela "clean and rebuild the project"

Deployment
~~~~~~~~

.. code-block:: bash

    angela "deploy the application to staging"
    angela "roll back the last deployment"
