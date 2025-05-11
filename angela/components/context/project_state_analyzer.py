# angela/context/project_state_analyzer.py
"""
Project state analysis for Angela CLI.

This module extends Angela's context awareness by providing detailed information
about the current state of the project, including Git status, pending migrations,
test coverage, and build health.
"""
import os
import re
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from datetime import datetime

from angela.utils.logging import get_logger
from angela.api.context import get_project_inference
from angela.api.execution import get_execution_engine

logger = get_logger(__name__)

class ProjectStateAnalyzer:
    """
    Project state analyzer that provides detailed information about the
    current state of the project beyond basic type detection.
    
    This class tracks:
    1. Git state (current branch, pending changes, stashes)
    2. Test coverage status
    3. Build health
    4. Pending migrations
    5. Dependency health (outdated packages, vulnerabilities)
    6. Linting/code quality issues
    7. TODO/FIXME comments
    """
    
    def __init__(self):
        """Initialize the project state analyzer."""
        self._logger = logger
        self._cache = {}  # Cache for state information
        self._cache_valid_time = 60  # Seconds before cache is invalid
        self._last_analysis_time = {}  # Timestamp of last analysis per project
    
    async def get_project_state(self, project_root: Union[str, Path]) -> Dict[str, Any]:
        """
        Get detailed information about the current state of the project.
        
        Args:
            project_root: Path to the project root directory
            
        Returns:
            Dictionary with project state information
        """
        path_obj = Path(project_root)
        path_str = str(path_obj)
        
        # Check if we have recent cached information
        if path_str in self._cache:
            # Check if the cache is still valid
            cache_age = datetime.now().timestamp() - self._last_analysis_time.get(path_str, 0)
            if cache_age < self._cache_valid_time:
                self._logger.debug(f"Using cached project state for {path_str} (age: {cache_age:.1f}s)")
                return self._cache[path_str]
        
        self._logger.info(f"Analyzing project state for {path_str}")
        
        # First, get basic project information
        try:
            project_inference = get_project_inference()
            basic_info = await project_inference.infer_project_info(path_obj)
        except Exception as e:
            self._logger.error(f"Error getting basic project info: {str(e)}")
            basic_info = {"project_type": "unknown"}
        
        # Initialize state information
        state_info = {
            "project_root": path_str,
            "project_type": basic_info.get("project_type", "unknown"),
            "analysis_time": datetime.now().isoformat(),
            "git_state": {},
            "test_status": {},
            "build_status": {},
            "migrations": {},
            "dependencies": {},
            "code_quality": {},
            "todo_items": []
        }
        
        # Analyze different aspects of the project state in parallel
        tasks = [
            self._analyze_git_state(path_obj),
            self._analyze_test_status(path_obj, basic_info.get("project_type", "unknown")),
            self._analyze_build_status(path_obj, basic_info.get("project_type", "unknown")),
            self._analyze_migrations(path_obj, basic_info.get("project_type", "unknown")),
            self._analyze_dependencies(path_obj, basic_info.get("project_type", "unknown")),
            self._analyze_code_quality(path_obj, basic_info.get("project_type", "unknown")),
            self._find_todo_items(path_obj)
        ]
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        if not isinstance(results[0], Exception):
            state_info["git_state"] = results[0] or {}
        if not isinstance(results[1], Exception):
            state_info["test_status"] = results[1] or {}
        if not isinstance(results[2], Exception):
            state_info["build_status"] = results[2] or {}
        if not isinstance(results[3], Exception):
            state_info["migrations"] = results[3] or {}
        if not isinstance(results[4], Exception):
            state_info["dependencies"] = results[4] or {}
        if not isinstance(results[5], Exception):
            state_info["code_quality"] = results[5] or {}
        if not isinstance(results[6], Exception):
            state_info["todo_items"] = results[6] or []
        
        # Cache the result
        self._cache[path_str] = state_info
        self._last_analysis_time[path_str] = datetime.now().timestamp()
        
        return state_info
    
    async def _analyze_git_state(self, project_root: Path) -> Dict[str, Any]:
        """
        Analyze the Git state of the project.
        
        Args:
            project_root: Path to the project root
            
        Returns:
            Dictionary with Git state information
        """
        result = {
            "is_git_repo": False,
            "current_branch": None,
            "has_changes": False,
            "untracked_files": [],
            "modified_files": [],
            "staged_files": [],
            "stashes": [],
            "remote_state": {},
            "recent_commits": []
        }
        
        # Check if this is a Git repository
        git_dir = project_root / ".git"
        if not git_dir.exists():
            return result
        
        result["is_git_repo"] = True
        
        try:
            execution_engine = get_execution_engine()
            
            # Get current branch
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {project_root} && git branch --show-current",
                check_safety=False
            )
            
            if return_code == 0 and stdout.strip():
                result["current_branch"] = stdout.strip()
            
            # Get git status
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {project_root} && git status --porcelain",
                check_safety=False
            )
            
            if return_code == 0:
                result["has_changes"] = bool(stdout.strip())
                
                # Parse status output
                for line in stdout.splitlines():
                    if not line.strip():
                        continue
                    
                    # Parse status code and filename
                    status_code = line[:2]
                    file_path = line[3:].strip()
                    
                    if status_code.startswith('??'):
                        # Untracked file
                        result["untracked_files"].append(file_path)
                    elif status_code.startswith('M'):
                        # Modified file
                        result["modified_files"].append(file_path)
                    elif status_code.startswith('A') or status_code.startswith('R'):
                        # Staged file (added or renamed)
                        result["staged_files"].append(file_path)
            
            # Get stash list
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {project_root} && git stash list",
                check_safety=False
            )
            
            if return_code == 0 and stdout.strip():
                # Parse stash list
                for line in stdout.splitlines():
                    match = re.match(r'stash@{(\d+)}: (.*)', line)
                    if match:
                        stash_id = match.group(1)
                        stash_description = match.group(2)
                        result["stashes"].append({
                            "id": stash_id,
                            "description": stash_description
                        })
            
            # Check remote state
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {project_root} && git status -sb",
                check_safety=False
            )
            
            if return_code == 0 and stdout.strip():
                # Parse first line for branch and tracking info
                first_line = stdout.splitlines()[0]
                
                # Check for ahead/behind information
                ahead_match = re.search(r'ahead (\d+)', first_line)
                behind_match = re.search(r'behind (\d+)', first_line)
                
                result["remote_state"] = {
                    "tracking": "origin" in first_line,
                    "ahead": int(ahead_match.group(1)) if ahead_match else 0,
                    "behind": int(behind_match.group(1)) if behind_match else 0
                }
            
            # Get recent commits
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {project_root} && git log -n 5 --pretty=format:'%h|%an|%s|%cr'",
                check_safety=False
            )
            
            if return_code == 0 and stdout.strip():
                for line in stdout.splitlines():
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commit_hash, author, message, time = parts
                        result["recent_commits"].append({
                            "hash": commit_hash,
                            "author": author,
                            "message": message,
                            "time": time
                        })
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error analyzing Git state: {str(e)}")
            return result
    
    async def _analyze_test_status(self, project_root: Path, project_type: str) -> Dict[str, Any]:
        """
        Analyze the test status of the project.
        
        Args:
            project_root: Path to the project root
            project_type: Type of the project
            
        Returns:
            Dictionary with test status information
        """
        result = {
            "test_framework_detected": False,
            "framework": None,
            "test_files_count": 0,
            "last_run": None,
            "coverage": None,
            "failing_tests": [],
            "performance_issues": []
        }
        
        # Look for test frameworks based on project type
        if "python" in project_type:
            # Check for pytest
            pytest_file = project_root / "pytest.ini"
            conftest_file = project_root / "conftest.py"
            
            if pytest_file.exists() or conftest_file.exists() or list(project_root.glob("**/test_*.py")):
                result["test_framework_detected"] = True
                result["framework"] = "pytest"
                
                # Count test files
                test_files = list(project_root.glob("**/test_*.py"))
                result["test_files_count"] = len(test_files)
                
                # Look for coverage file
                coverage_file = project_root / ".coverage"
                coverage_xml = project_root / "coverage.xml"
                
                if coverage_file.exists() or coverage_xml.exists():
                    # Try to get coverage info
                    if coverage_xml.exists():
                        try:
                            import xml.etree.ElementTree as ET
                            tree = ET.parse(coverage_xml)
                            root = tree.getroot()
                            
                            # Get coverage percentage
                            coverage_attr = root.get('line-rate')
                            if coverage_attr:
                                coverage_percentage = float(coverage_attr) * 100
                                result["coverage"] = {
                                    "percentage": coverage_percentage,
                                    "report_path": str(coverage_xml.relative_to(project_root))
                                }
                        except Exception as e:
                            self._logger.error(f"Error parsing coverage XML: {str(e)}")
            
            # Check for unittest
            elif list(project_root.glob("**/test*.py")):
                result["test_framework_detected"] = True
                result["framework"] = "unittest"
                
                # Count test files
                test_files = list(project_root.glob("**/test*.py"))
                result["test_files_count"] = len(test_files)
        
        elif "node" in project_type or "javascript" in project_type or "typescript" in project_type:
            # Check for Jest
            jest_config = project_root / "jest.config.js"
            package_json = project_root / "package.json"
            
            if jest_config.exists() or (package_json.exists() and "jest" in open(package_json).read()):
                result["test_framework_detected"] = True
                result["framework"] = "jest"
                
                # Count test files
                test_files = list(project_root.glob("**/*.test.js")) + list(project_root.glob("**/*.test.ts"))
                result["test_files_count"] = len(test_files)
                
                # Look for coverage directory
                coverage_dir = project_root / "coverage"
                if coverage_dir.exists():
                    try:
                        coverage_summary = coverage_dir / "coverage-summary.json"
                        if coverage_summary.exists():
                            with open(coverage_summary) as f:
                                coverage_data = json.load(f)
                                
                                if "total" in coverage_data and "lines" in coverage_data["total"]:
                                    coverage_percentage = coverage_data["total"]["lines"]["pct"]
                                    result["coverage"] = {
                                        "percentage": coverage_percentage,
                                        "report_path": str(coverage_summary.relative_to(project_root))
                                    }
                    except Exception as e:
                        self._logger.error(f"Error parsing Jest coverage: {str(e)}")
            
            # Check for Mocha
            elif package_json.exists() and "mocha" in open(package_json).read():
                result["test_framework_detected"] = True
                result["framework"] = "mocha"
                
                # Count test files
                test_files = list(project_root.glob("**/test/**/*.js")) + list(project_root.glob("**/test/**/*.ts"))
                result["test_files_count"] = len(test_files)
        
        elif "java" in project_type:
            # Check for JUnit
            if list(project_root.glob("**/src/test/**/*.java")):
                result["test_framework_detected"] = True
                result["framework"] = "junit"
                
                # Count test files
                test_files = list(project_root.glob("**/src/test/**/*.java"))
                result["test_files_count"] = len(test_files)
        
        return result
    
    async def _analyze_build_status(self, project_root: Path, project_type: str) -> Dict[str, Any]:
        """
        Analyze the build status of the project.
        
        Args:
            project_root: Path to the project root
            project_type: Type of the project
            
        Returns:
            Dictionary with build status information
        """
        result = {
            "build_system_detected": False,
            "system": None,
            "last_build": None,
            "artifacts": [],
            "problems": []
        }
        
        if "python" in project_type:
            # Check for setuptools
            setup_py = project_root / "setup.py"
            pyproject_toml = project_root / "pyproject.toml"
            
            if setup_py.exists():
                result["build_system_detected"] = True
                result["system"] = "setuptools"
                
                # Check for dist directory
                dist_dir = project_root / "dist"
                if dist_dir.exists():
                    # Get artifact files
                    artifacts = list(dist_dir.glob("*.whl")) + list(dist_dir.glob("*.tar.gz"))
                    
                    if artifacts:
                        result["artifacts"] = [str(a.relative_to(project_root)) for a in artifacts]
                        
                        # Get the most recent artifact's timestamp
                        most_recent = max(artifacts, key=lambda p: p.stat().st_mtime)
                        result["last_build"] = datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat()
            
            elif pyproject_toml.exists():
                result["build_system_detected"] = True
                
                # Determine build system from pyproject.toml
                try:
                    import tomli
                    with open(pyproject_toml, "rb") as f:
                        pyproject_data = tomli.load(f)
                    
                    if "build-system" in pyproject_data:
                        build_backend = pyproject_data["build-system"].get("build-backend", "")
                        
                        if "setuptools" in build_backend:
                            result["system"] = "setuptools"
                        elif "poetry" in build_backend:
                            result["system"] = "poetry"
                        elif "flit" in build_backend:
                            result["system"] = "flit"
                        elif "hatchling" in build_backend:
                            result["system"] = "hatch"
                        else:
                            result["system"] = build_backend
                except Exception as e:
                    self._logger.error(f"Error parsing pyproject.toml: {str(e)}")
                    result["system"] = "unknown-pyproject"
                
                # Check for dist directory
                dist_dir = project_root / "dist"
                if dist_dir.exists():
                    # Get artifact files
                    artifacts = list(dist_dir.glob("*.whl")) + list(dist_dir.glob("*.tar.gz"))
                    
                    if artifacts:
                        result["artifacts"] = [str(a.relative_to(project_root)) for a in artifacts]
                        
                        # Get the most recent artifact's timestamp
                        most_recent = max(artifacts, key=lambda p: p.stat().st_mtime)
                        result["last_build"] = datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat()
        
        elif "node" in project_type or "javascript" in project_type or "typescript" in project_type:
            # Check for various build systems
            package_json = project_root / "package.json"
            
            if package_json.exists():
                result["build_system_detected"] = True
                
                # Determine build system from package.json
                try:
                    with open(package_json) as f:
                        package_data = json.load(f)
                    
                    if "scripts" in package_data:
                        scripts = package_data["scripts"]
                        
                        if "build" in scripts:
                            build_script = scripts["build"]
                            
                            if "webpack" in build_script:
                                result["system"] = "webpack"
                            elif "rollup" in build_script:
                                result["system"] = "rollup"
                            elif "parcel" in build_script:
                                result["system"] = "parcel"
                            elif "tsc" in build_script:
                                result["system"] = "typescript"
                            elif "next build" in build_script:
                                result["system"] = "next.js"
                            elif "vue-cli-service build" in build_script:
                                result["system"] = "vue-cli"
                            elif "ng build" in build_script:
                                result["system"] = "angular-cli"
                            else:
                                result["system"] = "npm-script"
                except Exception as e:
                    self._logger.error(f"Error parsing package.json: {str(e)}")
                    result["system"] = "npm"
                
                # Check for build artifacts
                build_dir = project_root / "build"
                dist_dir = project_root / "dist"
                
                if build_dir.exists():
                    artifacts = list(build_dir.glob("**/*.*"))
                    if artifacts:
                        result["artifacts"] = [str(a.relative_to(project_root)) for a in artifacts[:5]]  # Limit to 5
                        
                        # Get the most recent artifact's timestamp
                        most_recent = max(artifacts, key=lambda p: p.stat().st_mtime)
                        result["last_build"] = datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat()
                
                elif dist_dir.exists():
                    artifacts = list(dist_dir.glob("**/*.*"))
                    if artifacts:
                        result["artifacts"] = [str(a.relative_to(project_root)) for a in artifacts[:5]]  # Limit to 5
                        
                        # Get the most recent artifact's timestamp
                        most_recent = max(artifacts, key=lambda p: p.stat().st_mtime)
                        result["last_build"] = datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat()
        
        elif "java" in project_type:
            # Check for Maven and Gradle
            pom_xml = project_root / "pom.xml"
            gradle_build = project_root / "build.gradle"
            
            if pom_xml.exists():
                result["build_system_detected"] = True
                result["system"] = "maven"
                
                # Check for target directory
                target_dir = project_root / "target"
                if target_dir.exists():
                    jar_files = list(target_dir.glob("*.jar"))
                    war_files = list(target_dir.glob("*.war"))
                    
                    artifacts = jar_files + war_files
                    if artifacts:
                        result["artifacts"] = [str(a.relative_to(project_root)) for a in artifacts]
                        
                        # Get the most recent artifact's timestamp
                        most_recent = max(artifacts, key=lambda p: p.stat().st_mtime)
                        result["last_build"] = datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat()
            
            elif gradle_build.exists():
                result["build_system_detected"] = True
                result["system"] = "gradle"
                
                # Check for build directory
                build_dir = project_root / "build"
                if build_dir.exists():
                    jar_files = list(build_dir.glob("**/*.jar"))
                    war_files = list(build_dir.glob("**/*.war"))
                    
                    artifacts = jar_files + war_files
                    if artifacts:
                        result["artifacts"] = [str(a.relative_to(project_root)) for a in artifacts]
                        
                        # Get the most recent artifact's timestamp
                        most_recent = max(artifacts, key=lambda p: p.stat().st_mtime)
                        result["last_build"] = datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat()
        
        return result
    
    async def _analyze_migrations(self, project_root: Path, project_type: str) -> Dict[str, Any]:
        """
        Analyze the migration status of the project.
        
        Args:
            project_root: Path to the project root
            project_type: Type of the project
            
        Returns:
            Dictionary with migration status information
        """
        result = {
            "has_migrations": False,
            "framework": None,
            "migration_files": [],
            "pending_migrations": []
        }
        
        if "python" in project_type:
            # Check for Django migrations
            migrations_dirs = list(project_root.glob("**/migrations"))
            
            if migrations_dirs:
                result["has_migrations"] = True
                result["framework"] = "django"
                
                # Get migration files
                migration_files = []
                for migrations_dir in migrations_dirs:
                    files = list(migrations_dir.glob("*.py"))
                    migration_files.extend([str(f.relative_to(project_root)) for f in files if f.name != "__init__.py"])
                
                result["migration_files"] = migration_files
                
                # Try to detect pending migrations using Django
                manage_py = project_root / "manage.py"
                if manage_py.exists():
                    try:
                        execution_engine = get_execution_engine()
                        stdout, stderr, return_code = await execution_engine.execute_command(
                            command=f"cd {project_root} && python manage.py showmigrations",
                            check_safety=False
                        )
                        
                        if return_code == 0:
                            # Parse output to find pending migrations
                            pending = []
                            current_app = None
                            
                            for line in stdout.splitlines():
                                if not line.strip():
                                    continue
                                
                                if not line.startswith(' '):
                                    # This is an app name
                                    current_app = line.strip()
                                elif line.strip().startswith('[ ]'):
                                    # This is a pending migration
                                    migration_name = line.strip()[4:].strip()
                                    if current_app:
                                        pending.append(f"{current_app}/{migration_name}")
                            
                            result["pending_migrations"] = pending
                    except Exception as e:
                        self._logger.error(f"Error detecting Django pending migrations: {str(e)}")
            
            # Check for Alembic migrations (SQLAlchemy)
            alembic_ini = project_root / "alembic.ini"
            if alembic_ini.exists():
                alembic_dir = None
                
                # Try to find migrations directory from alembic.ini
                try:
                    with open(alembic_ini) as f:
                        for line in f:
                            if line.startswith('script_location = '):
                                alembic_dir = line.split('=')[1].strip()
                                break
                except Exception:
                    pass
                
                if alembic_dir:
                    alembic_path = project_root / alembic_dir / "versions"
                    if alembic_path.exists():
                        result["has_migrations"] = True
                        result["framework"] = "alembic"
                        
                        # Get migration files
                        migration_files = list(alembic_path.glob("*.py"))
                        result["migration_files"] = [str(f.relative_to(project_root)) for f in migration_files]
                        
                        # Try to detect pending migrations
                        try:
                            execution_engine = get_execution_engine()
                            stdout, stderr, return_code = await execution_engine.execute_command(
                                command=f"cd {project_root} && alembic current",
                                check_safety=False
                            )
                            
                            if return_code == 0:
                                # Get current revision
                                current_revision = None
                                if stdout.strip():
                                    current_revision = stdout.strip().split(' ')[0]
                                
                                # Get available revisions
                                available_revisions = []
                                for file in migration_files:
                                    # Extract revision ID from filename
                                    revision_match = re.match(r'(\w+)_', file.stem)
                                    if revision_match:
                                        available_revisions.append(revision_match.group(1))
                                
                                # If we have a current revision, find pending ones
                                if current_revision and current_revision in available_revisions:
                                    current_index = available_revisions.index(current_revision)
                                    pending_revisions = available_revisions[current_index+1:]
                                    
                                    result["pending_migrations"] = [
                                        str((alembic_path / f"{rev}_something.py").relative_to(project_root))
                                        for rev in pending_revisions
                                    ]
                        except Exception as e:
                            self._logger.error(f"Error detecting Alembic pending migrations: {str(e)}")
        
        elif "node" in project_type or "javascript" in project_type:
            # Check for Sequelize migrations
            migrations_dir = project_root / "migrations"
            if migrations_dir.exists() and migrations_dir.is_dir():
                # Look for a Sequelize config file
                config_file = project_root / "config" / "config.json"
                sequelize_rc = project_root / ".sequelizerc"
                
                if config_file.exists() or sequelize_rc.exists():
                    result["has_migrations"] = True
                    result["framework"] = "sequelize"
                    
                    # Get migration files
                    migration_files = list(migrations_dir.glob("*.js"))
                    result["migration_files"] = [str(f.relative_to(project_root)) for f in migration_files]
        
        elif "ruby" in project_type or "rails" in project_type:
            # Check for Rails migrations
            migrations_dir = project_root / "db" / "migrate"
            if migrations_dir.exists() and migrations_dir.is_dir():
                result["has_migrations"] = True
                result["framework"] = "rails"
                
                # Get migration files
                migration_files = list(migrations_dir.glob("*.rb"))
                result["migration_files"] = [str(f.relative_to(project_root)) for f in migration_files]
                
                # Try to detect pending migrations
                try:
                    execution_engine = get_execution_engine()
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command=f"cd {project_root} && rake db:migrate:status",
                        check_safety=False
                    )
                    
                    if return_code == 0:
                        # Parse output to find pending migrations
                        pending = []
                        
                        for line in stdout.splitlines():
                            if line.strip().startswith('down '):
                                # This is a pending migration
                                migration_info = line.strip()[5:].strip()
                                migration_match = re.search(r'(\d+)_([a-z_]+)\.rb', migration_info)
                                if migration_match:
                                    pending.append(f"db/migrate/{migration_match.group(0)}")
                        
                        result["pending_migrations"] = pending
                except Exception as e:
                    self._logger.error(f"Error detecting Rails pending migrations: {str(e)}")
        
        return result
    
    async def _analyze_dependencies(self, project_root: Path, project_type: str) -> Dict[str, Any]:
        """
        Analyze the dependency health of the project.
        
        Args:
            project_root: Path to the project root
            project_type: Type of the project
            
        Returns:
            Dictionary with dependency health information
        """
        result = {
            "has_dependencies": False,
            "dependency_file": None,
            "package_manager": None,
            "dependencies_count": 0,
            "dev_dependencies_count": 0,
            "outdated_packages": [],
            "vulnerable_packages": []
        }
        
        if "python" in project_type:
            # Check for pip requirements
            requirements_txt = project_root / "requirements.txt"
            pipfile = project_root / "Pipfile"
            pyproject_toml = project_root / "pyproject.toml"
            
            if requirements_txt.exists():
                result["has_dependencies"] = True
                result["dependency_file"] = str(requirements_txt.relative_to(project_root))
                result["package_manager"] = "pip"
                
                # Count dependencies
                try:
                    with open(requirements_txt) as f:
                        deps = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                        result["dependencies_count"] = len(deps)
                except Exception as e:
                    self._logger.error(f"Error reading requirements.txt: {str(e)}")
                
                # Try to find outdated packages
                try:
                    execution_engine = get_execution_engine()
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command=f"cd {project_root} && pip list --outdated --format=json",
                        check_safety=False
                    )
                    
                    if return_code == 0 and stdout.strip():
                        try:
                            outdated = json.loads(stdout)
                            result["outdated_packages"] = [
                                {
                                    "name": pkg["name"],
                                    "current_version": pkg["version"],
                                    "latest_version": pkg["latest_version"]
                                }
                                for pkg in outdated
                            ]
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    self._logger.error(f"Error checking for outdated packages: {str(e)}")
            
            elif pipfile.exists():
                result["has_dependencies"] = True
                result["dependency_file"] = str(pipfile.relative_to(project_root))
                result["package_manager"] = "pipenv"
                
                # Try to get dependency info from Pipfile.lock
                pipfile_lock = project_root / "Pipfile.lock"
                if pipfile_lock.exists():
                    try:
                        with open(pipfile_lock) as f:
                            lock_data = json.load(f)
                            
                            if "default" in lock_data:
                                result["dependencies_count"] = len(lock_data["default"])
                            
                            if "develop" in lock_data:
                                result["dev_dependencies_count"] = len(lock_data["develop"])
                    except Exception as e:
                        self._logger.error(f"Error reading Pipfile.lock: {str(e)}")
            
            elif pyproject_toml.exists():
                result["has_dependencies"] = True
                result["dependency_file"] = str(pyproject_toml.relative_to(project_root))
                
                # Try to determine the package manager
                try:
                    import tomli
                    with open(pyproject_toml, "rb") as f:
                        pyproject_data = tomli.load(f)
                    
                    if "build-system" in pyproject_data:
                        build_backend = pyproject_data["build-system"].get("build-backend", "")
                        
                        if "poetry" in build_backend:
                            result["package_manager"] = "poetry"
                        else:
                            result["package_manager"] = "pip"
                    
                    # Count dependencies
                    if "project" in pyproject_data and "dependencies" in pyproject_data["project"]:
                        if isinstance(pyproject_data["project"]["dependencies"], list):
                            result["dependencies_count"] = len(pyproject_data["project"]["dependencies"])
                    
                    # Count dev dependencies
                    if "project" in pyproject_data and "optional-dependencies" in pyproject_data["project"]:
                        if "dev" in pyproject_data["project"]["optional-dependencies"]:
                            result["dev_dependencies_count"] = len(pyproject_data["project"]["optional-dependencies"]["dev"])
                
                except Exception as e:
                    self._logger.error(f"Error reading pyproject.toml: {str(e)}")
        
        elif "node" in project_type or "javascript" in project_type or "typescript" in project_type:
            # Check for NPM/Yarn dependencies
            package_json = project_root / "package.json"
            
            if package_json.exists():
                result["has_dependencies"] = True
                result["dependency_file"] = str(package_json.relative_to(project_root))
                
                # Determine package manager
                yarn_lock = project_root / "yarn.lock"
                package_lock = project_root / "package-lock.json"
                
                if yarn_lock.exists():
                    result["package_manager"] = "yarn"
                else:
                    result["package_manager"] = "npm"
                
                # Count dependencies
                try:
                    with open(package_json) as f:
                        package_data = json.load(f)
                        
                        if "dependencies" in package_data:
                            result["dependencies_count"] = len(package_data["dependencies"])
                        
                        if "devDependencies" in package_data:
                            result["dev_dependencies_count"] = len(package_data["devDependencies"])
                except Exception as e:
                    self._logger.error(f"Error reading package.json: {str(e)}")
                
                # Try to find outdated packages
                npm_cmd = "npm" if result["package_manager"] == "npm" else "yarn"
                try:
                    execution_engine = get_execution_engine()
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command=f"cd {project_root} && {npm_cmd} outdated --json",
                        check_safety=False
                    )
                    
                    if return_code == 0 and stdout.strip():
                        try:
                            outdated = json.loads(stdout)
                            
                            if isinstance(outdated, dict):
                                result["outdated_packages"] = [
                                    {
                                        "name": pkg_name,
                                        "current_version": pkg_info.get("current", "unknown"),
                                        "latest_version": pkg_info.get("latest", "unknown")
                                    }
                                    for pkg_name, pkg_info in outdated.items()
                                ]
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    self._logger.error(f"Error checking for outdated packages: {str(e)}")
        
        elif "java" in project_type:
            # Check for Maven dependencies
            pom_xml = project_root / "pom.xml"
            gradle_build = project_root / "build.gradle"
            
            if pom_xml.exists():
                result["has_dependencies"] = True
                result["dependency_file"] = str(pom_xml.relative_to(project_root))
                result["package_manager"] = "maven"
                
                # Try to count dependencies using basic XML parsing
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(pom_xml)
                    root = tree.getroot()
                    
                    # Add namespace to XML tags
                    ns = {"mvn": "http://maven.apache.org/POM/4.0.0"}
                    
                    # Count dependencies
                    dependencies = root.findall(".//mvn:dependencies/mvn:dependency", ns)
                    result["dependencies_count"] = len(dependencies)
                except Exception as e:
                    self._logger.error(f"Error parsing pom.xml: {str(e)}")
            
            elif gradle_build.exists():
                result["has_dependencies"] = True
                result["dependency_file"] = str(gradle_build.relative_to(project_root))
                result["package_manager"] = "gradle"
                
                # Count dependencies using a simple regex
                try:
                    with open(gradle_build) as f:
                        content = f.read()
                        
                        # Count dependencies
                        dependency_matches = re.findall(r"implementation ['\"]([^'\"]+?)['\"]", content)
                        result["dependencies_count"] = len(dependency_matches)
                        
                        # Count dev dependencies
                        test_matches = re.findall(r"testImplementation ['\"]([^'\"]+?)['\"]", content)
                        result["dev_dependencies_count"] = len(test_matches)
                except Exception as e:
                    self._logger.error(f"Error reading build.gradle: {str(e)}")
        
        return result
    
    async def _analyze_code_quality(self, project_root: Path, project_type: str) -> Dict[str, Any]:
        """
        Analyze the code quality of the project.
        
        Args:
            project_root: Path to the project root
            project_type: Type of the project
            
        Returns:
            Dictionary with code quality information
        """
        result = {
            "linting_setup_detected": False,
            "linter": None,
            "formatter": None,
            "issues_count": 0,
            "issues_by_type": {},
            "high_priority_issues": []
        }
        
        if "python" in project_type:
            # Check for Python linters
            flake8_config = project_root / ".flake8"
            pylintrc = project_root / ".pylintrc"
            mypy_ini = project_root / "mypy.ini"
            
            if flake8_config.exists():
                result["linting_setup_detected"] = True
                result["linter"] = "flake8"
                
                # Try to run flake8 to get issue count
                try:
                    execution_engine = get_execution_engine()
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command=f"cd {project_root} && flake8 --max-line-length=120 --count",
                        check_safety=False
                    )
                    
                    if return_code == 0 and stdout.strip():
                        # Last line contains the issue count
                        result["issues_count"] = int(stdout.strip().splitlines()[-1])
                except Exception as e:
                    self._logger.error(f"Error running flake8: {str(e)}")
            
            elif pylintrc.exists():
                result["linting_setup_detected"] = True
                result["linter"] = "pylint"
            
            # Check for Python formatters
            black_config = project_root / "pyproject.toml"
            if black_config.exists():
                try:
                    import tomli
                    with open(black_config, "rb") as f:
                        config_data = tomli.load(f)
                    
                    if "tool" in config_data and "black" in config_data["tool"]:
                        result["formatter"] = "black"
                except Exception:
                    pass
            
            isort_config = project_root / ".isort.cfg"
            if isort_config.exists():
                if result["formatter"]:
                    result["formatter"] += "+isort"
                else:
                    result["formatter"] = "isort"
        
        elif "node" in project_type or "javascript" in project_type or "typescript" in project_type:
            # Check for JS/TS linters
            eslintrc = any(
                (project_root / f).exists() 
                for f in [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml"]
            )
            
            if eslintrc:
                result["linting_setup_detected"] = True
                result["linter"] = "eslint"
                
                # Try to run eslint to get issue count
                try:
                    execution_engine = get_execution_engine()
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command=f"cd {project_root} && npx eslint . --max-warnings=9999 -f json",
                        check_safety=False
                    )
                    
                    if return_code == 0 and stdout.strip():
                        try:
                            lint_results = json.loads(stdout)
                            
                            # Count issues
                            total_issues = sum(len(file_result.get("messages", [])) for file_result in lint_results)
                            result["issues_count"] = total_issues
                            
                            # Count by severity
                            severity_counts = {"error": 0, "warning": 0, "info": 0}
                            
                            for file_result in lint_results:
                                for msg in file_result.get("messages", []):
                                    severity = msg.get("severity")
                                    if severity == 2:
                                        severity_counts["error"] += 1
                                    elif severity == 1:
                                        severity_counts["warning"] += 1
                                    else:
                                        severity_counts["info"] += 1
                            
                            result["issues_by_type"] = severity_counts
                            
                            # Collect high-priority issues
                            for file_result in lint_results:
                                for msg in file_result.get("messages", []):
                                    if msg.get("severity") == 2:  # Error
                                        result["high_priority_issues"].append({
                                            "file": file_result.get("filePath", "unknown"),
                                            "line": msg.get("line", 0),
                                            "column": msg.get("column", 0),
                                            "message": msg.get("message", "Unknown error"),
                                            "rule": msg.get("ruleId", "unknown")
                                        })
                                        
                                        # Limit to 10 issues
                                        if len(result["high_priority_issues"]) >= 10:
                                            break
                                
                                if len(result["high_priority_issues"]) >= 10:
                                    break
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    self._logger.error(f"Error running eslint: {str(e)}")
            
            # Check for tslint
            tslint_json = project_root / "tslint.json"
            if tslint_json.exists():
                result["linting_setup_detected"] = True
                result["linter"] = "tslint"
            
            # Check for formatters
            prettier_config = any(
                (project_root / f).exists() 
                for f in [".prettierrc", ".prettierrc.js", ".prettierrc.json", ".prettier.config.js"]
            )
            
            if prettier_config:
                result["formatter"] = "prettier"
        
        elif "java" in project_type:
            # Check for Java linters
            checkstyle_xml = project_root / "checkstyle.xml"
            pmd_xml = project_root / "pmd.xml"
            
            if checkstyle_xml.exists():
                result["linting_setup_detected"] = True
                result["linter"] = "checkstyle"
            
            elif pmd_xml.exists():
                result["linting_setup_detected"] = True
                result["linter"] = "pmd"
        
        return result
    
    async def _find_todo_items(self, project_root: Path) -> List[Dict[str, Any]]:
        """
        Find TODO and FIXME comments in the project.
        
        Args:
            project_root: Path to the project root
            
        Returns:
            List of dictionaries with todo items
        """
        # List of file extensions to search
        extensions = [
            ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".h", ".cs", 
            ".rb", ".php", ".go", ".rs", ".swift", ".kt", ".scala", ".html", ".css", 
            ".scss", ".less", ".md", ".txt", ".sh", ".bat", ".ps1"
        ]
        
        # Patterns to search for
        todo_patterns = [
            r'(?://|#|<!--|;|/\*)\s*TODO\s*(?:\(([^)]+)\)\s*)?:?\s*(.*?)(?:\*/|-->)?$',
            r'(?://|#|<!--|;|/\*)\s*FIXME\s*(?:\(([^)]+)\)\s*)?:?\s*(.*?)(?:\*/|-->)?$',
            r'(?://|#|<!--|;|/\*)\s*HACK\s*(?:\(([^)]+)\)\s*)?:?\s*(.*?)(?:\*/|-->)?$',
            r'(?://|#|<!--|;|/\*)\s*BUG\s*(?:\(([^)]+)\)\s*)?:?\s*(.*?)(?:\*/|-->)?$',
            r'(?://|#|<!--|;|/\*)\s*NOTE\s*(?:\(([^)]+)\)\s*)?:?\s*(.*?)(?:\*/|-->)?$'
        ]
        
        # Exclude patterns
        exclude_patterns = [
            "node_modules", "__pycache__", ".git", "venv", ".venv", "env", 
            "build", "dist", "target", "bin", "obj", ".pytest_cache"
        ]
        
        # Result list
        todo_items = []
        
        # Find files to search
        for ext in extensions:
            files = []
            for file in project_root.glob(f"**/*{ext}"):
                # Skip excluded directories
                if any(excl in str(file) for excl in exclude_patterns):
                    continue
                files.append(file)
            
            # Limit to 1000 files to avoid excessive processing
            if len(files) > 1000:
                files = files[:1000]
            
            # Search each file
            for file in files:
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            for pattern in todo_patterns:
                                matches = re.search(pattern, line)
                                if matches:
                                    # Extract todo info
                                    assignee = matches.group(1) if matches.lastindex >= 1 else None
                                    text = matches.group(2) if matches.lastindex >= 2 else matches.group(0)
                                    
                                    # Determine todo type
                                    todo_type = None
                                    if "TODO" in line:
                                        todo_type = "TODO"
                                    elif "FIXME" in line:
                                        todo_type = "FIXME"
                                    elif "HACK" in line:
                                        todo_type = "HACK"
                                    elif "BUG" in line:
                                        todo_type = "BUG"
                                    elif "NOTE" in line:
                                        todo_type = "NOTE"
                                    
                                    # Add to result
                                    todo_items.append({
                                        "type": todo_type,
                                        "text": text.strip(),
                                        "file": str(file.relative_to(project_root)),
                                        "line": i,
                                        "assignee": assignee.strip() if assignee else None
                                    })
                except Exception as e:
                    self._logger.error(f"Error searching for todos in {file}: {str(e)}")
        
        # Sort by file and line number
        todo_items.sort(key=lambda item: (item["file"], item["line"]))
        
        # Limit to 100 items to avoid excessive data
        return todo_items[:100]
    
    async def get_detailed_git_status(self, project_root: Union[str, Path]) -> Dict[str, Any]:
        """
        Get detailed information about the Git status of the project.
        
        Args:
            project_root: Path to the project root
            
        Returns:
            Dictionary with detailed Git information
        """
        path_obj = Path(project_root)
        
        # Get basic project state
        project_state = await self.get_project_state(path_obj)
        git_state = project_state.get("git_state", {})
        
        if not git_state.get("is_git_repo", False):
            return {"is_git_repo": False}
        
        # Add more detailed Git information
        result = dict(git_state)
        
        try:
            execution_engine = get_execution_engine()
            
            # Get the git log graph
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {path_obj} && git log --graph --oneline --decorate -n 10",
                check_safety=False
            )
            
            if return_code == 0 and stdout.strip():
                result["log_graph"] = stdout.strip()
            
            # Get branch info
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {path_obj} && git branch -vv",
                check_safety=False
            )
            
            if return_code == 0 and stdout.strip():
                branches = []
                for line in stdout.splitlines():
                    if not line.strip():
                        continue
                    
                    # Parse branch line
                    is_current = line.startswith('*')
                    branch_line = line[2:].strip()
                    
                    # Extract branch name and info
                    parts = branch_line.split(' ', 1)
                    if len(parts) == 2:
                        branch_name = parts[0]
                        branch_info = parts[1].strip()
                        
                        # Extract tracking info
                        tracking_match = re.search(r'\[(.*?)\]', branch_info)
                        tracking_info = tracking_match.group(1) if tracking_match else None
                        
                        branches.append({
                            "name": branch_name,
                            "is_current": is_current,
                            "tracking_info": tracking_info,
                            "info": branch_info
                        })
                
                result["branches"] = branches
            
            # Get remote info
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {path_obj} && git remote -v",
                check_safety=False
            )
            
            if return_code == 0 and stdout.strip():
                remotes = {}
                for line in stdout.splitlines():
                    if not line.strip():
                        continue
                    
                    # Parse remote line
                    parts = line.split()
                    if len(parts) >= 2:
                        remote_name = parts[0]
                        remote_url = parts[1]
                        remote_type = parts[2][1:-1] if len(parts) >= 3 else "fetch"
                        
                        if remote_name not in remotes:
                            remotes[remote_name] = {}
                        
                        remotes[remote_name][remote_type] = remote_url
                
                result["remotes"] = remotes
            
            # Get git config for the repo
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=f"cd {path_obj} && git config --local --list",
                check_safety=False
            )
            
            if return_code == 0 and stdout.strip():
                git_config = {}
                for line in stdout.splitlines():
                    if not line.strip() or '=' not in line:
                        continue
                    
                    key, value = line.split('=', 1)
                    git_config[key.strip()] = value.strip()
                
                # Extract useful config values
                config_extract = {}
                
                # User info
                if "user.name" in git_config:
                    config_extract["user.name"] = git_config["user.name"]
                if "user.email" in git_config:
                    config_extract["user.email"] = git_config["user.email"]
                
                # Branch default
                if "init.defaultBranch" in git_config:
                    config_extract["default_branch"] = git_config["init.defaultBranch"]
                
                # Pull strategy
                if "pull.rebase" in git_config:
                    config_extract["pull_strategy"] = "rebase" if git_config["pull.rebase"] == "true" else "merge"
                
                result["config"] = config_extract
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error getting detailed Git status: {str(e)}")
            return git_state
    
    async def get_project_tasks(self, project_root: Union[str, Path]) -> Dict[str, Any]:
        """
        Get a list of tasks (todos, issues, pending features, etc.) for the project.
        
        Args:
            project_root: Path to the project root
            
        Returns:
            Dictionary with project tasks
        """
        path_obj = Path(project_root)
        
        # Get the project state
        project_state = await self.get_project_state(path_obj)
        
        # Extract todo items
        todo_items = project_state.get("todo_items", [])
        
        # Look for task files
        tasks_files = []
        for file in ["TODO.md", "TODO.txt", "TASKS.md", "ROADMAP.md"]:
            task_file = path_obj / file
            if task_file.exists():
                tasks_files.append(str(task_file.relative_to(path_obj)))
        
        # Look for GitHub/GitLab issue templates
        issue_templates = []
        for template_dir in [".github/ISSUE_TEMPLATE", ".gitlab/issue_templates"]:
            template_path = path_obj / template_dir
            if template_path.exists() and template_path.is_dir():
                for template_file in template_path.glob("*.md"):
                    issue_templates.append(str(template_file.relative_to(path_obj)))
        
        # Combine everything into a tasks summary
        return {
            "todo_items": todo_items,
            "tasks_files": tasks_files,
            "issue_templates": issue_templates,
            "pending_migrations": project_state.get("migrations", {}).get("pending_migrations", []),
            "failing_tests": project_state.get("test_status", {}).get("failing_tests", []),
            "high_priority_issues": project_state.get("code_quality", {}).get("high_priority_issues", [])
        }

# Global project state analyzer instance
project_state_analyzer = ProjectStateAnalyzer()
