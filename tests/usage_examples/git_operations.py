# tests/usage_examples/git_operations.py

def test_git_status():
    """EXAMPLE: Check Git status
    DESCRIPTION: Use Angela to check the status of your Git repository.
    COMMAND: what's the status of my git repo
    RESULT:
    Executing command: git status
    On branch main
    Changes not staged for commit:
      (use "git add <file>..." to update what will be committed)
      (use "git restore <file>..." to discard changes in working directory)
            modified:   README.md
    
    no changes added to commit (use "git add" and/or "git commit -a")
    """
    pass

def test_create_branch():
    """EXAMPLE: Create a new feature branch
    DESCRIPTION: Use Angela to create a new feature branch and switch to it.
    COMMAND: create a new branch called feature/user-auth and switch to it
    RESULT:
    Creating plan to:
    1. Create new branch 'feature/user-auth'
    2. Switch to the new branch
    
    Executing command: git branch feature/user-auth
    Executing command: git checkout feature/user-auth
    Switched to branch 'feature/user-auth'
    """
    pass
