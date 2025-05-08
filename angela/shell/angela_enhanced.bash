#!/bin/bash
# Angela CLI Enhanced Bash Integration

# Global variables for tracking
ANGELA_LAST_COMMAND=""
ANGELA_LAST_COMMAND_RESULT=$?
ANGELA_LAST_PWD="$PWD"
ANGELA_COMMAND_START_TIME=0

# Pre-command execution hook
angela_pre_exec() {
    # Capture the command
    ANGELA_LAST_COMMAND="$BASH_COMMAND"
    ANGELA_COMMAND_START_TIME=$(date +%s)
    
    # Send notification to Angela's monitoring system
    if [[ ! "$ANGELA_LAST_COMMAND" =~ ^angela ]]; then
        # Only track non-angela commands to avoid recursion
        (angela --notify pre_exec "$ANGELA_LAST_COMMAND" &>/dev/null &)
    fi
}

# Post-command execution hook
angela_post_exec() {
    local exit_code=$?
    ANGELA_LAST_COMMAND_RESULT=$exit_code
    local duration=$(($(date +%s) - ANGELA_COMMAND_START_TIME))
    
    # Check for directory change
    if [[ "$PWD" != "$ANGELA_LAST_PWD" ]]; then
        # Directory changed, update context
        ANGELA_LAST_PWD="$PWD"
        (angela --notify dir_change "$PWD" &>/dev/null &)
    fi
    
    # Send post-execution notification for non-angela commands
    if [[ ! "$ANGELA_LAST_COMMAND" =~ ^angela ]]; then
        # Pass execution result to Angela
        (angela --notify post_exec "$ANGELA_LAST_COMMAND" $exit_code $duration &>/dev/null &)
        
        # Check if we should offer assistance based on exit code and command pattern
        if [[ $exit_code -ne 0 ]]; then
            angela_check_command_suggestion "$ANGELA_LAST_COMMAND" $exit_code
        fi
    fi
}

# Function to check if Angela should offer command suggestions
angela_check_command_suggestion() {
    local command="$1"
    local exit_code=$2
    
    # Check for common error patterns
    case "$command" in
        git*)
            # For git commands with errors, offer assistance
            if [[ $exit_code -ne 0 ]]; then
                echo -e "\033[33m[Angela] I noticed your git command failed. Need help? Try: angela fix-git\033[0m"
            fi
            ;;
        python*|pip*)
            # For Python-related errors
            if [[ $exit_code -ne 0 ]]; then
                echo -e "\033[33m[Angela] Python command failed. For assistance, try: angela fix-python\033[0m"
            fi
            ;;
    esac
    
    # Match other patterns that might benefit from Angela's assistance
    if [[ "$command" =~ "commit -m" ]]; then
        # Offer to enhance commit messages
        echo -e "\033[33m[Angela] I can help with more descriptive commit messages. Try: angela enhance-commit\033[0m"
    fi
}

# Install hooks
trap angela_pre_exec DEBUG
PROMPT_COMMAND="angela_post_exec${PROMPT_COMMAND:+;$PROMPT_COMMAND}"

# Main Angela function
angela() {
    # Check if no arguments or help requested
    if [ $# -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        python -m angela --help
        return
    fi

    # Handle notify subcommand (used by hooks)
    if [ "$1" = "--notify" ]; then
        # This is a notification from the hooks, handle silently
        python -m angela --notify "${@:2}" &>/dev/null &
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

    # Handle natural language commands (implicit invocation)
    if [ "$1" = "fix" ] || [ "$1" = "explain" ] || [ "$1" = "help-with" ]; then
        # These are common natural language commands
        python -m angela $DEBUG_FLAG request "$@"
        return
    fi

    # Handle specific command (init, etc.)
    if [ "$1" = "init" ]; then
        python -m angela $DEBUG_FLAG init
        return
    fi

    # Process as a request for anything else
    python -m angela $DEBUG_FLAG request "$@"
}

# Register completion for angela
_angela_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # Get dynamic completions from Angela
    local completions=$(angela --completions "${COMP_WORDS[@]:1}" 2>/dev/null)
    
    # If completions were returned, use them
    if [ -n "$completions" ]; then
        COMPREPLY=( $(compgen -W "$completions" -- "$cur") )
        return 0
    fi
    
    # Fallback static completions
    opts="init status shell files workflows generate rollback fix explain help-with"
    
    # Complete based on the current argument
    if [[ ${prev} == "angela" ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _angela_completion angela
