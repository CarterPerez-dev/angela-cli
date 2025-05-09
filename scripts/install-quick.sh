#!/bin/bash
# Quick installer for Angela CLI

set -e  # Exit on any error

# Print colored status messages
info() { echo -e "\033[0;36m$1\033[0m"; }
success() { echo -e "\033[0;32m$1\033[0m"; }
warn() { echo -e "\033[0;33m$1\033[0m"; }
error() { echo -e "\033[0;31m$1\033[0m"; }

# Create temporary directory
TMP_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# Check Python version
info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$PY_VERSION" | awk -F. '{print $1}') -lt 3 || ($(echo "$PY_VERSION" | awk -F. '{print $1}') -eq 3 && $(echo "$PY_VERSION" | awk -F. '{print $2}') -lt 9) ]]; then
    error "Python 3.9+ is required, but you have $PY_VERSION"
    exit 1
fi

info "Python $PY_VERSION detected ✓"

# Check pip
if ! command -v pip3 &> /dev/null; then
    error "pip3 is not installed. Please install pip for Python 3."
    exit 1
fi

# Check if sphinx is installed
info "Checking for Sphinx documentation generator..."
if ! python3 -c "import sphinx" &> /dev/null; then
    info "Installing Sphinx for documentation..."
    pip3 install sphinx sphinx_rtd_theme
fi

# Clone the repository
info "Downloading Angela CLI..."
cd "$TMP_DIR"
git clone https://github.com/your-repo/angela-cli.git --depth=1
cd angela-cli

# Install Angela CLI
info "Installing Angela CLI..."
pip3 install -e . --user

# Set up shell integration
info "Setting up shell integration..."
SHELL_TYPE=$(basename "$SHELL")
RC_FILE=""

case "$SHELL_TYPE" in
    bash)
        RC_FILE="$HOME/.bashrc"
        ;;
    zsh)
        RC_FILE="$HOME/.zshrc"
        ;;
    *)
        warn "Unsupported shell: $SHELL_TYPE. Please manually add Angela to your shell."
        ;;
esac

if [ -n "$RC_FILE" ]; then
    if grep -q "angela.bash" "$RC_FILE" || grep -q "angela.zsh" "$RC_FILE"; then
        info "Shell integration already set up."
    else
        # Get the integration file path
        ANGELA_PATH=$(pip3 show angela-cli | grep "Location" | cut -d " " -f 2)
        if [ "$SHELL_TYPE" = "bash" ]; then
            INTEGRATION_FILE="$ANGELA_PATH/angela/shell/angela.bash"
        else
            INTEGRATION_FILE="$ANGELA_PATH/angela/shell/angela.zsh"
        fi
        
        # Add to shell config
        echo "" >> "$RC_FILE"
        echo "# Angela CLI integration" >> "$RC_FILE"
        echo "source \"$INTEGRATION_FILE\"" >> "$RC_FILE"
        
        success "Shell integration added to $RC_FILE"
        info "Please restart your shell or run: source $RC_FILE"
    fi
fi

# Build documentation
info "Building documentation..."
bash scripts/generate_docs.sh

# Set up API key
read -p "Would you like to set up your Gemini API key now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your Gemini API key: " API_KEY
    mkdir -p ~/.config/angela
    echo "GEMINI_API_KEY=$API_KEY" > ~/.config/angela/.env
    success "API key saved!"
fi

success "✅ Angela CLI installed successfully!"
info "Documentation available at: ~/.local/lib/angela/docs/build/html/index.html"
info "To get started, try: angela \"help me with git commands\""
