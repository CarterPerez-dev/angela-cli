#!/bin/bash
# Angela CLI Tmux Integration

# Define Angela status indicator for Tmux status bar
angela_tmux_status() {
    # Check if Angela is enabled
    if [ -f "$HOME/.config/angela/enabled" ]; then
        echo "#[fg=green]◉ Angela#[fg=default]"
    else
        echo "#[fg=red]◯ Angela#[fg=default]"
    fi
}

# Register Angela key bindings
angela_tmux_bindings() {
    # Bind Alt+A to activate Angela
    tmux bind-key -n M-a run-shell "angela status"
    
    # Bind Alt+C to send current pane command to Angela
    tmux bind-key -n M-c run-shell "tmux capture-pane -p | tail -n 1 | sed 's/^[^#]*#//' | angela request"
    
    # Bind Alt+H for Angela help
    tmux bind-key -n M-h run-shell "angela --help"
}

# Setup Angela integration in Tmux
angela_tmux_setup() {
    # Add Angela status to right status bar
    tmux set-option -g status-right "#{?window_zoomed_flag,#[fg=yellow]Z#[fg=default] ,}#[fg=blue]#(angela_tmux_status) | %H:%M %d-%b-%y"
    
    # Register key bindings
    angela_tmux_bindings
    
    # Set the status update interval to update Angela status
    tmux set-option -g status-interval 5
}

# Main function
main() {
    # Check if we're running inside tmux
    if [ -n "$TMUX" ]; then
        angela_tmux_setup
        echo "Angela Tmux integration enabled"
    else
        echo "Error: Not running inside tmux session"
        exit 1
    fi
}

# Run main function
main "$@"
