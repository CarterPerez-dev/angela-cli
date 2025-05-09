# tests/usage_examples/testing_debugging.py

def test_generate_unit_tests():
    """EXAMPLE: Generate unit tests
    DESCRIPTION: Angela can help generate unit tests for your code.
    COMMAND: create unit tests for the User class in models/user.py
    RESULT:
    Analyzing User class in models/user.py...
    
    Found methods to test:
    - __init__
    - validate_password
    - generate_token
    - from_token
    
    Creating test file: tests/test_user_model.py
    
    ```python
    import pytest
    from models.user import User
    
    class TestUser:
        def test_init(self):
            user = User(username="testuser", email="test@example.com")
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.created_at is not None
            
        def test_validate_password(self):
            user = User(username="testuser", email="test@example.com")
            user.set_password("password123")
            assert user.validate_password("password123") is True
            assert user.validate_password("wrongpassword") is False
            
        def test_generate_token(self):
            user = User(username="testuser", email="test@example.com")
            token = user.generate_token()
            assert token is not None
            assert isinstance(token, str)
            
        def test_from_token(self):
            user = User(username="testuser", email="test@example.com")
            token = user.generate_token()
            retrieved_user = User.from_token(token)
            assert retrieved_user is not None
            assert retrieved_user.username == user.username
            assert retrieved_user.email == user.email
    ```
    
    Test file created successfully!
    """
    pass

def test_debug_code():
    """EXAMPLE: Debug code issues
    DESCRIPTION: Angela can help identify and fix bugs in your code.
    COMMAND: debug why my Flask route is returning 500 errors
    RESULT:
    Analyzing Flask application logs and code...
    
    Found traceback in error logs:
    ```
    File "app.py", line 45, in user_profile
        user_data = get_user_by_id(user_id)
    File "models/user.py", line 67, in get_user_by_id
        return db.session.query(User).filter(User.id == user_id).first()
    TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
    ```
    
    Root cause: The user_id parameter is None when reaching the database query.
    
    Suggested fix in app.py, line 44-47:
    ```python
    @app.route('/user/<int:user_id>')
    def user_profile(user_id):
        if user_id is None:
            return redirect(url_for('index'))
        user_data = get_user_by_id(user_id)
        # ...
    ```
    
    Apply this fix? [y/N]:
    """
    pass

def test_performance_analysis():
    """EXAMPLE: Code performance analysis
    DESCRIPTION: Angela can analyze and optimize slow code.
    COMMAND: why is my data import script so slow
    RESULT:
    Analyzing import_data.py...
    
    Performance bottlenecks detected:
    
    1. Line 34: Database operations inside loop
       → Moving 1000 separate INSERT statements into a single transaction would be ~50x faster
    
    2. Line 57: Inefficient CSV parsing
       → Using pandas instead of manual CSV parsing would reduce processing time by ~70%
       
    3. Line 89: Repeated API calls without caching
       → Implementing basic caching would eliminate 90% of redundant network requests
    
    Would you like me to optimize this script? I can:
    1. Implement batch database operations
    2. Convert to pandas for CSV processing 
    3. Add caching for API calls
    4. All of the above
    
    Your choice [1-4]:
    """
    pass

def test_log_analysis():
    """EXAMPLE: Log file analysis
    DESCRIPTION: Angela can analyze log files to identify patterns and issues.
    COMMAND: check my application logs for errors
    RESULT:
    Analyzing application logs in /var/log/myapp/...
    
    Summary of issues found:
    
    1. Database connection timeouts (27 occurrences)
       First seen: May 8, 2025 14:23:15
       Last seen: May 9, 2025 06:45:32
       Pattern: "ConnectionError: Connection timed out"
    
    2. Memory usage warnings (15 occurrences)
       Pattern: "WARNING: Memory usage exceeds 80%"
       Increasing frequency - possible memory leak
    
    3. Authentication failures (42 occurrences)
       Multiple failed attempts for user 'admin' from IP 203.0.113.42
       Possible brute force attack attempt
    
    Would you like detailed information on any of these issues? [1-3]:
    """
    pass
