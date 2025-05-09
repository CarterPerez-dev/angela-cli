#!/bin/bash
# scripts/generate_docs.sh

set -e

# Create documentation directory if it doesn't exist
mkdir -p docs/source/ext
mkdir -p tests/usage_examples

# Copy extension if it doesn't exist
if [ ! -f docs/source/ext/usage_examples.py ]; then
    echo "Creating usage examples extension..."
    cat > docs/source/ext/usage_examples.py << 'EOF'
# Extension code goes here
EOF
fi

# Extract API documentation
echo "Generating API documentation..."
sphinx-apidoc -o docs/source/api angela

# Build documentation
cd docs
make html

echo "Documentation built successfully in docs/build/html/"
