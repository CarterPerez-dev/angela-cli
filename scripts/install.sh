#!/bin/bash
# Angela CLI Installation Script

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "Warning: Running as root. Installing system-wide."
    INSTALL_DIR="/usr/local/lib/angela"
    CONFIG_DIR="/etc/angela"
else
    echo "Installing for current user."
    INSTALL_DIR="$HOME/.local/lib/angela"
    CONFIG_DIR="$HOME/.config/angela"
fi

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/logs"

# Install Python package
echo "Installing Python package..."
pip install -e .

# Determine shell
current_shell="$(basename "$SHELL")"
echo "Detected shell: $current_shell"

# Enhanced integration for Bash
setup_bash() {
    echo "Setting up enhanced Bash integration..."
    
    bashrc="$HOME/.bashrc"
    
    # Check if angela is already in .bashrc
    if grep -q "angela_enhanced.bash" "$bashrc"; then
        echo "Enhanced Bash integration already installed."
    else
        # Remove old integration if present
        sed -i '/angela.bash/d' "$bashrc"
        
        # Add the enhanced integration
        cat << 'EOF' >> "$bashrc"

# Angela CLI Enhanced Integration
if [ -f "$HOME/.local/lib/angela/shell/angela_enhanced.bash" ]; then
    source "$HOME/.local/lib/angela/shell/angela_enhanced.bash"
fi
EOF
        echo "Enhanced Bash integration added to $bashrc"
    fi
    
    # Copy the enhanced shell script
    cp angela/shell/angela_enhanced.bash "$INSTALL_DIR/shell/"
    chmod +x "$INSTALL_DIR/shell/angela_enhanced.bash"
}

# Enhanced integration for Zsh
setup_zsh() {
    echo "Setting up enhanced Zsh integration..."
    
    zshrc="$HOME/.zshrc"
    
    # Check if angela is already in .zshrc
    if grep -q "angela_enhanced.zsh" "$zshrc"; then
        echo "Enhanced Zsh integration already installed."
    else
        # Remove old integration if present
        sed -i '/angela.zsh/d' "$zshrc"
        
        # Add the enhanced integration
        cat << 'EOF' >> "$zshrc"

# Angela CLI Enhanced Integration
if [ -f "$HOME/.local/lib/angela/shell/angela_enhanced.zsh" ]; then
    source "$HOME/.local/lib/angela/shell/angela_enhanced.zsh"
fi
EOF
        echo "Enhanced Zsh integration added to $zshrc"
    fi
    
    # Copy the enhanced shell script
    cp angela/shell/angela_enhanced.zsh "$INSTALL_DIR/shell/"
    chmod +x "$INSTALL_DIR/shell/angela_enhanced.zsh"
}

# Set up based on shell
case "$current_shell" in
    bash)
        setup_bash
        ;;
    zsh)
        setup_zsh
        ;;
    *)
        echo "Unsupported shell: $current_shell"
        echo "Only Bash and Zsh are currently supported."
        echo "Manual installation required."
        exit 1
        ;;
esac

# Copy shell scripts
echo "Setting up shell scripts..."
mkdir -p "$INSTALL_DIR/shell"
cp angela/shell/angela.bash "$INSTALL_DIR/shell/"
cp angela/shell/angela.zsh "$INSTALL_DIR/shell/"
chmod +x "$INSTALL_DIR/shell/angela.bash"
chmod +x "$INSTALL_DIR/shell/angela.zsh"

# Initialize Angela CLI
echo -e "${YELLOW}Initializing Angela CLI...${NC}"


echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Angela CLI installed successfully!  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo "Please restart your shell or run 'source ~/.${current_shell}rc' to complete the installation."
echo -e "You can now use Angela CLI by typing: ${BLUE}angela <your request>${NC}"

