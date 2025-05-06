# Phase 6: Enhanced Project Context - Implementation Guide

This guide provides detailed instructions on how to implement Phase 6 of the Angela CLI project, which focuses on enhancing project context awareness.

## Overview

Phase 6 adds the following capabilities to Angela CLI:

1. **Project Type Inference** - Automatically detect project type, frameworks, and dependencies
2. **File Reference Resolution** - Resolve file references from natural language
3. **File Activity Tracking** - Track file operations for better context
4. **Enhanced Prompt Engineering** - Use all the above to improve AI responses

## Implementation Steps

### Step 1: Add New Core Files

First, add the following new files to the project:

- `angela/context/enhancer.py` - Context enhancement with project inference
- `angela/context/file_resolver.py` - File reference resolution from natural language
- `angela/context/file_activity.py` - File activity tracking
- `angela/execution/hooks.py` - Execution hooks for tracking file operations

### Step 2: Update Context Package Initialization

Update `angela/context/__init__.py` to expose the new modules and initialize project inference:

```python
"""Context management package for Angela CLI."""

from .manager import context_manager
from .session import session_manager
from .history import history_manager
from .preferences import preferences_manager
from .file_detector import detect_file_type, get_content_preview
from .file_resolver import file_resolver
from .file_activity import file_activity_tracker, ActivityType
from .enhancer import context_enhancer

# Initialize project inference in the background when importing this package
import asyncio
from .project_inference import project_inference

def initialize_project_inference():
    """Initialize project inference for the current project in background."""
    from .manager import context_manager
    if context_manager.project_root:
        asyncio.create_task(
            project_inference.infer_project_info(context_manager.project_root)
        )

# Schedule initialization to run soon but not block import
asyncio.get_event_loop().call_soon(initialize_project_inference)
```

### Step 3: Update the Orchestrator

Update `angela/orchestrator.py` to integrate the new components:

1. Add these imports at the top:
   ```python
   from angela.context.enhancer import context_enhancer
   from angela.context.file_resolver import file_resolver
   from angela.context.file_activity import file_activity_tracker, ActivityType
   from angela.execution.hooks import execution_hooks
   ```

2. Replace the `process_request` method with the enhanced version that:
   - Enhances context with project information
   - Extracts and resolves file references
   - Adds the enhanced context to the AI prompts

3. Replace the `_extract_file_path` method with the one that uses the file resolver

### Step 4: Update the Execution Engine

Update `angela/execution/adaptive_engine.py` to add execution hooks:

1. In the `execute_command` method, add:
   ```python
   # Call pre-execution hook
   await execution_hooks.pre_execute_command(command, context)
   
   # ... existing execution code ...
   
   # Call post-execution hook
   await execution_hooks.post_execute_command(command, result, context)
   ```

### Step 5: Update Prompt Engineering

Update `angela/ai/prompts.py` to use the enhanced context:

1. Add the enhanced project context template
2. Add the recent file activity template
3. Add the resolved file references template
4. Update the `build_prompt` function to incorporate all these templates
5. Update the `build_file_operation_prompt` function with file-specific context

### Step 6: Add CLI Extensions for File Resolution

Add new commands to the CLI to help users work with file references:

1. Create `angela/cli/files_extension.py` with commands for:
   - Resolving file references
   - Extracting references from text
   - Showing recent files
   - Showing most active files
   - Showing project information

2. Update `angela/cli/__init__.py` to include these extensions:
   ```python
   # Import and add the files extensions
   from angela.cli.files_extension import app as files_extensions_app
   
   # Add files extensions to the files app
   from angela.cli.files import app as files_app
   files_app.add_typer(files_extensions_app)
   ```

### Step 7: Add Unit Tests

Add unit tests to validate the new functionality:

1. `tests/test_file_resolver.py` - Tests for file reference resolution
2. `tests/test_context_enhancer.py` - Tests for context enhancement
3. `tests/test_file_activity.py` - Tests for file activity tracking

### Step 8: Update Documentation

Update the project documentation to reflect the new capabilities:

1. Add a section on Enhanced Project Context to the README
2. Create a new `docs/phase6.md` file explaining the new features
3. Update the user guide with examples of using the new commands

## Using the New Features

### Project Type Inference

Angela now automatically detects:
- The type of project you're working on (Python, Node.js, etc.)
- Frameworks used in the project (Flask, React, etc.)
- Dependencies and their versions
- Important project files

This information is used to provide more contextually relevant responses.

### File Reference Resolution

Users can now refer to files in various ways:
- By exact path: `file.txt`, `/path/to/file.txt`
- By description: "the main file", "the configuration file"
- By fuzzy matching: "config" for "config.json"
- By special references: "current file", "last modified file"

The CLI also provides new commands:
- `angela files resolve "reference"` - Resolve a file reference
- `angela files extract "text with references"` - Extract references from text
- `angela files recent` - Show recently accessed files
- `angela files active` - Show most actively used files
- `angela files project` - Show detected project information

### File Activity Tracking

Angela now tracks:
- Files you've viewed, created, modified, or deleted
- Which commands accessed which files
- Most frequently used files

This information helps Angela understand the files that are most important to you and your current context.

## How It All Works Together

1. You make a request: `angela "fix the bug in the main controller"`
2. Angela:
   - Enhances the context with project information
   - Resolves "main controller" to the actual file
   - Checks recent activity on that file
   - Uses all this information to generate a response
   - Tracks the file activity for future context

The result is a much more contextually aware AI that understands your project structure and your file usage patterns.
---
## Directory Structure Integration
### First, ensure all files are in their correct locations:
```
angela/
├── context/
│   ├── __init__.py (updated)
│   ├── enhancer.py (new)
│   ├── file_resolver.py (new)
│   ├── file_activity.py (new)
│   └── ... (existing files)
├── execution/
│   ├── hooks.py (new)
│   ├── adaptive_engine.py (to update)
│   └── ... (existing files)
├── ai/
│   ├── prompts.py (to update)
│   └── ... (existing files)
├── cli/
│   ├── files_extension.py (new)
│   └── ... (existing files)
```
## Troubleshooting

### Project Type Inference Not Working

If project type inference isn't working:
- Make sure you're in a valid project directory
- Try running `angela files project` to see what's detected
- Check logs for any errors

### File References Not Resolving

If file references aren't resolving correctly:
- Try using `angela files resolve "reference"` to debug
- Make sure the file exists in your project
- Try using a more specific reference

### Command Not Tracking File Activity

If file activity isn't being tracked:
- Check that the command actually accessed files
- Try using `angela files recent` to see tracked activities
- Run commands through Angela to ensure they're tracked
