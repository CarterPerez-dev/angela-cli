"""
Tests for file type detection.
"""
import os
import pytest
import tempfile
from pathlib import Path

from angela.context.file_detector import detect_file_type, get_content_preview


@pytest.fixture
def temp_file_dir():
    """Create a temporary directory for file testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_detect_text_file(temp_file_dir):
    """Test detection of basic text files."""
    # Create a Python file
    python_file = temp_file_dir / "example.py"
    python_file.write_text('#!/usr/bin/env python\nprint("Hello, world!")')
    
    info = detect_file_type(python_file)
    assert info["type"] == "source_code"
    assert info["language"] == "Python"
    assert info["binary"] is False
    
    # Create a simple text file
    text_file = temp_file_dir / "example.txt"
    text_file.write_text("This is a plain text file.")
    
    info = detect_file_type(text_file)
    assert info["type"] != "binary"
    assert info["binary"] is False
    
    # Create an HTML file
    html_file = temp_file_dir / "example.html"
    html_file.write_text("<html><body><h1>Hello</h1></body></html>")
    
    info = detect_file_type(html_file)
    assert info["type"] == "source_code"
    assert info["language"] == "HTML"
    assert info["mime_type"] is not None


def test_detect_binary_file(temp_file_dir):
    """Test detection of binary files."""
    # Create a simple binary file
    binary_file = temp_file_dir / "binary.bin"
    with open(binary_file, "wb") as f:
        f.write(b"\x00\x01\x02\x03\xFF")
    
    info = detect_file_type(binary_file)
    assert info["binary"] is True
    
    # Create a simulated image file
    image_file = temp_file_dir / "image.jpg"
    with open(image_file, "wb") as f:
        # JPEG file header signature
        f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF")
        f.write(bytes(100))
    
    info = detect_file_type(image_file)
    assert info["type"] in ["image", "binary"]
    assert "image" in info["mime_type"].lower()
    assert info["binary"] is True


def test_detect_common_config_files(temp_file_dir):
    """Test detection of common configuration files by name."""
    # Create a .gitignore file
    git_file = temp_file_dir / ".gitignore"
    git_file.write_text("*.pyc\n__pycache__/")
    
    info = detect_file_type(git_file)
    assert info["type"] == "Git"
    
    # Create a package.json file
    pkg_file = temp_file_dir / "package.json"
    pkg_file.write_text('{"name": "test", "version": "1.0.0"}')
    
    info = detect_file_type(pkg_file)
    assert info["type"] == "Node.js"
    
    # Create a requirements.txt file
    req_file = temp_file_dir / "requirements.txt"
    req_file.write_text("pytest\nrequests")
    
    info = detect_file_type(req_file)
    assert info["type"] == "Python"
    
    # Create a Dockerfile
    docker_file = temp_file_dir / "Dockerfile"
    docker_file.write_text("FROM python:3.9\nWORKDIR /app")
    
    info = detect_file_type(docker_file)
    assert info["type"] == "Docker"


def test_detect_by_shebang(temp_file_dir):
    """Test detection by shebang line."""
    # Create a file with bash shebang but no extension
    bash_file = temp_file_dir / "script"
    bash_file.write_text("#!/bin/bash\necho 'Hello, world!'")
    
    info = detect_file_type(bash_file)
    assert info["language"] == "Bash"
    assert info["type"] == "source_code"
    
    # Create a file with Python shebang but no extension
    python_file = temp_file_dir / "pyscript"
    python_file.write_text("#!/usr/bin/env python3\nprint('Hello, world!')")
    
    info = detect_file_type(python_file)
    assert info["language"] == "Python"
    assert info["type"] == "source_code"


def test_get_content_preview(temp_file_dir):
    """Test getting content previews."""
    # Create a text file
    text_file = temp_file_dir / "example.txt"
    text_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
    
    preview = get_content_preview(text_file, max_lines=3)
    assert "Line 1" in preview
    assert "Line 3" in preview
    assert "Line 4" not in preview
    
    # Test preview of large file
    large_file = temp_file_dir / "large.txt"
    large_file.write_text("\n".join([f"Line {i}" for i in range(1, 100)]))
    
    preview = get_content_preview(large_file, max_lines=5)
    assert "Line 1" in preview
    assert "Line 5" in preview
    assert "Line 6" not in preview
    assert "..." in preview
    
    # Test preview of binary file
    binary_file = temp_file_dir / "binary.bin"
    with open(binary_file, "wb") as f:
        f.write(b"\x00\x01\x02\x03\xFF")
    
    preview = get_content_preview(binary_file)
    assert preview == "[Binary file]"
    
    # Test preview of nonexistent file
    nonexistent = temp_file_dir / "nonexistent.txt"
    preview = get_content_preview(nonexistent)
    assert preview is None
