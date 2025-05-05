#!/bin/bash
# Angela CLI Uninstallation Script

set -e

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Angela CLI Uninstallation       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Confirm uninstallation
echo -e "${YELLOW}Are you sure you want to uninstall Angela CLI? (y/n)${NC}"
read -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${RED}Uninstallation cancelled.${NC}"
    exit 0
fi

# Function to remove Bash integration
remove_bash_integration() {
    echo -e "${YELLOW}Removing Bash integration...${NC}"
    BASH_RC="$HOME/.bashrc"
    
    if grep -q "# Angela CLI Integration" "$BASH_RC"; then
        # Remove integration from .bashrc
        sed -i '/# Angela CLI Integration/,/# End Angela CLI Integration/d' "$BASH_RC"
        echo -e "${GREEN}Bash integration removed successfully!${NC}"
    else
        echo -e "${YELLOW}No Angela CLI integration found in $BASH_RC${NC}"
    fi
}

# Function to remove Zsh integration
remove_zsh_integration() {
    echo -e "${YELLOW}Removing Zsh integration...${NC}"
    ZSH_RC="$HOME/.zshrc"
    
    if grep -q "# Angela CLI Integration" "$ZSH_RC"; then
        # Remove integration from .zshrc
        sed -i '/# Angela CLI Integration/,/# End Angela CLI Integration/d' "$ZSH_RC"
        echo -e "${GREEN}Zsh integration removed successfully!${NC}"
    else
        echo -e "${YELLOW}No Angela CLI integration found in $ZSH_RC${NC}"
    fi
}

# Remove both integrations to ensure complete uninstallation
remove_bash_integration
remove_zsh_integration

# Remove configuration
echo -e "${YELLOW}Would you like to remove Angela CLI configuration? (y/n)${NC}"
read -r REMOVE_CONFIG
if [[ "$REMOVE_CONFIG" =~ ^[Yy]$ ]]; then
    CONFIG_DIR="$HOME/.config/angela"
    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}Configuration removed successfully!${NC}"
    else
        echo -e "${YELLOW}No configuration directory found.${NC}"
    fi
fi

# Uninstall Python package
echo -e "${YELLOW}Would you like to uninstall the Angela CLI Python package? (y/n)${NC}"
read -r UNINSTALL_PACKAGE
if [[ "$UNINSTALL_PACKAGE" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Uninstalling Angela CLI Python package...${NC}"
    pip uninstall -y angela-cli
    echo -e "${GREEN}Python package uninstalled successfully!${NC}"
fi

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Angela CLI uninstalled successfully! ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}Please restart your terminal for changes to take effect.${NC}"
echo
