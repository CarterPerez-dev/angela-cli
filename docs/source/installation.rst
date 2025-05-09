Installation
============

Prerequisites
------------

Before installing Angela CLI, ensure you have:

* Python 3.9 or higher
* pip (Python package installer)
* Git
* Bash or Zsh shell

Quick Installation
----------------

The fastest way to install Angela CLI is with our installation script:

.. code-block:: bash

    curl -sSL https://raw.githubusercontent.com/your-repo/angela-cli/main/scripts/install-quick.sh | bash

This script will:

1. Clone the Angela CLI repository
2. Install the package and dependencies
3. Set up shell integration for Bash or Zsh
4. Build documentation
5. Prompt you to configure your API key

Manual Installation
-----------------

If you prefer to install manually, follow these steps:

1. Clone the repository:

   .. code-block:: bash

       git clone https://github.com/your-repo/angela-cli.git
       cd angela-cli

2. Install the package:

   .. code-block:: bash

       pip install -e .

3. Set up shell integration:

   For Bash:

   .. code-block:: bash

       echo 'source "$(dirname $(python -c "import angela; print(angela.__file__)"))/shell/angela.bash"' >> ~/.bashrc
       source ~/.bashrc

   For Zsh:

   .. code-block:: bash

       echo 'source "$(dirname $(python -c "import angela; print(angela.__file__)"))/shell/angela.zsh"' >> ~/.zshrc
       source ~/.zshrc

4. Configure your API key:

   .. code-block:: bash

       mkdir -p ~/.config/angela
       echo "GEMINI_API_KEY=your_api_key_here" > ~/.config/angela/.env

API Key Setup
-----------

Angela CLI requires a Google Gemini API key to function. You can get one at `Google AI Studio <https://makersuite.google.com/>`_.

Once you have your key, you can:

1. Let the installer script set it up for you, or
2. Manually create the config file:

   .. code-block:: bash

       mkdir -p ~/.config/angela
       echo "GEMINI_API_KEY=your_api_key_here" > ~/.config/angela/.env

Verifying Installation
--------------------

To verify that Angela CLI is installed correctly, run:

.. code-block:: bash

    angela --version

You should see the version number of Angela CLI.

Next, try a simple request:

.. code-block:: bash

    angela "hello world"

If everything is working, Angela should respond with a greeting.

Troubleshooting
--------------

If you encounter issues during installation:

1. **Shell integration not working**:
   
   Ensure that the shell script is being sourced correctly in your shell configuration file.
   Try running ``source ~/.bashrc`` or ``source ~/.zshrc`` to reload your configuration.

2. **API key issues**:
   
   Check that your API key is correctly set in the `~/.config/angela/.env` file.

3. **Python version errors**:
   
   Verify your Python version with ``python3 --version``. Angela CLI requires Python 3.9 or higher.

4. **Dependency conflicts**:
   
   Try installing Angela CLI in a virtual environment to avoid dependency conflicts:
   
   .. code-block:: bash
   
       python -m venv angela-env
       source angela-env/bin/activate
       pip install -e path/to/angela-cli

For additional help, check the GitHub issues page or run ``angela "help me troubleshoot installation"``.
