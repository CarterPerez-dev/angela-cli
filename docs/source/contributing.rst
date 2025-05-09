Contributing
============

We welcome contributions to Angela CLI! This guide will help you get started with the development process.

Setting Up Development Environment
--------------------------------

1. Clone the repository:

   .. code-block:: bash

       git clone https://github.com/your-repo/angela-cli.git
       cd angela-cli

2. Install development dependencies:

   .. code-block:: bash

       make dev-setup

   This will install Angela CLI in editable mode with all development dependencies.

3. Set up your API key:

   .. code-block:: bash

       echo "GEMINI_API_KEY=your_api_key_here" > .env

4. Run tests to verify your setup:

   .. code-block:: bash

       make test

Project Structure
---------------

The Angela CLI project is organized into several key components:

- ``angela/ai/``: AI integration with LLMs (Gemini API)
- ``angela/cli/``: Command-line interface definition
- ``angela/context/``: Context management and project awareness
- ``angela/execution/``: Command execution and safety features
- ``angela/generation/``: Code generation capabilities
- ``angela/intent/``: Intent analysis and planning
- ``angela/safety/``: Safety checks and risk assessment
- ``angela/shell/``: Shell integration scripts
- ``angela/toolchain/``: Integration with development tools
- ``angela/workflows/``: Workflow definition and execution
- ``tests/``: Test suite

Development Workflow
------------------

1. **Create a branch**: Create a new branch for your changes:

   .. code-block:: bash

       git checkout -b feature/your-feature-name

2. **Make changes**: Implement your changes, following the coding standards.

3. **Add tests**: Add tests for your changes, including usage examples in ``tests/usage_examples/``.

4. **Run tests**: Ensure all tests pass:

   .. code-block:: bash

       make test

5. **Format code**: Format your code using our formatting tools:

   .. code-block:: bash

       make format

6. **Lint code**: Check for code quality issues:

   .. code-block:: bash

       make lint

7. **Submit a pull request**: Push your branch and create a pull request.

Adding Usage Examples
-------------------

Usage examples serve both as tests and documentation. To add a new example:

1. Create or modify a file in ``tests/usage_examples/``.

2. Add a test function with a descriptive docstring in this format:

   .. code-block:: python

       def test_your_feature():
           """EXAMPLE: Title of your example
           DESCRIPTION: Detailed description of what this example demonstrates.
           COMMAND: The exact command a user would type
           RESULT:
           The expected output from Angela CLI,
           exactly as it would appear in the terminal
           """
           # Test implementation goes here
           pass

3. Implement the actual test logic to verify the functionality.

4. Run ``pytest`` to ensure your test passes.

5. Generate documentation with ``scripts/generate_docs.sh`` to see your example in the docs.

Documentation
-----------

We use Sphinx for documentation. To build the docs:

.. code-block:: bash

    cd docs
    make html

The output will be in ``docs/build/html/``.

To add a new documentation page:

1. Create a new ``.rst`` file in ``docs/source/``.
2. Add it to the table of contents in ``docs/source/index.rst``.
3. Build the documentation to see your changes.

Code Style
---------

We follow these style guidelines:

- PEP 8 for Python code
- Black for code formatting
- isort for sorting imports
- mypy for type checking

Our pre-commit hooks enforce these standards, so make sure to run:

.. code-block:: bash

    make format
    make lint

before committing.

Pull Request Process
------------------

1. Ensure all tests pass locally.
2. Update documentation if needed.
3. Add yourself to CONTRIBUTORS.md if you're not already listed.
4. Submit your pull request with a clear description of:
   - What problem you're solving
   - How your changes address the problem
   - Any additional context or considerations

Once your PR is submitted, maintainers will review it and provide feedback.

Running Integration Tests
-----------------------

For comprehensive testing, run the integration tests which check actual shell integration:

.. code-block:: bash

    python -m scripts.test_integrations

These tests require shell access and may prompt for input.

Debugging Tips
------------

1. Use the ``--debug`` flag for verbose logging:

   .. code-block:: bash

       angela --debug "your request"

2. Check logs in ``.angela/logs/`` for detailed information.

3. For shell integration issues, add ``set -x`` to the shell script for verbose output:

   .. code-block:: bash

       # In angela/shell/angela.bash or angela/shell/angela.zsh
       set -x  # Add this at the top of the file

Thank You
--------

Your contributions help make Angela CLI better for everyone. Thank you for your time and effort!
