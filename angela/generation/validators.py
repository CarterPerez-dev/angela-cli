# angela/generation/validators.py
"""
Code validation for Angela CLI.

This module provides validators for different programming languages
to ensure generated code is syntactically correct and follows best practices.
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import re

from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Map file extensions to language validators
LANGUAGE_VALIDATORS = {
    ".py": "validate_python",
    ".js": "validate_javascript",
    ".jsx": "validate_javascript",
    ".ts": "validate_typescript",
    ".tsx": "validate_typescript",
    ".java": "validate_java",
    ".go": "validate_go",
    ".rb": "validate_ruby",
    ".rs": "validate_rust",
    ".html": "validate_html",
    ".css": "validate_css",
    ".php": "validate_php"
}

def validate_code(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate code based on file extension.
    
    Args:
        content: Code content to validate
        file_path: Path of the file (used to determine language)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    logger.info(f"Validating code for: {file_path}")
    
    _, extension = os.path.splitext(file_path.lower())
    
    # Get the validator function for this extension
    validator_name = LANGUAGE_VALIDATORS.get(extension)
    
    if validator_name and validator_name in globals():
        validator_func = globals()[validator_name]
        return validator_func(content, file_path)
    
    # If no specific validator, do basic checks
    return validate_generic(content, file_path)

def validate_generic(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Generic validator for any code file.
    
    Args:
        content: Code content to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for basic issues like unmatched brackets
    bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
    
    for opening, closing in bracket_pairs:
        if content.count(opening) != content.count(closing):
            return False, f"Unmatched brackets: {opening}{closing}"
    
    return True, ""

def validate_python(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate Python code.
    
    Args:
        content: Python code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(content.encode('utf-8'))
    
    try:
        # Use Python's compile function to check syntax
        result = subprocess.run(
            ['python', '-m', 'py_compile', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Parse the error message
            error_msg = result.stderr
            
            # Simplify the error message
            error_lines = error_msg.splitlines()
            for line in error_lines:
                if "File " in line and ", line " in line:
                    continue
                if line.strip():
                    error_msg = line.strip()
                    break
            
            return False, f"Python syntax error: {error_msg}"
        
        # Additional checks for common Python issues
        issues = []
        
        # Check for undefined or unused imports
        import_lines = []
        imported_modules = []
        
        for line in content.splitlines():
            if line.strip().startswith(('import ', 'from ')):
                import_lines.append(line)
                
                if line.strip().startswith('import '):
                    modules = line.strip()[7:].split(',')
                    for module in modules:
                        if ' as ' in module:
                            module = module.split(' as ')[1]
                        imported_modules.append(module.strip())
                elif line.strip().startswith('from '):
                    parts = line.strip().split(' import ')
                    if len(parts) == 2:
                        modules = parts[1].split(',')
                        for module in modules:
                            if ' as ' in module:
                                module = module.split(' as ')[1]
                            imported_modules.append(module.strip())
        
        # Check if imports are used
        for module in imported_modules:
            if module not in content.replace(f"import {module}", "").replace(f"from {module}", ""):
                issues.append(f"Potentially unused import: {module}")
        
        # If we found issues but not syntax errors, still consider it valid
        # but report the issues
        if issues:
            return True, f"Code is valid but has issues: {'; '.join(issues)}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating Python code: {str(e)}")
        return False, f"Error validating Python code: {str(e)}"
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def validate_javascript(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate JavaScript code.
    
    Args:
        content: JavaScript code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if node is available
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Node.js not found, falling back to basic JS validation")
        return validate_javascript_basic(content, file_path)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(content.encode('utf-8'))
    
    try:
        # Use Node.js to check syntax
        result = subprocess.run(
            ['node', '--check', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Parse the error message
            error_msg = result.stderr
            return False, f"JavaScript syntax error: {error_msg.strip()}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating JavaScript code: {str(e)}")
        return False, f"Error validating JavaScript code: {str(e)}"
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def validate_javascript_basic(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Basic validation for JavaScript code without using Node.js.
    
    Args:
        content: JavaScript code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for basic syntax issues
    
    # Check for unmatched brackets
    bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
    
    for opening, closing in bracket_pairs:
        if content.count(opening) != content.count(closing):
            return False, f"Unmatched brackets: {opening}{closing}"
    
    # Check for missing semicolons (simplified)
    lines = content.splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.endswith(';') and not line.endswith('{') and not line.endswith('}') and \
           not line.endswith(':') and not line.startswith('//') and not line.startswith('/*') and \
           not line.endswith('*/') and not line.startswith('import ') and not line.startswith('export '):
            # This is a simplistic check and might have false positives
            logger.debug(f"Line {i+1} might be missing a semicolon: {line}")
    
    # Check for common React/JSX issues if it seems to be a React file
    if ".jsx" in file_path or "React" in content or "react" in content:
        # Check if JSX elements are closed
        jsx_tags = re.findall(r'<([a-zA-Z0-9]+)(?:\s+[^>]*)?>', content)
        for tag in jsx_tags:
            if tag[0].isupper() and f"</{tag}>" not in content and "/>" not in content:
                return False, f"Unclosed JSX element: <{tag}>"
    
    return True, ""

def validate_typescript(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate TypeScript code.
    
    Args:
        content: TypeScript code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if tsc is available
    try:
        subprocess.run(['tsc', '--version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("TypeScript compiler not found, falling back to JavaScript validation")
        return validate_javascript(content, file_path)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(content.encode('utf-8'))
    
    try:
        # Use tsc to check syntax (without emitting JS files)
        result = subprocess.run(
            ['tsc', '--noEmit', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Parse the error message
            error_msg = result.stderr or result.stdout
            return False, f"TypeScript error: {error_msg.strip()}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating TypeScript code: {str(e)}")
        return False, f"Error validating TypeScript code: {str(e)}"
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def validate_java(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate Java code.
    
    Args:
        content: Java code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if javac is available
    try:
        subprocess.run(['javac', '-version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Java compiler not found, falling back to basic Java validation")
        return validate_java_basic(content, file_path)
    
    # Extract class name from the code
    class_name = None
    class_match = re.search(r'public\s+class\s+(\w+)', content)
    if class_match:
        class_name = class_match.group(1)
    else:
        # Try to get class name from file path
        base_name = os.path.basename(file_path)
        if base_name.endswith('.java'):
            class_name = base_name[:-5]
    
    if not class_name:
        return False, "Could not determine Java class name"
    
    # Update content to match class name from file if needed
    if class_match and class_match.group(1) != class_name:
        content = content.replace(f"class {class_match.group(1)}", f"class {class_name}")
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.java', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(content.encode('utf-8'))
    
    try:
        # Use javac to check syntax
        result = subprocess.run(
            ['javac', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Parse the error message
            error_msg = result.stderr
            return False, f"Java syntax error: {error_msg.strip()}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating Java code: {str(e)}")
        return False, f"Error validating Java code: {str(e)}"
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def validate_java_basic(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Basic validation for Java code without using javac.
    
    Args:
        content: Java code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for basic syntax issues
    
    # Check for unmatched brackets
    bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
    
    for opening, closing in bracket_pairs:
        if content.count(opening) != content.count(closing):
            return False, f"Unmatched brackets: {opening}{closing}"
    
    # Check for missing semicolons (simplified)
    lines = content.splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.endswith(';') and not line.endswith('{') and not line.endswith('}') and \
           not line.endswith(':') and not line.startswith('//') and not line.startswith('/*') and \
           not line.endswith('*/'):
            if not any(keyword in line for keyword in ['class ', 'interface ', 'enum ', 'import ', 'package ']):
                # This is a simplistic check and might have false positives
                logger.debug(f"Line {i+1} might be missing a semicolon: {line}")
    
    # Check for class name matching file name
    class_match = re.search(r'public\s+class\s+(\w+)', content)
    if class_match:
        class_name = class_match.group(1)
        base_name = os.path.basename(file_path)
        if base_name.endswith('.java') and base_name[:-5] != class_name:
            return False, f"Class name '{class_name}' does not match file name '{base_name[:-5]}'"
    
    return True, ""

def validate_go(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate Go code.
    
    Args:
        content: Go code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if go is available
    try:
        subprocess.run(['go', 'version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Go compiler not found, falling back to basic Go validation")
        return validate_go_basic(content, file_path)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.go', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(content.encode('utf-8'))
    
    try:
        # Use go vet to check syntax and common issues
        result = subprocess.run(
            ['go', 'vet', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Parse the error message
            error_msg = result.stderr
            return False, f"Go error: {error_msg.strip()}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating Go code: {str(e)}")
        return False, f"Error validating Go code: {str(e)}"
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def validate_go_basic(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Basic validation for Go code without using go compiler.
    
    Args:
        content: Go code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for basic syntax issues
    
    # Check for unmatched brackets
    bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
    
    for opening, closing in bracket_pairs:
        if content.count(opening) != content.count(closing):
            return False, f"Unmatched brackets: {opening}{closing}"
    
    # Check for package declaration
    if not re.search(r'package\s+\w+', content):
        return False, "Missing package declaration"
    
    return True, ""

def validate_ruby(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate Ruby code.
    
    Args:
        content: Ruby code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if ruby is available
    try:
        subprocess.run(['ruby', '--version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Ruby interpreter not found, falling back to basic Ruby validation")
        return validate_ruby_basic(content, file_path)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.rb', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(content.encode('utf-8'))
    
    try:
        # Use ruby -c to check syntax
        result = subprocess.run(
            ['ruby', '-c', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Parse the error message
            error_msg = result.stderr
            return False, f"Ruby syntax error: {error_msg.strip()}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating Ruby code: {str(e)}")
        return False, f"Error validating Ruby code: {str(e)}"
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def validate_ruby_basic(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Basic validation for Ruby code without using ruby interpreter.
    
    Args:
        content: Ruby code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for basic syntax issues
    
    # Check for unmatched brackets
    bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
    
    for opening, closing in bracket_pairs:
        if content.count(opening) != content.count(closing):
            return False, f"Unmatched brackets: {opening}{closing}"
    
    # Check for unmatched 'do' blocks
    do_count = len(re.findall(r'\bdo\b(?:\s*\|.*?\|)?', content))
    end_count = len(re.findall(r'\bend\b', content))
    
    if do_count != end_count:
        return False, f"Unmatched 'do' and 'end' blocks: {do_count} 'do' vs {end_count} 'end'"
    
    return True, ""

def validate_rust(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate Rust code.
    
    Args:
        content: Rust code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if rustc is available
    try:
        subprocess.run(['rustc', '--version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Rust compiler not found, falling back to basic Rust validation")
        return validate_rust_basic(content, file_path)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.rs', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(content.encode('utf-8'))
    
    try:
        # Use rustc to check syntax (with --emit=metadata to avoid producing binaries)
        result = subprocess.run(
            ['rustc', '--emit=metadata', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Parse the error message
            error_msg = result.stderr
            return False, f"Rust syntax error: {error_msg.strip()}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating Rust code: {str(e)}")
        return False, f"Error validating Rust code: {str(e)}"
    
    finally:
        # Clean up the temporary files
        try:
            os.unlink(tmp_path)
            # Also try to remove any generated metadata files
            metadata_path = tmp_path.replace('.rs', '')
            if os.path.exists(metadata_path):
                os.unlink(metadata_path)
        except Exception:
            pass

def validate_rust_basic(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Basic validation for Rust code without using rustc.
    
    Args:
        content: Rust code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for basic syntax issues
    
    # Check for unmatched brackets
    bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
    
    for opening, closing in bracket_pairs:
        if content.count(opening) != content.count(closing):
            return False, f"Unmatched brackets: {opening}{closing}"
    
    return True, ""

def validate_html(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate HTML code.
    
    Args:
        content: HTML code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic HTML validation without external tools
    
    # Check for DOCTYPE declaration
    if not re.search(r'<!DOCTYPE\s+html>', content, re.IGNORECASE):
        logger.warning("HTML file missing DOCTYPE declaration")
    
    # Check for basic required elements
    if not re.search(r'<html', content, re.IGNORECASE):
        return False, "Missing <html> element"
    
    if not re.search(r'<head', content, re.IGNORECASE):
        return False, "Missing <head> element"
    
    if not re.search(r'<body', content, re.IGNORECASE):
        return False, "Missing <body> element"
    
    # Check for unmatched tags (simplified)
    html_tags = re.findall(r'<([a-zA-Z0-9]+)[^>]*>', content)
    void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 
                     'link', 'meta', 'param', 'source', 'track', 'wbr'}
    
    tag_stack = []
    
    for tag in html_tags:
        tag_lower = tag.lower()
        if tag_lower not in void_elements:
            tag_stack.append(tag_lower)
    
    closing_tags = re.findall(r'</([a-zA-Z0-9]+)>', content)
    
    for tag in closing_tags:
        tag_lower = tag.lower()
        if tag_stack and tag_stack[-1] == tag_lower:
            tag_stack.pop()
        else:
            return False, f"Unmatched closing tag: </
            
            
def validate_css(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate CSS code.
    
    Args:
        content: CSS code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic CSS validation without external tools
    
    # Check for unmatched brackets
    if content.count('{') != content.count('}'):
        return False, "Unmatched brackets in CSS"
    
    # Check for missing semicolons in property declarations
    lines = content.splitlines()
    in_rule_block = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if not line or line.startswith('/*') or line.endswith('*/'):
            continue
        
        if '{' in line:
            in_rule_block = True
            continue
            
        if '}' in line:
            in_rule_block = False
            continue
        
        if in_rule_block and ':' in line and not line.endswith(';') and not line.endswith('{'):
            # This might be a property without a semicolon
            # Check if it's not the last property in a block
            next_line_idx = i + 1
            while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                next_line_idx += 1
                
            if next_line_idx < len(lines) and not lines[next_line_idx].strip().startswith('}'):
                return False, f"Missing semicolon at line {i+1}: {line}"
    
    return True, ""

def validate_php(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Validate PHP code.
    
    Args:
        content: PHP code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if php is available
    try:
        subprocess.run(['php', '--version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("PHP interpreter not found, falling back to basic PHP validation")
        return validate_php_basic(content, file_path)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.php', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(content.encode('utf-8'))
    
    try:
        # Use php -l to check syntax
        result = subprocess.run(
            ['php', '-l', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Parse the error message
            error_msg = result.stderr or result.stdout
            return False, f"PHP syntax error: {error_msg.strip()}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating PHP code: {str(e)}")
        return False, f"Error validating PHP code: {str(e)}"
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def validate_php_basic(content: str, file_path: str) -> Tuple[bool, str]:
    """
    Basic validation for PHP code without using php interpreter.
    
    Args:
        content: PHP code to validate
        file_path: Path of the file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for basic syntax issues
    
    # Check for PHP opening tag
    if not re.search(r'<\?php', content):
        return False, "Missing PHP opening tag (<?php)"
    
    # Check for unmatched brackets
    bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
    
    for opening, closing in bracket_pairs:
        if content.count(opening) != content.count(closing):
            return False, f"Unmatched brackets: {opening}{closing}"
    
    return True, ""
