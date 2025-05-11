# angela/utils/async_utils.py
"""
Utility functions for handling async operations in synchronous contexts.

This module provides helper functions to safely run asynchronous code
from synchronous contexts without causing runtime errors.
"""
import asyncio
import functools
import threading
from typing import Any, Callable, Coroutine, TypeVar, cast, Optional

from angela.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

def run_async(coroutine: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine from a synchronous context.
    
    This function creates a new event loop, runs the coroutine to completion,
    and then closes the loop. It's safe to use when there is no active
    event loop in the current thread.
    
    Args:
        coroutine: The coroutine (async function) to run
        
    Returns:
        The result of the coroutine
        
    Example:
        ```
        # Instead of this (which will fail if no event loop):
        result = asyncio.create_task(some_async_function())
        
        # Use this:
        result = run_async(some_async_function())
        ```
    """
    try:
        # Check if there's already a running loop
        try:
            loop = asyncio.get_running_loop()
            logger.warning(
                "Called run_async from a thread that already has a running event loop. "
                "This might lead to unexpected behavior."
            )
            raise RuntimeError(
                "run_async called from an async context. "
                "Use 'await coroutine' directly instead."
            )
        except RuntimeError:
            pass
        
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coroutine)
        finally:
            # Always close the loop to clean up resources
            loop.close()
            # Reset the event loop to None to avoid affecting other code
            asyncio.set_event_loop(None)
    except Exception as e:
        logger.error(f"Error running async coroutine: {str(e)}")
        raise  # Re-raise the exception after logging

def to_sync(async_func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Convert an async function to a synchronous function.
    
    This decorator wraps an async function so it can be called
    like a regular synchronous function.
    
    Args:
        async_func: The async function to convert
        
    Returns:
        A synchronous version of the function
        
    Example:
        ```
        @to_sync
        async def fetch_data(url):
            # async code here
            return result
            
        # Now you can call it synchronously:
        result = fetch_data("https://example.com")
        ```
    """
    @functools.wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        coroutine = async_func(*args, **kwargs)
        return run_async(coroutine)
    return wrapper

def run_async_background(
    coroutine: Coroutine[Any, Any, T], 
    callback: Optional[Callable[[T], None]] = None,
    error_callback: Optional[Callable[[Exception], None]] = None
) -> threading.Thread:
    """
    Run an async coroutine in a background thread with optional callbacks.
    
    This is useful for fire-and-forget operations where you don't need
    to wait for the result.
    
    Args:
        coroutine: The coroutine to run
        callback: Optional function to call with the result when done
        error_callback: Optional function to call if an error occurs
        
    Returns:
        The background thread object (already started)
        
    Example:
        ```
        def on_complete(result):
            print(f"Operation completed with result: {result}")
            
        def on_error(error):
            print(f"Operation failed: {error}")
            
        thread = run_async_background(
            long_running_operation(), 
            callback=on_complete,
            error_callback=on_error
        )
        # Continue with other work while operation runs in background
        ```
    """
    def _run_in_thread() -> None:
        try:
            result = run_async(coroutine)
            if callback:
                callback(result)
        except Exception as e:
            logger.error(f"Error in background async task: {str(e)}")
            if error_callback:
                error_callback(e)
                
    thread = threading.Thread(target=_run_in_thread)
    thread.daemon = True  # Make the thread exit when the main program exits
    thread.start()
    return thread
