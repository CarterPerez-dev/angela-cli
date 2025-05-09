Quickstart
==========

Getting Started
--------------

After installing Angela CLI, you can start using it right away. The basic syntax is:

.. code-block:: bash

    angela "your request in natural language"

For example:

.. code-block:: bash

    angela "list all files in the current directory"

This will translate your request into the appropriate shell command (in this case, ``ls -la``) and execute it.

Basic Command Examples
--------------------

Here are some simple commands to get you started:

File Operations
~~~~~~~~~~~~~~

.. code-block:: bash

    # List files
    angela "show me all JavaScript files in this directory"
    
    # Create files and directories
    angela "create a new directory called 'src' with subdirectories for 'models', 'views', and 'controllers'"
    
    # Find files
    angela "find all files modified in the last 24 hours"

Git Operations
~~~~~~~~~~~~

.. code-block:: bash

    # Check status
    angela "what's the status of my git repository"
    
    # Create branches
    angela "create a new branch called feature/user-auth and switch to it"
    
    # Commit changes
    angela "commit all changes with a message explaining what I did"

Project Management
~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Project information
    angela "what kind of project is this"
    
    # Dependencies
    angela "add express and mongoose to this Node.js project"
    
    # Generate code
    angela "create a basic REST API endpoint for user authentication"

Using the --dry-run Flag
----------------------

To see what commands Angela would execute without actually running them, use the ``--dry-run`` flag:

.. code-block:: bash

    angela --dry-run "delete all temporary files in this directory"

This will show you the command that would be executed, allowing you to verify it before actual execution.

Multi-Step Workflows
------------------

Angela can handle complex, multi-step workflows:

.. code-block:: bash

    angela "create a new React component called UserProfile, add it to the components directory, and import it in the main App.js file"

Angela will break this down into individual steps, showing you the plan before executing it.

Defining Reusable Workflows
-------------------------

You can define workflows for tasks you perform repeatedly:

.. code-block:: bash

    angela "define a workflow called deploy that builds the app, runs tests, and pushes to production"

And then run them:

.. code-block:: bash

    angela "run the deploy workflow"

Getting Help
----------

If you need help with Angela CLI, try:

.. code-block:: bash

    angela "help"
    angela "show me examples of file operations"
    angela "what can you do with git?"

Advanced Usage
------------

For more advanced usage, check out the detailed guides on:

- :ref:`Workflows <workflows>`
- :ref:`Tool Integrations <tool-integrations>`
- :ref:`Safety Features <safety-features>`
- :ref:`Code Generation <code-generation>`

Next Steps
---------

After getting familiar with the basics, explore:

1. :ref:`Context Awareness <context-awareness>` - How Angela understands your project
2. :ref:`Safety Features <safety-features>` - Protecting you from risky operations
3. :ref:`Workflows <workflows>` - Creating reusable sequences of operations
