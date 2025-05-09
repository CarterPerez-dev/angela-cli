# tests/usage_examples/workflows.py

def test_define_workflow():
    """EXAMPLE: Define a new workflow
    DESCRIPTION: Create a reusable workflow for common tasks.
    COMMAND: define a workflow called deploy that builds the app, runs tests, and deploys to staging
    RESULT:
    Creating workflow "deploy" with the following steps:
    
    1. Build the application
       $ npm run build
    
    2. Run tests
       $ npm test
    
    3. Deploy to staging
       $ git push heroku staging
    
    Workflow "deploy" created successfully!
    Use "angela workflows run deploy" to execute this workflow.
    """
    pass

def test_run_workflow():
    """EXAMPLE: Run an existing workflow
    DESCRIPTION: Execute a previously defined workflow.
    COMMAND: run the deploy workflow
    RESULT:
    Executing workflow "deploy":
    
    Step 1/3: Build the application
    $ npm run build
    > my-app@1.0.0 build
    > webpack --mode production
    
    Step 2/3: Run tests
    $ npm test
    > my-app@1.0.0 test
    > jest
    PASS tests/app.test.js
    
    Step 3/3: Deploy to staging
    $ git push heroku staging
    Counting objects: 5, done.
    
    Workflow completed successfully!
    """
    pass

def test_workflow_with_variables():
    """EXAMPLE: Use variables in workflows
    DESCRIPTION: Create a workflow that accepts parameters.
    COMMAND: define a workflow called backup that takes a directory path and creates a timestamped backup
    RESULT:
    Creating parameterized workflow "backup":
    
    Variables:
    - $DIRECTORY: Directory path to backup
    
    Steps:
    1. Create timestamp
       $ TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    
    2. Create backup archive
       $ tar -czf backup_$TIMESTAMP.tar.gz $DIRECTORY
    
    3. Show backup info
       $ echo "Backup of $DIRECTORY created as backup_$TIMESTAMP.tar.gz"
    
    Workflow "backup" created successfully!
    Run with: angela workflows run backup --directory=/path/to/backup
    """
    pass

def test_multi_step_operation():
    """EXAMPLE: Perform a multi-step operation
    DESCRIPTION: Angela can break down complex requests into discrete steps.
    COMMAND: create a feature branch called user-auth, add a new auth.py file with basic Flask-Login code, and commit it
    RESULT:
    I'll break this down into multiple steps:
    
    1. Create a new feature branch
       $ git checkout -b user-auth
    
    2. Create auth.py with Flask-Login code
       Creating file: auth.py
    
    3. Add the file to git
       $ git add auth.py
    
    4. Commit the changes
       $ git commit -m "Add basic Flask-Login implementation"
    
    Execute these steps? [Y/n]: 
    """
    pass
