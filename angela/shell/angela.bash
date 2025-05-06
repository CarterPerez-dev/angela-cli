#!/bin/bash
# Angela CLI Bash Integration

# Function to handle Angela CLI requests
angela() {
    # Check if no arguments or help requested
    if [ $# -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        python -m angela --help
        return
    fi

    # Handle version flag
    if [ "$1" = "--version" ] || [ "$1" = "-v" ]; then
        python -m angela --version
        return
    fi

    # Handle debug flag
    if [ "$1" = "--debug" ] || [ "$1" = "-d" ]; then
        DEBUG_FLAG="--debug"
        shift  # Remove the debug flag from arguments
    else
        DEBUG_FLAG=""
    fi

    # Handle specific command (init, etc.)
    if [ "$1" = "init" ]; then
        python -m angela $DEBUG_FLAG init
        return
    fi

    # Process as a request for anything else
    python -m angela $DEBUG_FLAG request "$@"
}

# Enable command completion for angela function
# This will be implemented in a future phase
