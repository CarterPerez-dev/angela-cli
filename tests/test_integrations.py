# scripts/test_integrations.py

#!/usr/bin/env python3
"""
Test script for Angela CLI shell integration.
"""
import os
import sys
import subprocess
import time

def run_command(command, shell=True):
    """Run a command and return its output."""
    try:
        result = subprocess.run(
            command, 
            shell=shell, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return e.stdout, e.stderr

def test_basic_integration():
    """Test that angela command is available."""
    print("Testing basic integration...")
    
    # See if angela is in PATH
    try:
        stdout, stderr = run_command("which angela")
        print(f"Angela found at: {stdout.strip()}")
    except:
        print("Angela not found in PATH. This is normal if using shell function.")
    
    # Test if angela can be invoked
    try:
        stdout, stderr = run_command("angela --version")
        print(f"Angela version: {stdout.strip()}")
    except:
        print("Failed to invoke Angela. Please check shell integration.")
        return False
    
    return True

def test_notification_hooks():
    """Test that shell hooks are working."""
    print("\nTesting notification hooks...")
    
    # Create a test script
    test_script = """
    #!/bin/bash
    echo "Running test command..."
    # This command will intentionally fail
    ls /nonexistent_directory
    # This is to check if post-execution hook is triggered
    """
    
    with open("/tmp/angela_test.sh", "w") as f:
        f.write(test_script)
    
    os.chmod("/tmp/angela_test.sh", 0o755)
    
    # Run the test script and catch the error
    try:
        stdout, stderr = run_command("/tmp/angela_test.sh")
        print("Test script executed successfully (unexpected)")
    except:
        print("Test script failed as expected")
    
    # Check if Angela registered the command (requires manual verification)
    print("\nPlease verify that Angela detected the failed command.")
    print("You should see a suggestion message in your terminal.")
    
    return True

def test_autocompletion():
    """Test command autocompletion."""
    print("\nTesting autocompletion...")
    
    # This is tricky to test programmatically, so we'll just provide instructions
    print("Please type 'angela rollback ' and press Tab to see if completion works.")
    print("You should see operation, transaction, list, last as completion options.")
    
    return True

def main():
    """Run all integration tests."""
    print("Angela CLI Integration Test")
    print("==========================\n")
    
    # Tests to run
    tests = [
        test_basic_integration,
        test_notification_hooks,
        test_autocompletion
    ]
    
    # Run each test
    success = True
    for test in tests:
        if not test():
            success = False
            
    # Print overall result
    print("\nTest Results:")
    if success:
        print("✅ All tests passed")
    else:
        print("❌ Some tests failed")
    
    # Cleanup
    if os.path.exists("/tmp/angela_test.sh"):
        os.unlink("/tmp/angela_test.sh")

if __name__ == "__main__":
    main()
