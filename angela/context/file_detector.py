"""
File type detection for Angela CLI.

This module provides functionality to detect file types and languages
to enhance context awareness for operations.
"""
import re
import os
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize mimetypes
mimetypes.init()

# Map of file extensions to programming languages
LANGUAGE_EXTENSIONS = {
    # Web
    '.html': 'HTML',
    '.htm': 'HTML',
    '.css': 'CSS',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript (React)',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript (React)',
    
    # Python
    '.py': 'Python',
    '.pyi': 'Python Interface',
    '.pyx': 'Cython',
    '.ipynb': 'Jupyter Notebook',
    
    # Ruby
    '.rb': 'Ruby',
    '.erb': 'Ruby (ERB)',
    '.rake': 'Ruby (Rake)',
    
    # Java/JVM
    '.java': 'Java',
    '.kt': 'Kotlin',
    '.groovy': 'Groovy',
    '.scala': 'Scala',
    
    # C/C++
    '.c': 'C',
    '.h': 'C Header',
    '.cpp': 'C++',
    '.cc': 'C++',
    '.hpp': 'C++ Header',
    
    # C#
    '.cs': 'C#',
    
    # Go
    '.go': 'Go',
    
    # Rust
    '.rs': 'Rust',
    
    # Swift
    '.swift': 'Swift',
    
    # PHP
    '.php': 'PHP',
    
    # Shell
    '.sh': 'Shell (Bash)',
    '.bash': 'Bash',
    '.zsh': 'Zsh',
    '.fish': 'Fish',
    
    # Configuration
    '.json': 'JSON',
    '.yaml': 'YAML',
    '.yml': 'YAML',
    '.toml': 'TOML',
    '.ini': 'INI',
    '.cfg': 'Config',
    '.conf': 'Config',
    
    # Markup
    '.md': 'Markdown',
    '.rst': 'reStructuredText',
    '.xml': 'XML',
    '.svg': 'SVG',
    
    # Data
    '.csv': 'CSV',
    '.tsv': 'TSV',
    '.txt': 'Text',
    '.log': 'Log',
    
    # Documents
    '.pdf': 'PDF',
    '.doc': 'MS Word',
    '.docx': 'MS Word',
    '.xls': 'MS Excel',
    '.xlsx': 'MS Excel',
    '.ppt': 'MS PowerPoint',
    '.pptx': 'MS PowerPoint',
    
    # Images
    '.jpg': 'JPEG Image',
    '.jpeg': 'JPEG Image',
    '.png': 'PNG Image',
    '.gif': 'GIF Image',
    '.bmp': 'BMP Image',
    '.webp': 'WebP Image',
    
    # Audio
    '.mp3': 'MP3 Audio',
    '.wav': 'WAV Audio',
    '.ogg': 'OGG Audio',
    '.flac': 'FLAC Audio',
    
    # Video
    '.mp4': 'MP4 Video',
    '.avi': 'AVI Video',
    '.mkv': 'MKV Video',
    '.mov': 'MOV Video',
    
    # Archives
    '.zip': 'ZIP Archive',
    '.tar': 'TAR Archive',
    '.gz': 'GZIP Archive',
    '.bz2': 'BZIP2 Archive',
    '.xz': 'XZ Archive',
    '.7z': '7-Zip Archive',
    '.rar': 'RAR Archive',
    
    # Executables
    '.exe': 'Windows Executable',
    '.dll': 'Windows Library',
    '.so': 'Shared Object',
    '.dylib': 'macOS Library',
    
    # Other
    '.sql': 'SQL',
    '.db': 'Database',
    '.sqlite': 'SQLite Database',
}

# Mapping of file names to types
FILENAME_MAPPING = {
    'Dockerfile': 'Docker',
    'docker-compose.yml': 'Docker Compose',
    'docker-compose.yaml': 'Docker Compose',
    '.dockerignore': 'Docker',
    'Makefile': 'Makefile',
    'CMakeLists.txt': 'CMake',
    'package.json': 'Node.js',
    'package-lock.json': 'Node.js',
    'yarn.lock': 'Yarn',
    'requirements.txt': 'Python',
    'setup.py': 'Python',
    'pyproject.toml': 'Python',
    'Pipfile': 'Python (Pipenv)',
    'Pipfile.lock': 'Python (Pipenv)',
    'Gemfile': 'Ruby',
    'Gemfile.lock': 'Ruby',
    'build.gradle': 'Gradle',
    'build.gradle.kts': 'Gradle (Kotlin)',
    'pom.xml': 'Maven',
    'Cargo.toml': 'Rust',
    'Cargo.lock': 'Rust',
    '.gitignore': 'Git',
    '.gitattributes': 'Git',
    '.gitlab-ci.yml': 'GitLab CI',
    '.travis.yml': 'Travis CI',
    'Jenkinsfile': 'Jenkins',
    '.editorconfig': 'EditorConfig',
    '.eslintrc': 'ESLint',
    '.eslintrc.js': 'ESLint',
    '.eslintrc.json': 'ESLint',
    '.prettierrc': 'Prettier',
    '.prettierrc.js': 'Prettier',
    '.prettierrc.json': 'Prettier',
    'tsconfig.json': 'TypeScript',
    'tslint.json': 'TSLint',
    '.babelrc': 'Babel',
    'babel.config.js': 'Babel',
    'webpack.config.js': 'Webpack',
    'rollup.config.js': 'Rollup',
    'vite.config.js': 'Vite',
    'jest.config.js': 'Jest',
    '.env': 'Environment Variables',
    '.env.example': 'Environment Variables',
    'README.md': 'Documentation',
    'LICENSE': 'License',
    'CHANGELOG.md': 'Changelog',
    'CONTRIBUTING.md': 'Documentation',
    'CODE_OF_CONDUCT.md': 'Documentation',
}

# Language-specific shebang patterns
SHEBANG_PATTERNS = [
    (r'^#!/bin/bash', 'Bash'),
    (r'^#!/usr/bin/env\s+bash', 'Bash'),
    (r'^#!/bin/sh', 'Shell'),
    (r'^#!/usr/bin/env\s+sh', 'Shell'),
    (r'^#!/usr/bin/python', 'Python'),
    (r'^#!/usr/bin/env\s+python', 'Python'),
    (r'^#!/usr/bin/node', 'JavaScript'),
    (r'^#!/usr/bin/env\s+node', 'JavaScript'),
    (r'^#!/usr/bin/ruby', 'Ruby'),
    (r'^#!/usr/bin/env\s+ruby', 'Ruby'),
    (r'^#!/usr/bin/perl', 'Perl'),
    (r'^#!/usr/bin/env\s+perl', 'Perl'),
    (r'^#!/usr/bin/php', 'PHP'),
    (r'^#!/usr/bin/env\s+php', 'PHP'),
]


def detect_file_type(path: Path) -> Dict[str, Any]:
    """
    Detect the type of a file based on extension, content, and other heuristics.
    
    Args:
        path: The path to the file.
        
    Returns:
        A dictionary with file type information including:
            - type: General file type
            - language: Programming language (if applicable)
            - mime_type: MIME type
            - binary: Whether the file is binary
            - encoding: File encoding (if applicable)
    """
    result = {
        'type': 'unknown',
        'language': None,
        'mime_type': None,
        'binary': False,
        'encoding': None,
    }
    
    try:
        if not path.exists():
            return result
        
        # Check if it's a directory
        if path.is_dir():
            result['type'] = 'directory'
            return result
        
        # Get file name and extension
        name = path.name
        extension = path.suffix.lower()
        
        # Check if it's a known file by name
        if name in FILENAME_MAPPING:
            result['type'] = FILENAME_MAPPING[name]
            
        # Get MIME type
        mime_type, encoding = mimetypes.guess_type(str(path))
        if mime_type:
            result['mime_type'] = mime_type
            result['encoding'] = encoding
            
            # Get general type from MIME
            main_type = mime_type.split('/')[0]
            result['type'] = main_type
        
        # Detect language based on extension
        if extension in LANGUAGE_EXTENSIONS:
            result['language'] = LANGUAGE_EXTENSIONS[extension]
            result['type'] = 'source_code'
        
        # For text files without a clear type, check for shebangs
        if extension in ['.txt', ''] or not result['language']:
            try:
                # Read the first line of the file
                with open(path, 'r', errors='ignore') as f:
                    first_line = f.readline().strip()
                
                # Check for shebang patterns
                for pattern, language in SHEBANG_PATTERNS:
                    if re.match(pattern, first_line):
                        result['language'] = language
                        result['type'] = 'source_code'
                        break
            except UnicodeDecodeError:
                # File is likely binary
                result['binary'] = True
                result['type'] = 'binary'
        
        # Check if the file is binary
        if not result['binary'] and not result['type'] == 'directory':
            try:
                with open(path, 'rb') as f:
                    chunk = f.read(4096)
                    # Check for null bytes (common in binary files)
                    if b'\0' in chunk:
                        result['binary'] = True
                        if not result['type'] or result['type'] == 'unknown':
                            result['type'] = 'binary'
            except IOError:
                pass
        
        return result
    
    except Exception as e:
        logger.exception(f"Error detecting file type for {path}: {str(e)}")
        return result


def get_content_preview(path: Path, max_lines: int = 10, max_chars: int = 1000) -> Optional[str]:
    """
    Get a preview of a file's content.
    
    Args:
        path: The path to the file.
        max_lines: Maximum number of lines to preview.
        max_chars: Maximum number of characters to preview.
        
    Returns:
        A string with the file preview, or None if the file is not readable.
    """
    try:
        if not path.exists() or not path.is_file():
            return None
        
        # Check file type
        file_info = detect_file_type(path)
        if file_info['binary']:
            return "[Binary file]"
        
        # Read the file content
        with open(path, 'r', errors='replace') as f:
            lines = []
            total_chars = 0
            
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append("...")
                    break
                
                if total_chars + len(line) > max_chars:
                    # Truncate the line if it would exceed max_chars
                    available_chars = max_chars - total_chars
                    if available_chars > 3:
                        lines.append(line[:available_chars - 3] + "...")
                    break
                
                lines.append(line.rstrip('\n'))
                total_chars += len(line)
        
        return '\n'.join(lines)
    
    except Exception as e:
        logger.exception(f"Error getting content preview for {path}: {str(e)}")
        return None
