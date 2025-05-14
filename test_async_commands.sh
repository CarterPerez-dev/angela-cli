#!/bin/bash
# test_async_commands.sh

# Set up error handling
set -e
echo "Running async command tests..."

# Test the create-framework-project command
echo "Testing create-framework-project command..."
angela generate create-framework-project react "test-react-project" --dry-run

# Add more tests for other async commands as needed

echo "All tests passed successfully!"
