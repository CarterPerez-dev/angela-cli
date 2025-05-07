# angela/toolchain/test_frameworks.py
"""
Test framework integration for Angela CLI.

This module provides functionality for integrating with test frameworks
and generating test files for generated code.
"""
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import importlib
import inspect

from angela.utils.logging import get_logger
from angela.generation.engine import CodeFile
from angela.context import context_manager

logger = get_logger(__name__)

class TestFrameworkIntegration:
    """
    Integration with test frameworks for automated testing.
    """
    
    def __init__(self):
        """Initialize the test framework integration."""
        self._logger = logger
        
        # Map of project types to test frameworks
        self._test_frameworks = {
            "python": ["pytest", "unittest"],
            "node": ["jest", "mocha"],
            "ruby": ["rspec", "minitest"],
            "go": ["go_test"],
            "rust": ["cargo_test"],
            "java": ["junit", "testng"]
        }
    
    async def detect_test_framework(
        self, 
        path: Union[str, Path],
        project_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect the test framework used in a project.
        
        Args:
            path: Path to the project
            project_type: Optional type of project
            
        Returns:
            Dictionary with the detected test framework info
        """
        self._logger.info(f"Detecting test framework in {path}")
        
        path_obj = Path(path)
        
        # Check if path exists
        if not path_obj.exists() or not path_obj.is_dir():
            return {
                "detected": False,
                "error": f"Path does not exist or is not a directory: {path}",
                "test_framework": None,
                "project_type": project_type
            }
        
        # Determine project type if not provided
        if project_type is None:
            # Try to detect from context
            context = context_manager.get_context_dict()
            if context.get("project_type"):
                project_type = context["project_type"]
            else:
                # Try to infer from files
                if (path_obj / "requirements.txt").exists() or (path_obj / "setup.py").exists():
                    project_type = "python"
                elif (path_obj / "package.json").exists():
                    project_type = "node"
                elif (path_obj / "Gemfile").exists():
                    project_type = "ruby"
                elif (path_obj / "go.mod").exists():
                    project_type = "go"
                elif (path_obj / "Cargo.toml").exists():
                    project_type = "rust"
                elif (path_obj / "pom.xml").exists() or (path_obj / "build.gradle").exists():
                    project_type = "java"
        
        # Files that indicate test frameworks
        test_framework_files = {
            "python": {
                "pytest.ini": "pytest",
                "conftest.py": "pytest",
                "test_*.py": "pytest",  # Pattern for pytest files
                "*_test.py": "unittest"  # Pattern for unittest files
            },
            "node": {
                "jest.config.js": "jest",
                "jest.config.ts": "jest",
                "package.json": "jest",  # Need to check content for jest dependency
                "mocha.opts": "mocha",
                ".mocharc.js": "mocha",
                ".mocharc.json": "mocha"
            },
            "ruby": {
                ".rspec": "rspec",
                "spec_helper.rb": "rspec",
                "test_helper.rb": "minitest"
            },
            "go": {
                "*_test.go": "go_test"  # Pattern for Go test files
            },
            "rust": {
                "**/tests/*.rs": "cargo_test"  # Pattern for Rust test files
            },
            "java": {
                "pom.xml": "junit",  # Need to check content for junit dependency
                "build.gradle": "junit"  # Need to check content for junit dependency
            }
        }
        
        # Check for test framework files based on project type
        if project_type in test_framework_files:
            for file_pattern, framework in test_framework_files[project_type].items():
                # Check for exact file matches
                if not file_pattern.startswith("*"):
                    if (path_obj / file_pattern).exists():
                        # For package.json, check if jest is a dependency
                        if file_pattern == "package.json" and framework == "jest":
                            try:
                                import json
                                with open(path_obj / file_pattern, 'r') as f:
                                    package_data = json.load(f)
                                
                                # Check for jest in dependencies or devDependencies
                                deps = package_data.get("dependencies", {})
                                dev_deps = package_data.get("devDependencies", {})
                                
                                if "jest" in deps or "jest" in dev_deps:
                                    return {
                                        "detected": True,
                                        "test_framework": framework,
                                        "project_type": project_type,
                                        "indicator_file": file_pattern
                                    }
                                # If jest not found, check for mocha
                                elif "mocha" in deps or "mocha" in dev_deps:
                                    return {
                                        "detected": True,
                                        "test_framework": "mocha",
                                        "project_type": project_type,
                                        "indicator_file": file_pattern
                                    }
                            except Exception:
                                pass
                        else:
                            return {
                                "detected": True,
                                "test_framework": framework,
                                "project_type": project_type,
                                "indicator_file": file_pattern
                            }
                else:
                    # Check for pattern matches
                    pattern = file_pattern.replace("*", "**")
                    matches = list(path_obj.glob(pattern))
                    if matches:
                        return {
                            "detected": True,
                            "test_framework": framework,
                            "project_type": project_type,
                            "indicator_file": str(matches[0].relative_to(path_obj))
                        }
        
        # If no specific test framework detected, use default for project type
        if project_type in self._test_frameworks:
            default_framework = self._test_frameworks[project_type][0]
            return {
                "detected": False,
                "test_framework": default_framework,
                "project_type": project_type,
                "indicator_file": None,
                "message": f"No test framework detected, defaulting to {default_framework}"
            }
        
        return {
            "detected": False,
            "error": f"Unable to detect test framework for project type: {project_type}",
            "test_framework": None,
            "project_type": project_type
        }
    
    async def generate_test_files(
        self, 
        src_files: List[CodeFile],
        test_framework: Optional[str] = None,
        project_type: Optional[str] = None,
        test_dir: Optional[str] = None,
        root_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate test files for source files.
        
        Args:
            src_files: List of source files to generate tests for
            test_framework: Optional test framework to use
            project_type: Optional project type
            test_dir: Optional directory for test files
            root_dir: Optional root directory of the project
            
        Returns:
            Dictionary with the test generation result
        """
        self._logger.info(f"Generating test files for {len(src_files)} source files")
        
        # Get project root
        if root_dir is None:
            root_dir = context_manager.get_context_dict().get("project_root", os.getcwd())
        
        root_path = Path(root_dir)
        
        # Detect project type if not provided
        if project_type is None:
            # Try to detect from context
            context = context_manager.get_context_dict()
            if context.get("project_type"):
                project_type = context["project_type"]
            else:
                # Try to infer from files
                if (root_path / "requirements.txt").exists() or (root_path / "setup.py").exists():
                    project_type = "python"
                elif (root_path / "package.json").exists():
                    project_type = "node"
                elif (root_path / "Gemfile").exists():
                    project_type = "ruby"
                elif (root_path / "go.mod").exists():
                    project_type = "go"
                elif (root_path / "Cargo.toml").exists():
                    project_type = "rust"
                elif (root_path / "pom.xml").exists() or (root_path / "build.gradle").exists():
                    project_type = "java"
        
        # Detect test framework if not provided
        if test_framework is None:
            detection_result = await self.detect_test_framework(root_path, project_type)
            test_framework = detection_result.get("test_framework")
            
            if not test_framework:
                # Use default for project type
                if project_type in self._test_frameworks:
                    test_framework = self._test_frameworks[project_type][0]
                else:
                    return {
                        "success": False,
                        "error": "Unable to determine test framework",
                        "test_framework": None,
                        "project_type": project_type
                    }
        
        # Determine test directory
        if test_dir is None:
            if project_type == "python":
                if (root_path / "tests").exists():
                    test_dir = "tests"
                else:
                    test_dir = "test"
            elif project_type == "node":
                if (root_path / "tests").exists():
                    test_dir = "tests"
                elif (root_path / "__tests__").exists():
                    test_dir = "__tests__"
                else:
                    test_dir = "test"
            elif project_type == "ruby":
                if (root_path / "spec").exists():
                    test_dir = "spec"
                else:
                    test_dir = "test"
            elif project_type == "go":
                test_dir = "."  # Go tests are usually in the same directory
            elif project_type == "rust":
                test_dir = "tests"
            elif project_type == "java":
                test_dir = "src/test/java"
            else:
                test_dir = "tests"
        
        test_path = root_path / test_dir
        
        # Create test directory if it doesn't exist
        if not test_path.exists():
            os.makedirs(test_path, exist_ok=True)
        
        # Generate test files based on framework
        if test_framework == "pytest":
            return await self._generate_pytest_files(src_files, test_path, root_path)
        elif test_framework == "unittest":
            return await self._generate_unittest_files(src_files, test_path, root_path)
        elif test_framework == "jest":
            return await self._generate_jest_files(src_files, test_path, root_path)
        elif test_framework == "mocha":
            return await self._generate_mocha_files(src_files, test_path, root_path)
        elif test_framework == "go_test":
            return await self._generate_go_test_files(src_files, test_path, root_path)
        # Add other test frameworks as needed
        
        return {
            "success": False,
            "error": f"Unsupported test framework: {test_framework}",
            "test_framework": test_framework,
            "project_type": project_type
        }
    
    async def _generate_pytest_files(
        self, 
        src_files: List[CodeFile],
        test_path: Path,
        root_path: Path
    ) -> Dict[str, Any]:
        """
        Generate pytest test files.
        
        Args:
            src_files: List of source files to generate tests for
            test_path: Path to the test directory
            root_path: Path to the project root
            
        Returns:
            Dictionary with the test generation result
        """
        self._logger.info(f"Generating pytest files in {test_path}")
        
        generated_files = []
        errors = []
        
        # Create conftest.py if it doesn't exist
        conftest_path = test_path / "conftest.py"
        if not conftest_path.exists():
            try:
                with open(conftest_path, 'w') as f:
                    f.write("""
# pytest fixtures and configuration

import pytest

# Define fixtures that can be used by multiple tests
@pytest.fixture
def sample_fixture():
    \"\"\"Example fixture.\"\"\"
    return "sample_value"
""".strip())
                
                generated_files.append(str(conftest_path))
            except Exception as e:
                errors.append(f"Failed to create conftest.py: {str(e)}")
        
        # Generate test file for each source file
        for src_file in src_files:
            # Skip if not a Python file
            if not src_file.path.endswith('.py'):
                continue
            
            # Determine test file path
            src_rel_path = src_file.path
            if src_rel_path.startswith('/'):
                # Convert absolute path to relative
                try:
                    src_rel_path = str(Path(src_rel_path).relative_to(root_path))
                except ValueError:
                    # Not under the project root, use the filename
                    src_rel_path = os.path.basename(src_rel_path)
            
            # Create test filename
            test_filename = f"test_{os.path.basename(src_rel_path)}"
            
            # Create module structure
            module_parts = os.path.dirname(src_rel_path).split('/')
            test_file_dir = test_path
            
            for part in module_parts:
                if part and part != '.':
                    test_file_dir = test_file_dir / part
                    os.makedirs(test_file_dir, exist_ok=True)
                    
                    # Create __init__.py if it doesn't exist
                    init_path = test_file_dir / "__init__.py"
                    if not init_path.exists():
                        try:
                            with open(init_path, 'w') as f:
                                f.write("# Test package initialization")
                            
                            generated_files.append(str(init_path))
                        except Exception as e:
                            errors.append(f"Failed to create {init_path}: {str(e)}")
            
            test_file_path = test_file_dir / test_filename
            
            # Generate test content
            test_content = await self._generate_python_test_content(src_file, "pytest")
            
            # Write the test file
            try:
                with open(test_file_path, 'w') as f:
                    f.write(test_content)
                
                generated_files.append(str(test_file_path))
            except Exception as e:
                errors.append(f"Failed to create {test_file_path}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "test_framework": "pytest",
            "project_type": "python",
            "generated_files": generated_files,
            "errors": errors,
            "file_count": len(generated_files)
        }
    
    async def _generate_unittest_files(
        self, 
        src_files: List[CodeFile],
        test_path: Path,
        root_path: Path
    ) -> Dict[str, Any]:
        """
        Generate unittest test files.
        
        Args:
            src_files: List of source files to generate tests for
            test_path: Path to the test directory
            root_path: Path to the project root
            
        Returns:
            Dictionary with the test generation result
        """
        self._logger.info(f"Generating unittest files in {test_path}")
        
        generated_files = []
        errors = []
        
        # Generate test file for each source file
        for src_file in src_files:
            # Skip if not a Python file
            if not src_file.path.endswith('.py'):
                continue
            
            # Determine test file path
            src_rel_path = src_file.path
            if src_rel_path.startswith('/'):
                # Convert absolute path to relative
                try:
                    src_rel_path = str(Path(src_rel_path).relative_to(root_path))
                except ValueError:
                    # Not under the project root, use the filename
                    src_rel_path = os.path.basename(src_rel_path)
            
            # Create test filename (unittest style)
            test_filename = f"{os.path.splitext(os.path.basename(src_rel_path))[0]}_test.py"
            
            # Create module structure
            module_parts = os.path.dirname(src_rel_path).split('/')
            test_file_dir = test_path
            
            for part in module_parts:
                if part and part != '.':
                    test_file_dir = test_file_dir / part
                    os.makedirs(test_file_dir, exist_ok=True)
                    
                    # Create __init__.py if it doesn't exist
                    init_path = test_file_dir / "__init__.py"
                    if not init_path.exists():
                        try:
                            with open(init_path, 'w') as f:
                                f.write("# Test package initialization")
                            
                            generated_files.append(str(init_path))
                        except Exception as e:
                            errors.append(f"Failed to create {init_path}: {str(e)}")
            
            test_file_path = test_file_dir / test_filename
            
            # Generate test content
            test_content = await self._generate_python_test_content(src_file, "unittest")
            
            # Write the test file
            try:
                with open(test_file_path, 'w') as f:
                    f.write(test_content)
                
                generated_files.append(str(test_file_path))
            except Exception as e:
                errors.append(f"Failed to create {test_file_path}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "test_framework": "unittest",
            "project_type": "python",
            "generated_files": generated_files,
            "errors": errors,
            "file_count": len(generated_files)
        }
    
    async def _generate_python_test_content(
        self, 
        src_file: CodeFile, 
        framework: str
    ) -> str:
        """
        Generate Python test content for a source file.
        
        Args:
            src_file: Source file to generate test for
            framework: Test framework to use ('pytest' or 'unittest')
            
        Returns:
            Test file content
        """
        # Convert relative path to module import path
        module_path = src_file.path.replace('/', '.').replace('\\', '.')
        if module_path.endswith('.py'):
            module_path = module_path[:-3]
        
        # Check for 'src/' prefix and remove it for imports
        if module_path.startswith('src.'):
            module_path = module_path[4:]
        
        # Analyze source code to extract classes and functions
        classes = []
        functions = []
        
        # Use regex to extract classes and functions
        class_pattern = r'class\s+(\w+)'
        function_pattern = r'def\s+(\w+)\s*\('
        
        for match in re.finditer(class_pattern, src_file.content):
            class_name = match.group(1)
            if not class_name.startswith('_') and class_name != 'Test':
                classes.append(class_name)
        
        for match in re.finditer(function_pattern, src_file.content):
            function_name = match.group(1)
            if not function_name.startswith('_') and function_name not in ['setup', 'teardown']:
                functions.append(function_name)
        
        # Generate test content based on framework
        if framework == "pytest":
            content = f"""
# Test file for {src_file.path}
import pytest
from {module_path} import *

"""
            
            # Add class tests
            for class_name in classes:
                content += f"""
class Test{class_name}:
    def setup_method(self):
        \"\"\"Set up test fixtures.\"\"\"
        self.instance = {class_name}()
    
    def teardown_method(self):
        \"\"\"Tear down test fixtures.\"\"\"
        pass
    
    def test_{class_name.lower()}_initialization(self):
        \"\"\"Test {class_name} initialization.\"\"\"
        assert self.instance is not None
    
    # Add more tests for class methods
"""
            
            # Add function tests
            for function_name in functions:
                content += f"""
def test_{function_name}():
    \"\"\"Test {function_name} function.\"\"\"
    # TODO: Add test implementation
    assert {function_name} is not None
"""
        
        elif framework == "unittest":
            content = f"""
# Test file for {src_file.path}
import unittest
from {module_path} import *

"""
            
            # Add class tests
            for class_name in classes:
                content += f"""
class {class_name}Test(unittest.TestCase):
    def setUp(self):
        \"\"\"Set up test fixtures.\"\"\"
        self.instance = {class_name}()
    
    def tearDown(self):
        \"\"\"Tear down test fixtures.\"\"\"
        pass
    
    def test_{class_name.lower()}_initialization(self):
        \"\"\"Test {class_name} initialization.\"\"\"
        self.assertIsNotNone(self.instance)
    
    # Add more tests for class methods
"""
            
            # Add function tests
            for function_name in functions:
                content += f"""
class {function_name.capitalize()}Test(unittest.TestCase):
    def test_{function_name}(self):
        \"\"\"Test {function_name} function.\"\"\"
        # TODO: Add test implementation
        self.assertIsNotNone({function_name})
"""
            
            # Add main block
            content += """

if __name__ == '__main__':
    unittest.main()
"""
        
        return content.strip()
    
    async def _generate_jest_files(
        self, 
        src_files: List[CodeFile],
        test_path: Path,
        root_path: Path
    ) -> Dict[str, Any]:
        """
        Generate Jest test files.
        
        Args:
            src_files: List of source files to generate tests for
            test_path: Path to the test directory
            root_path: Path to the project root
            
        Returns:
            Dictionary with the test generation result
        """
        self._logger.info(f"Generating Jest files in {test_path}")
        
        generated_files = []
        errors = []
        
        # Create jest.config.js if it doesn't exist
        jest_config_path = root_path / "jest.config.js"
        if not jest_config_path.exists():
            try:
                with open(jest_config_path, 'w') as f:
                    f.write("""
module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/__tests__/**/*.js?(x)', '**/?(*.)+(spec|test).js?(x)'],
  collectCoverage: true,
  coverageDirectory: 'coverage',
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!**/node_modules/**',
    '!**/vendor/**'
  ]
};
""".strip())
                
                generated_files.append(str(jest_config_path))
            except Exception as e:
                errors.append(f"Failed to create jest.config.js: {str(e)}")
        
        # Generate test file for each source file
        for src_file in src_files:
            # Skip if not a JavaScript file
            if not src_file.path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
            
            # Determine test file path
            src_rel_path = src_file.path
            if src_rel_path.startswith('/'):
                # Convert absolute path to relative
                try:
                    src_rel_path = str(Path(src_rel_path).relative_to(root_path))
                except ValueError:
                    # Not under the project root, use the filename
                    src_rel_path = os.path.basename(src_rel_path)
            
            # Create test filename (Jest style)
            file_basename = os.path.basename(src_rel_path)
            base, ext = os.path.splitext(file_basename)
            test_filename = f"{base}.test{ext}"
            
            # Create directory structure
            test_file_dir = test_path
            os.makedirs(test_file_dir, exist_ok=True)
            
            test_file_path = test_file_dir / test_filename
            
            # Generate test content
            test_content = await self._generate_js_test_content(src_file, "jest", src_rel_path)
            
            # Write the test file
            try:
                with open(test_file_path, 'w') as f:
                    f.write(test_content)
                
                generated_files.append(str(test_file_path))
            except Exception as e:
                errors.append(f"Failed to create {test_file_path}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "test_framework": "jest",
            "project_type": "node",
            "generated_files": generated_files,
            "errors": errors,
            "file_count": len(generated_files)
        }
    
    async def _generate_js_test_content(
        self, 
        src_file: CodeFile, 
        framework: str,
        rel_path: str
    ) -> str:
        """
        Generate JavaScript test content for a source file.
        
        Args:
            src_file: Source file to generate test for
            framework: Test framework to use ('jest' or 'mocha')
            rel_path: Relative path to the source file
            
        Returns:
            Test file content
        """
        # Create import path
        import_path = os.path.splitext(rel_path)[0]  # Remove extension
        
        # Handle path format
        if import_path.startswith('./') or import_path.startswith('../'):
            pass  # Keep as-is
        else:
            # Make it relative
            import_path = f"../{import_path}"
        
        # Get module type (ESM or CommonJS)
        is_esm = "export " in src_file.content or "import " in src_file.content
        
        # Analyze source code to extract exports
        exports = []
        
        # Match named exports and default exports
        export_patterns = [
            r'export\s+const\s+(\w+)',
            r'export\s+function\s+(\w+)',
            r'export\s+class\s+(\w+)',
            r'export\s+default\s+(?:function\s+)?(\w+)',
            r'module\.exports\s*=\s*{([^}]+)}',
            r'exports\.(\w+)\s*='
        ]
        
        has_default_export = "export default" in src_file.content or "module.exports = " in src_file.content
        
        for pattern in export_patterns:
            for match in re.finditer(pattern, src_file.content):
                if pattern == r'module\.exports\s*=\s*{([^}]+)}':
                    # Extract multiple exports from module.exports = {...}
                    exports_str = match.group(1)
                    for export_name in re.findall(r'(\w+)\s*:', exports_str):
                        exports.append(export_name)
                else:
                    export_name = match.group(1)
                    exports.append(export_name)
        
        # Generate test content based on framework
        if framework == "jest":
            if is_esm:
                content = f"""
// Tests for {rel_path}
import {{ {', '.join(exports)} }} from '{import_path}';
"""
                if has_default_export:
                    content += f"""
import defaultExport from '{import_path}';
"""
            else:
                content = f"""
// Tests for {rel_path}
const {{ {', '.join(exports)} }} = require('{import_path}');
"""
            
            content += """

describe('Module functionality', () => {
"""
            
            # Add tests for each export
            for export_name in exports:
                content += f"""
  describe('{export_name}', () => {{
    test('should be defined', () => {{
      expect({export_name}).toBeDefined();
    }});
    
    // Add more specific tests here
  }});
"""
            
            if has_default_export:
                content += """
  describe('default export', () => {
    test('should be defined', () => {
      expect(defaultExport).toBeDefined();
    });
    
    // Add more specific tests here
  });
"""
            
            # Close the describe block
            content += "});\n"
        
        elif framework == "mocha":
            if is_esm:
                content = f"""
// Tests for {rel_path}
import {{ {', '.join(exports)} }} from '{import_path}';
import assert from 'assert';
"""
                if has_default_export:
                    content += f"""
import defaultExport from '{import_path}';
"""
            else:
                content = f"""
// Tests for {rel_path}
const {{ {', '.join(exports)} }} = require('{import_path}');
const assert = require('assert');
"""
            
            content += """

describe('Module functionality', function() {
"""
            
            # Add tests for each export
            for export_name in exports:
                content += f"""
  describe('{export_name}', function() {{
    it('should be defined', function() {{
      assert({export_name} !== undefined);
    }});
    
    // Add more specific tests here
  }});
"""
            
            if has_default_export:
                content += """
  describe('default export', function() {
    it('should be defined', function() {
      assert(defaultExport !== undefined);
    });
    
    // Add more specific tests here
  });
"""
            
            # Close the describe block
            content += "});\n"
        
        return content.strip()
    
    async def _generate_mocha_files(
        self, 
        src_files: List[CodeFile],
        test_path: Path,
        root_path: Path
    ) -> Dict[str, Any]:
        """
        Generate Mocha test files.
        
        Args:
            src_files: List of source files to generate tests for
            test_path: Path to the test directory
            root_path: Path to the project root
            
        Returns:
            Dictionary with the test generation result
        """
        self._logger.info(f"Generating Mocha files in {test_path}")
        
        generated_files = []
        errors = []
        
        # Create .mocharc.js if it doesn't exist
        mocha_config_path = root_path / ".mocharc.js"
        if not mocha_config_path.exists():
            try:
                with open(mocha_config_path, 'w') as f:
                    f.write("""
module.exports = {
  require: '@babel/register',
  reporter: 'spec',
  timeout: 5000,
  recursive: true,
  'watch-files': ['test/**/*.js', 'src/**/*.js']
};
""".strip())
                
                generated_files.append(str(mocha_config_path))
            except Exception as e:
                errors.append(f"Failed to create .mocharc.js: {str(e)}")
        
        # Generate test file for each source file
        for src_file in src_files:
            # Skip if not a JavaScript file
            if not src_file.path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
            
            # Determine test file path
            src_rel_path = src_file.path
            if src_rel_path.startswith('/'):
                # Convert absolute path to relative
                try:
                    src_rel_path = str(Path(src_rel_path).relative_to(root_path))
                except ValueError:
                    # Not under the project root, use the filename
                    src_rel_path = os.path.basename(src_rel_path)
            
            # Create test filename (Mocha style)
            file_basename = os.path.basename(src_rel_path)
            base, ext = os.path.splitext(file_basename)
            test_filename = f"{base}.spec{ext}"
            
            # Create directory structure
            test_file_dir = test_path
            os.makedirs(test_file_dir, exist_ok=True)
            
            test_file_path = test_file_dir / test_filename
            
            # Generate test content
            test_content = await self._generate_js_test_content(src_file, "mocha", src_rel_path)
            
            # Write the test file
            try:
                with open(test_file_path, 'w') as f:
                    f.write(test_content)
                
                generated_files.append(str(test_file_path))
            except Exception as e:
                errors.append(f"Failed to create {test_file_path}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "test_framework": "mocha",
            "project_type": "node",
            "generated_files": generated_files,
            "errors": errors,
            "file_count": len(generated_files)
        }
    
    async def _generate_go_test_files(
        self, 
        src_files: List[CodeFile],
        test_path: Path,
        root_path: Path
    ) -> Dict[str, Any]:
        """
        Generate Go test files.
        
        Args:
            src_files: List of source files to generate tests for
            test_path: Path to the test directory
            root_path: Path to the project root
            
        Returns:
            Dictionary with the test generation result
        """
        self._logger.info(f"Generating Go test files in {test_path}")
        
        generated_files = []
        errors = []
        
        # In Go, test files are typically in the same directory as the source files
        # with a _test.go suffix
        
        # Generate test file for each source file
        for src_file in src_files:
            # Skip if not a Go file
            if not src_file.path.endswith('.go'):
                continue
            
            # Extract package information from source file
            package_match = re.search(r'package\s+(\w+)', src_file.content)
            if not package_match:
                errors.append(f"Could not determine package for {src_file.path}")
                continue
            
            package_name = package_match.group(1)
            
            # Determine test file path
            src_rel_path = src_file.path
            if src_rel_path.startswith('/'):
                # Convert absolute path to relative
                try:
                    src_rel_path = str(Path(src_rel_path).relative_to(root_path))
                except ValueError:
                    # Not under the project root, use the filename
                    src_rel_path = os.path.basename(src_rel_path)
            
            # Create test filename (Go style)
            dir_name = os.path.dirname(src_rel_path)
            file_basename = os.path.basename(src_rel_path)
            base, _ = os.path.splitext(file_basename)
            test_filename = f"{base}_test.go"
            
            # Go tests are in the same directory as the source
            if dir_name:
                test_file_dir = root_path / dir_name
            else:
                test_file_dir = root_path
            
            os.makedirs(test_file_dir, exist_ok=True)
            
            test_file_path = test_file_dir / test_filename
            
            # Analyze source code to extract functions and types
            function_pattern = r'func\s+(\w+)'
            type_pattern = r'type\s+(\w+)\s+'
            
            functions = []
            types = []
            
            for match in re.finditer(function_pattern, src_file.content):
                function_name = match.group(1)
                if not function_name.startswith('Test') and function_name[0].isupper():  # Exported functions
                    functions.append(function_name)
            
            for match in re.finditer(type_pattern, src_file.content):
                type_name = match.group(1)
                if type_name[0].isupper():  # Exported types
                    types.append(type_name)
            
            # Generate test content
            content = f"""
package {package_name}

import (
    "testing"
)

"""
            
            # Add function tests
            for function_name in functions:
                content += f"""
func Test{function_name}(t *testing.T) {{
    // TODO: Implement test
    t.Run("{function_name} basic test", func(t *testing.T) {{
        // t.Fatal("Not implemented")
    }})
}}
"""
            
            # Add type tests
            for type_name in types:
                content += f"""
func Test{type_name}(t *testing.T) {{
    // TODO: Implement test
    t.Run("{type_name} initialization", func(t *testing.T) {{
        // t.Fatal("Not implemented")
    }})
}}
"""
            
            # Add benchmark examples if there are functions
            if functions:
                content += f"""
func Benchmark{functions[0]}(b *testing.B) {{
    for i := 0; i < b.N; i++ {{
        // TODO: Call the function to benchmark
    }}
}}
"""
            
            # Write the test file
            try:
                with open(test_file_path, 'w') as f:
                    f.write(content.strip())
                
                generated_files.append(str(test_file_path))
            except Exception as e:
                errors.append(f"Failed to create {test_file_path}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "test_framework": "go_test",
            "project_type": "go",
            "generated_files": generated_files,
            "errors": errors,
            "file_count": len(generated_files)
        }

# Global test framework integration instance
test_framework_integration = TestFrameworkIntegration()
