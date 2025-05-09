# tests/usage_examples/file_operations.py

def test_file_listing():
    """EXAMPLE: List files in current directory
    DESCRIPTION: Use Angela to list all files in the current directory with details.
    COMMAND: list all files in current directory with size and date
    RESULT:
    Executing command: ls -la
    total 40
    drwxr-xr-x  5 user  staff   160 May  9 10:15 .
    drwxr-xr-x  3 user  staff    96 May  9 10:12 ..
    -rw-r--r--  1 user  staff  1240 May  9 10:15 README.md
    -rw-r--r--  1 user  staff   432 May  9 10:15 setup.py
    drwxr-xr-x  8 user  staff   256 May  9 10:15 angela
    """
    pass  # Actual test implementation would go here

def test_create_file():
    """EXAMPLE: Create a new file with content
    DESCRIPTION: Use Angela to create a new text file and write some content to it.
    COMMAND: create a file called notes.txt with the content "Meeting agenda for tomorrow"
    RESULT:
    Creating file: notes.txt
    Writing content to file
    File created successfully!
    """
    pass  # Actual test implementation would go here
