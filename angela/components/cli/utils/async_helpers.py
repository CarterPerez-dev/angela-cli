# angela/components/cli/utils/async_helpers.py
"""
Async utilities for Typer commands.

This module provides decorators and helpers for working with async functions in Typer commands.
"""
import asyncio
import functools
import logging
from typing import Callable, Any, TypeVar, cast, Optional, Union
import typer

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])

def async_command(app_or_name=None, *args, **kwargs):
    """
    Decorator that converts an async function into a synchronous Typer command.
    
    Can be used in two ways:
    1. With app instance: @async_command(app, "command-name")
    2. Without app: @async_command("command-name") - must then be used inside a module with an 'app' variable
    
    Args:
        app_or_name: Either a Typer app instance or the command name
        *args: Additional arguments to pass to app.command()
        **kwargs: Keyword arguments to pass to app.command()
        
    Returns:
        A decorator function that wraps an async function and applies app.command()
    """
    # Determine if first arg is app instance or command name
    app_instance = None
    cmd_args = list(args)
    
    if app_or_name is None:
        # Just @async_command() without arguments
        def get_app():
            # Get app from module globals
            import inspect
            frame = inspect.currentframe()
            try:
                if frame and frame.f_back and frame.f_back.f_globals:
                    return frame.f_back.f_globals.get('app')
            finally:
                del frame
            return None
    elif isinstance(app_or_name, str) or app_or_name is None:
        # Command name provided, e.g., @async_command("command-name")
        # Prepend the name to args if it's a string
        if isinstance(app_or_name, str):
            cmd_args.insert(0, app_or_name)
        
        def get_app():
            # Get app from module globals
            import inspect
            frame = inspect.currentframe()
            try:
                if frame and frame.f_back and frame.f_back.f_globals:
                    return frame.f_back.f_globals.get('app')
            finally:
                del frame
            return None
    else:
        # App instance provided, e.g., @async_command(app, "command-name")
        app_instance = app_or_name
        
        def get_app():
            return app_instance
    
    def decorator(async_func: F) -> F:
        @functools.wraps(async_func)
        def sync_wrapper(*func_args, **func_kwargs):
            try:
                return asyncio.run(async_func(*func_args, **func_kwargs))
            except Exception as e:
                logger.exception(f"Error running async command {async_func.__name__}: {str(e)}")
                raise
        
        # Get the app instance (either provided or from module globals)
        app = get_app()
        if app is None:
            raise ValueError(
                f"Could not find a Typer app instance for async command {async_func.__name__}. "
                "Either pass the app instance to @async_command or ensure there's an 'app' variable in the module."
            )
        
        # Apply the app.command decorator to the wrapper
        wrapped = app.command(*cmd_args, **kwargs)(sync_wrapper)
        return cast(F, wrapped)
    
    return decorator
