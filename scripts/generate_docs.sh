#!/bin/bash
# scripts/generate_docs.sh - Enhanced version

set -e

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Angela CLI Documentation Builder   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Create documentation directory structure if it doesn't exist
echo -e "${YELLOW}Creating directory structure...${NC}"
mkdir -p docs/source/ext
mkdir -p docs/source/_static
mkdir -p docs/source/_templates
mkdir -p tests/usage_examples

# Copy extension if it doesn't exist or update if newer
if [ ! -f docs/source/ext/usage_examples.py ] || [ docs/source/ext/usage_examples_enhanced.py -nt docs/source/ext/usage_examples.py ]; then
    echo -e "${YELLOW}Updating usage examples extension...${NC}"
    cp docs/source/ext/usage_examples_enhanced.py docs/source/ext/usage_examples.py
fi

# Check if the required packages are installed
echo -e "${YELLOW}Checking required packages...${NC}"
python -c "import sphinx" 2>/dev/null || {
    echo -e "${RED}Sphinx not found. Installing...${NC}"
    pip install sphinx sphinx_rtd_theme
}

# Extract API documentation
echo -e "${YELLOW}Generating API documentation...${NC}"
sphinx-apidoc -o docs/source/api angela

# Verify all usage example files are valid Python
echo -e "${YELLOW}Validating usage example files...${NC}"
for example_file in tests/usage_examples/*.py; do
    if [ -f "$example_file" ]; then
        python -m py_compile "$example_file" 2>/dev/null || {
            echo -e "${RED}Error in $example_file - fixing...${NC}"
            # Fix common issues with the file
            sed -i 's/```/`/g' "$example_file"  # Fix triple backticks
            sed -i 's/"""EXAMPLE:/"""\nEXAMPLE:/g' "$example_file"  # Fix docstring format
        }
    fi
done

# Ensure index.rst has a usage_examples directive
if ! grep -q "usage_examples::" docs/source/index.rst; then
    echo -e "${YELLOW}Adding usage_examples directive to index.rst...${NC}"
    # Add after "Contents:" line
    sed -i '/Contents:/a\\\n.. usage_examples::' docs/source/index.rst
fi

# Check for required pages
required_pages=("introduction" "installation" "quickstart" "usage" "examples" "contributing")
for page in "${required_pages[@]}"; do
    if [ ! -f "docs/source/${page}.rst" ]; then
        echo -e "${RED}Missing ${page}.rst - Please create this file${NC}"
    fi
done

# Build documentation
echo -e "${YELLOW}Building documentation...${NC}"
cd docs
make html

# Check for build errors
if [ $? -ne 0 ]; then
    echo -e "${RED}Documentation build failed. Please check the errors above.${NC}"
    exit 1
fi

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║ Documentation built successfully!       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo -e "Documentation is available in: ${BLUE}docs/build/html/index.html${NC}"
echo -e "To view it in your browser, run: ${YELLOW}python -m http.server --directory docs/build/html${NC}"
echo

# Optional: Open the docs in a browser if not in CI
if [ -z "$CI" ]; then
    echo -e "${YELLOW}Would you like to open the documentation in your browser? (y/n)${NC}"
    read -r OPEN_DOCS
    if [[ "$OPEN_DOCS" =~ ^[Yy]$ ]]; then
        if command -v xdg-open &>/dev/null; then
            xdg-open docs/build/html/index.html
        elif command -v open &>/dev/null; then
            open docs/build/html/index.html
        elif command -v start &>/dev/null; then
            start docs/build/html/index.html
        else
            python -m http.server --directory docs/build/html
        fi
    fi
fi
