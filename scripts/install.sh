#!/bin/bash
# Angela CLI Installation Script

set -e

# Determine script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ANGELA_ROOT="$(dirname "$SCRIPT_DIR")"

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Angela CLI Installation         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Install Python package in development mode
echo -e "${YELLOW}Installing Angela CLI Python package...${NC}"
pip install -e "$ANGELA_ROOT"
echo -e "${GREEN}Python package installed successfully!${NC}"
echo

# Detect shell and perform appropriate installation
echo -e "${YELLOW}Detecting shell...${NC}"
DETECTED_SHELL="$(basename "$SHELL")"
echo -e "Detected shell: ${BLUE}$DETECTED_SHELL${NC}"

# Function to install Bash integration
install_bash() {
    echo -e "${YELLOW}Installing Bash integration...${NC}"
    BASH_RC="$HOME/.bashrc"
    
    # Check if integration is already installed
    if grep -q "# Angela CLI Integration" "$BASH_RC"; then
        echo -e "${YELLOW}Angela CLI integration already exists in $BASH_RC${NC}"
        echo -e "${YELLOW}Updating existing integration...${NC}"
        # Remove existing integration
        sed -i '/# Angela CLI Integration/,/# End Angela CLI Integration/d' "$BASH_RC"
    fi
    
    # Add integration to .bashrc
    echo "" >> "$BASH_RC"
    echo "# Angela CLI Integration" >> "$BASH_RC"
    echo "source \"$ANGELA_ROOT/shell/angela.bash\"" >> "$BASH_RC"
    echo "# End Angela CLI Integration" >> "$BASH_RC"
    
    echo -e "${GREEN}Bash integration installed successfully!${NC}"
    echo -e "${YELLOW}Please restart your terminal or run 'source ~/.bashrc' to apply changes.${NC}"
}

# Function to install Zsh integration
install_zsh() {
    echo -e "${YELLOW}Installing Zsh integration...${NC}"
    ZSH_RC="$HOME/.zshrc"
    
    # Check if integration is already installed
    if grep -q "# Angela CLI Integration" "$ZSH_RC"; then
        echo -e "${YELLOW}Angela CLI integration already exists in $ZSH_RC${NC}"
        echo -e "${YELLOW}Updating existing integration...${NC}"
        # Remove existing integration
        sed -i '/# Angela CLI Integration/,/# End Angela CLI Integration/d' "$ZSH_RC"
    fi
    
    # Add integration to .zshrc
    echo "" >> "$ZSH_RC"
    echo "# Angela CLI Integration" >> "$ZSH_RC"
    echo "source \"$ANGELA_ROOT/shell/angela.zsh\"" >> "$ZSH_RC"
    echo "# End Angela CLI Integration" >> "$ZSH_RC"
    
    echo -e "${GREEN}Zsh integration installed successfully!${NC}"
    echo -e "${YELLOW}Please restart your terminal or run 'source ~/.zshrc' to apply changes.${NC}"
}

# Install based on detected shell
case "$DETECTED_SHELL" in
    bash)
        install_bash
        ;;
    zsh)
        install_zsh
        ;;
    *)
        echo -e "${RED}Unsupported shell: $DETECTED_SHELL${NC}"
        echo -e "${YELLOW}Supported shells: bash, zsh${NC}"
        echo 
        echo -e "${YELLOW}Would you like to install for bash anyway? (y/n)${NC}"
        read -r INSTALL_BASH
        if [[ "$INSTALL_BASH" =~ ^[Yy]$ ]]; then
            install_bash
        else
            echo -e "${RED}Installation cancelled.${NC}"
            exit 1
        fi
        ;;
esac

# Initialize Angela CLI
echo -e "${YELLOW}Initializing Angela CLI...${NC}"
python -m angela init

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Angela CLI installed successfully!  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo -e "You can now use Angela CLI by typing: ${BLUE}angela <your request>${NC}"
echo
