# tests/test_prompt_building.py
"""Tests for prompt building functionality."""
import pytest

from angela.ai.prompts import build_prompt


def test_build_prompt_basic():
    """Test building a basic prompt."""
    request = "Find all Python files"
    context = {
        "cwd": "/home/user/project",
    }
    
    prompt = build_prompt(request, context)
    
    # Check that the prompt contains the request
    assert request in prompt
    
    # Check that the context is included
    assert "Current working directory: /home/user/project" in prompt
    
    # Check that the system instructions are included
    assert "You are Angela, an AI-powered command-line assistant" in prompt
    
    # Check that the response format is included
    assert "Expected response format" in prompt


def test_build_prompt_full_context():
    """Test building a prompt with full context."""
    request = "Show me files modified in the last week"
    context = {
        "cwd": "/home/user/project/src",
        "project_root": "/home/user/project",
        "project_type": "python",
        "relative_path": "src",
    }
    
    prompt = build_prompt(request, context)
    
    # Check that all context elements are included
    assert "Current working directory: /home/user/project/src" in prompt
    assert "Project root: /home/user/project" in prompt
    assert "Project type: python" in prompt
    assert "Path relative to project root: src" in prompt


def test_build_prompt_examples():
    """Test that examples are included in the prompt."""
    request = "List all files"
    context = {"cwd": "/home/user"}
    
    prompt = build_prompt(request, context)
    
    # Check that examples are included
    assert "Examples:" in prompt
    assert "User request: Find all Python files in this project" in prompt
    assert "User request: Show me disk usage for the current directory" in prompt


def test_build_prompt_length():
    """Test that the prompt doesn't exceed a reasonable length."""
    request = "A very long request " + "with lots of words " * 20
    context = {
        "cwd": "/home/user/project",
        "project_root": "/home/user/project",
        "project_type": "python",
    }
    
    prompt = build_prompt(request, context)
    
    # Check that the prompt isn't unreasonably long
    # (Adjust the length based on your token limit considerations)
    assert len(prompt) < 10000, "Prompt is too long"
