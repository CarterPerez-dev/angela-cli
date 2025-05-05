#!/bin/zsh
# Angela CLI Zsh Integration

# Function to handle Angela CLI requests
angela() {
    # Check if arguments were provided
    if [ $# -eq 0 ]; then
        # No arguments, show help
        python -m angela --help
    else
        # Capture the current working directory
        local current_dir=$(pwd)
        
        # Process the request
        python -m angela request "$@"
        
        # Note: In future phases, we'll add support for command execution,
        # directory changing, etc. For now, this is just a simple pass-through.
    fi
}

# Enable command completion for angela function
# This will be implemented in a future phase
