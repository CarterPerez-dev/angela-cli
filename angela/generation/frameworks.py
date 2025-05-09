# angela/generation/frameworks.py
"""
Specialized framework generators for Angela CLI.

This module provides framework-specific code generation capabilities
for popular frameworks like React, Django, Spring, etc.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
import json
import re
import sys

from angela.ai.client import gemini_client, GeminiRequest
from angela.utils.logging import get_logger
from angela.generation.engine import CodeFile

logger = get_logger(__name__)

class FrameworkGenerator:
    """
    Generator for framework-specific code structures.
    
    This class provides specialized generation capabilities for various
    web and application frameworks, creating standardized project structures
    with appropriate files, configurations, and boilerplate code.
    """
    
    def __init__(self):
        """Initialize the framework generator with registered framework handlers."""
        self._logger = logger
        self._logger.info("Initializing FrameworkGenerator")
        
        # Register specialized framework generators
        self._framework_generators = {
            "react": self._generate_react,
            "django": self._generate_django,
            "flask": self._generate_flask,
            "spring": self._generate_spring,
            "express": self._generate_express,
            "fastapi": self._generate_fastapi,
            "vue": self._generate_vue,
            "angular": self._generate_angular
        }
        
        # Framework to project type mapping for better type inference
        self._framework_project_types = {
            "react": "node",
            "vue": "node",
            "angular": "node",
            "express": "node",
            "django": "python",
            "flask": "python",
            "fastapi": "python",
            "spring": "java",
            "rails": "ruby",
            "laravel": "php"
        }
        
        self._logger.debug(f"Registered frameworks: {', '.join(self._framework_generators.keys())}")
    
    async def generate_framework_structure(
        self, 
        framework: str,
        description: str,
        output_dir: Union[str, Path],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a framework-specific project structure.
        
        Args:
            framework: Framework to generate for (e.g., "react", "django")
            description: Description of the project
            output_dir: Directory where the project should be generated
            options: Additional options for the framework (e.g., typescript, variant)
            
        Returns:
            Dictionary with generation results containing:
            - success: Whether generation was successful
            - framework: The framework that was generated
            - files: List of CodeFile objects
            - project_type: Type of project (node, python, etc.)
            - Additional framework-specific information
            
        Raises:
            ValueError: If the framework is not recognized and generic generation fails
        """
        options = options or {}
        framework = framework.lower()
        self._logger.info(f"Generating {framework} structure for: {description}")
        
        try:
            # Get the specialized generator function if available
            generator_func = self._framework_generators.get(framework)
            
            if generator_func:
                # Use specialized generator
                self._logger.debug(f"Using specialized generator for {framework}")
                return await generator_func(description, output_dir, options)
            else:
                # Fallback to generic generator
                self._logger.debug(f"No specialized generator for {framework}, using generic generator")
                return await self._generate_generic(framework, description, output_dir, options)
        except Exception as e:
            self._logger.error(f"Error generating {framework} project: {str(e)}", exc_info=True)
            return {
                "success": False,
                "framework": framework,
                "error": f"Failed to generate {framework} project: {str(e)}",
                "files": []
            }
    
    async def list_supported_frameworks(self) -> List[Dict[str, Any]]:
        """
        Get a list of supported frameworks with details.
        
        Returns:
            List of framework information dictionaries
        """
        frameworks = []
        
        # Add specialized frameworks
        for framework in self._framework_generators.keys():
            frameworks.append({
                "name": framework,
                "type": "specialized",
                "project_type": self._framework_project_types.get(framework, "unknown")
            })
        
        # We could add more supported frameworks here that would use the generic generator
        additional_frameworks = [
            {"name": "svelte", "project_type": "node"},
            {"name": "rails", "project_type": "ruby"},
            {"name": "laravel", "project_type": "php"},
            {"name": "dotnet", "project_type": "csharp"}
        ]
        
        for framework in additional_frameworks:
            if framework["name"] not in self._framework_generators:
                framework["type"] = "generic"
                frameworks.append(framework)
        
        return frameworks
    
    async def _generate_react(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a React project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating React project: {description}")
        
        # Determine React variant (Next.js, Create React App, etc.)
        variant = options.get("variant", "cra").lower()
        
        if variant == "nextjs":
            # Call Next.js generator
            return await self._generate_nextjs(description, output_dir, options)
        
        # Default: Create React App structure
        files = []
        
        # Define project structure
        structure = [
            {
                "path": "public/index.html",
                "content": await self._generate_content("react/index.html", description, options),
                "purpose": "Main HTML file",
                "language": "html"
            },
            {
                "path": "src/index.js",
                "content": await self._generate_content("react/index.js", description, options),
                "purpose": "Application entry point",
                "language": "javascript"
            },
            {
                "path": "src/App.js",
                "content": await self._generate_content("react/App.js", description, options),
                "purpose": "Main application component",
                "language": "javascript"
            },
            {
                "path": "src/App.css",
                "content": await self._generate_content("react/App.css", description, options),
                "purpose": "Application styles",
                "language": "css"
            },
            {
                "path": "package.json",
                "content": await self._generate_content("react/package.json", description, options),
                "purpose": "NPM package configuration",
                "language": "json"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("react/README.md", description, options),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # TypeScript support
        if options.get("typescript", False):
            # Replace .js files with .tsx
            structure = [
                {
                    "path": f.get("path").replace(".js", ".tsx") if f.get("path").endswith(".js") else f.get("path"),
                    "content": await self._generate_content(f.get("path").replace(".js", ".tsx") if f.get("path").endswith(".js") else f.get("path"), description, options),
                    "purpose": f.get("purpose"),
                    "language": "typescript" if f.get("language") == "javascript" else f.get("language")
                }
                for f in structure
            ]
            
            # Add TypeScript config
            structure.append({
                "path": "tsconfig.json",
                "content": await self._generate_content("react/tsconfig.json", description, options),
                "purpose": "TypeScript configuration",
                "language": "json"
            })
        
        # Add testing setup if requested
        if options.get("testing", False):
            test_files = await self._generate_react_testing_files(description, options)
            structure.extend(test_files)
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "react",
            "variant": variant,
            "files": files,
            "project_type": "node"
        }
    
    async def _generate_nextjs(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a Next.js project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating Next.js project: {description}")
        
        files = []
        
        # Define project structure
        structure = [
            {
                "path": "pages/index.js",
                "content": await self._generate_content("nextjs/pages/index.js", description, options),
                "purpose": "Home page component",
                "language": "javascript"
            },
            {
                "path": "pages/_app.js",
                "content": await self._generate_content("nextjs/pages/_app.js", description, options),
                "purpose": "Application wrapper component",
                "language": "javascript"
            },
            {
                "path": "styles/globals.css",
                "content": await self._generate_content("nextjs/styles/globals.css", description, options),
                "purpose": "Global styles",
                "language": "css"
            },
            {
                "path": "package.json",
                "content": await self._generate_content("nextjs/package.json", description, options),
                "purpose": "NPM package configuration",
                "language": "json"
            },
            {
                "path": "next.config.js",
                "content": await self._generate_content("nextjs/next.config.js", description, options),
                "purpose": "Next.js configuration",
                "language": "javascript"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("nextjs/README.md", description, options),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # Add app directory structure if using the new App Router pattern
        if options.get("app_router", False):
            structure.extend([
                {
                    "path": "app/page.js",
                    "content": await self._generate_content("nextjs/app/page.js", description, options),
                    "purpose": "Home page using App Router",
                    "language": "javascript"
                },
                {
                    "path": "app/layout.js",
                    "content": await self._generate_content("nextjs/app/layout.js", description, options),
                    "purpose": "Root layout using App Router",
                    "language": "javascript"
                }
            ])
        
        # TypeScript support
        if options.get("typescript", False):
            # Replace .js files with .tsx
            structure = [
                {
                    "path": f.get("path").replace(".js", ".tsx") if f.get("path").endswith(".js") else f.get("path"),
                    "content": await self._generate_content(f.get("path").replace(".js", ".tsx") if f.get("path").endswith(".js") else f.get("path"), description, options),
                    "purpose": f.get("purpose"),
                    "language": "typescript" if f.get("language") == "javascript" else f.get("language")
                }
                for f in structure
            ]
            
            # Add TypeScript config
            structure.append({
                "path": "tsconfig.json",
                "content": await self._generate_content("nextjs/tsconfig.json", description, options),
                "purpose": "TypeScript configuration",
                "language": "json"
            })
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "react",
            "variant": "nextjs",
            "files": files,
            "project_type": "node"
        }
    
    async def _generate_react_testing_files(
        self,
        description: str,
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate React testing files.
        
        Args:
            description: Project description
            options: Additional options
            
        Returns:
            List of file information dictionaries
        """
        # Determine testing framework
        testing_framework = options.get("testing_framework", "jest").lower()
        
        files = []
        file_extension = ".tsx" if options.get("typescript", False) else ".js"
        
        if testing_framework == "jest":
            files = [
                {
                    "path": f"src/App.test{file_extension}",
                    "content": await self._generate_content(f"react/App.test{file_extension}", description, options),
                    "purpose": "App component tests",
                    "language": "typescript" if options.get("typescript", False) else "javascript"
                },
                {
                    "path": "jest.config.js",
                    "content": await self._generate_content("react/jest.config.js", description, options),
                    "purpose": "Jest configuration",
                    "language": "javascript"
                }
            ]
        elif testing_framework == "cypress":
            files = [
                {
                    "path": "cypress/e2e/home.cy.js",
                    "content": await self._generate_content("react/cypress/e2e/home.cy.js", description, options),
                    "purpose": "Home page E2E tests",
                    "language": "javascript"
                },
                {
                    "path": "cypress.config.js",
                    "content": await self._generate_content("react/cypress.config.js", description, options),
                    "purpose": "Cypress configuration",
                    "language": "javascript"
                }
            ]
        elif testing_framework == "testing-library":
            files = [
                {
                    "path": f"src/App.test{file_extension}",
                    "content": await self._generate_content(f"react/App.test-rtl{file_extension}", description, options),
                    "purpose": "App component tests with React Testing Library",
                    "language": "typescript" if options.get("typescript", False) else "javascript"
                }
            ]
        
        return files
    
    async def _generate_django(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a Django project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating Django project: {description}")
        
        # Get project name
        project_name = options.get("project_name", "django_project")
        project_name = re.sub(r'[^a-zA-Z0-9_]', '_', project_name)
        
        # Get app name
        app_name = options.get("app_name", "main")
        app_name = re.sub(r'[^a-zA-Z0-9_]', '_', app_name)
        
        files = []
        
        # Define project structure
        structure = [
            {
                "path": f"{project_name}/settings.py",
                "content": await self._generate_content("django/settings.py", description, {"project_name": project_name, "app_name": app_name, **options}),
                "purpose": "Django settings",
                "language": "python"
            },
            {
                "path": f"{project_name}/urls.py",
                "content": await self._generate_content("django/urls.py", description, {"project_name": project_name, "app_name": app_name, **options}),
                "purpose": "URL configuration",
                "language": "python"
            },
            {
                "path": f"{project_name}/wsgi.py",
                "content": await self._generate_content("django/wsgi.py", description, {"project_name": project_name, **options}),
                "purpose": "WSGI configuration",
                "language": "python"
            },
            {
                "path": f"{project_name}/asgi.py",
                "content": await self._generate_content("django/asgi.py", description, {"project_name": project_name, **options}),
                "purpose": "ASGI configuration",
                "language": "python"
            },
            {
                "path": f"{project_name}/__init__.py",
                "content": "",
                "purpose": "Package initialization",
                "language": "python"
            },
            {
                "path": f"{app_name}/models.py",
                "content": await self._generate_content("django/models.py", description, {"app_name": app_name, **options}),
                "purpose": "Data models",
                "language": "python"
            },
            {
                "path": f"{app_name}/views.py",
                "content": await self._generate_content("django/views.py", description, {"app_name": app_name, **options}),
                "purpose": "View functions",
                "language": "python"
            },
            {
                "path": f"{app_name}/urls.py",
                "content": await self._generate_content("django/app_urls.py", description, {"app_name": app_name, **options}),
                "purpose": "App URL configuration",
                "language": "python"
            },
            {
                "path": f"{app_name}/__init__.py",
                "content": "",
                "purpose": "App package initialization",
                "language": "python"
            },
            {
                "path": f"{app_name}/templates/{app_name}/index.html",
                "content": await self._generate_content("django/index.html", description, {"app_name": app_name, **options}),
                "purpose": "Main template",
                "language": "html"
            },
            {
                "path": "manage.py",
                "content": await self._generate_content("django/manage.py", description, {"project_name": project_name, **options}),
                "purpose": "Django management script",
                "language": "python"
            },
            {
                "path": "requirements.txt",
                "content": await self._generate_content("django/requirements.txt", description, options),
                "purpose": "Python dependencies",
                "language": "text"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("django/README.md", description, {"project_name": project_name, "app_name": app_name, **options}),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # Add tests if requested
        if options.get("tests", True):
            structure.append({
                "path": f"{app_name}/tests.py",
                "content": await self._generate_content("django/tests.py", description, {"app_name": app_name, **options}),
                "purpose": "Test cases",
                "language": "python"
            })
        
        # Add forms if requested
        if options.get("forms", False):
            structure.append({
                "path": f"{app_name}/forms.py",
                "content": await self._generate_content("django/forms.py", description, {"app_name": app_name, **options}),
                "purpose": "Form definitions",
                "language": "python"
            })
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "django",
            "files": files,
            "project_type": "python",
            "project_name": project_name,
            "app_name": app_name
        }
    
    async def _generate_flask(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a Flask project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating Flask project: {description}")
        
        # Get app name
        app_name = options.get("app_name", "app")
        app_name = re.sub(r'[^a-zA-Z0-9_]', '_', app_name)
        
        files = []
        
        # Define project structure
        structure = [
            {
                "path": "app.py",
                "content": await self._generate_content("flask/app.py", description, {"app_name": app_name, **options}),
                "purpose": "Main application",
                "language": "python"
            },
            {
                "path": "config.py",
                "content": await self._generate_content("flask/config.py", description, options),
                "purpose": "Configuration",
                "language": "python"
            },
            {
                "path": f"{app_name}/__init__.py",
                "content": await self._generate_content("flask/init.py", description, {"app_name": app_name, **options}),
                "purpose": "Application initialization",
                "language": "python"
            },
            {
                "path": f"{app_name}/routes.py",
                "content": await self._generate_content("flask/routes.py", description, options),
                "purpose": "Route definitions",
                "language": "python"
            },
            {
                "path": f"{app_name}/models.py",
                "content": await self._generate_content("flask/models.py", description, options),
                "purpose": "Data models",
                "language": "python"
            },
            {
                "path": "templates/index.html",
                "content": await self._generate_content("flask/index.html", description, options),
                "purpose": "Main template",
                "language": "html"
            },
            {
                "path": "templates/layout.html",
                "content": await self._generate_content("flask/layout.html", description, options),
                "purpose": "Base template",
                "language": "html"
            },
            {
                "path": "static/css/style.css",
                "content": await self._generate_content("flask/style.css", description, options),
                "purpose": "Main stylesheet",
                "language": "css"
            },
            {
                "path": "requirements.txt",
                "content": await self._generate_content("flask/requirements.txt", description, options),
                "purpose": "Python dependencies",
                "language": "text"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("flask/README.md", description, {"app_name": app_name, **options}),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # Add Docker support if requested
        if options.get("docker", False):
            structure.extend([
                {
                    "path": "Dockerfile",
                    "content": await self._generate_content("flask/Dockerfile", description, {"app_name": app_name, **options}),
                    "purpose": "Docker configuration",
                    "language": "dockerfile"
                },
                {
                    "path": "docker-compose.yml",
                    "content": await self._generate_content("flask/docker-compose.yml", description, {"app_name": app_name, **options}),
                    "purpose": "Docker Compose configuration",
                    "language": "yaml"
                }
            ])
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "flask",
            "files": files,
            "project_type": "python",
            "app_name": app_name
        }
    
    async def _generate_express(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate an Express.js project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating Express project: {description}")
        
        files = []
        
        # Define project structure
        structure = [
            {
                "path": "app.js",
                "content": await self._generate_content("express/app.js", description, options),
                "purpose": "Main application",
                "language": "javascript"
            },
            {
                "path": "routes/index.js",
                "content": await self._generate_content("express/routes/index.js", description, options),
                "purpose": "Main routes",
                "language": "javascript"
            },
            {
                "path": "routes/users.js",
                "content": await self._generate_content("express/routes/users.js", description, options),
                "purpose": "User routes",
                "language": "javascript"
            },
            {
                "path": "views/index.ejs",
                "content": await self._generate_content("express/views/index.ejs", description, options),
                "purpose": "Main view template",
                "language": "html"
            },
            {
                "path": "views/error.ejs",
                "content": await self._generate_content("express/views/error.ejs", description, options),
                "purpose": "Error view template",
                "language": "html"
            },
            {
                "path": "public/stylesheets/style.css",
                "content": await self._generate_content("express/public/stylesheets/style.css", description, options),
                "purpose": "Main stylesheet",
                "language": "css"
            },
            {
                "path": "package.json",
                "content": await self._generate_content("express/package.json", description, options),
                "purpose": "NPM package configuration",
                "language": "json"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("express/README.md", description, options),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # Add configuration file
        structure.append({
            "path": "config/config.js",
            "content": await self._generate_content("express/config/config.js", description, options),
            "purpose": "Configuration settings",
            "language": "javascript"
        })
        
        # Add middleware directory
        structure.append({
            "path": "middleware/auth.js",
            "content": await self._generate_content("express/middleware/auth.js", description, options),
            "purpose": "Authentication middleware",
            "language": "javascript"
        })
        
        # TypeScript support
        if options.get("typescript", False):
            # Replace .js files with .ts
            structure = [
                {
                    "path": f.get("path").replace(".js", ".ts") if f.get("path").endswith(".js") else f.get("path"),
                    "content": await self._generate_content(f.get("path").replace(".js", ".ts") if f.get("path").endswith(".js") else f.get("path"), description, options),
                    "purpose": f.get("purpose"),
                    "language": "typescript" if f.get("language") == "javascript" else f.get("language")
                }
                for f in structure
            ]
            
            # Add TypeScript config
            structure.append({
                "path": "tsconfig.json",
                "content": await self._generate_content("express/tsconfig.json", description, options),
                "purpose": "TypeScript configuration",
                "language": "json"
            })
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "express",
            "files": files,
            "project_type": "node"
        }
    
    async def _generate_fastapi(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a FastAPI project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating FastAPI project: {description}")
        
        # Get app name
        app_name = options.get("app_name", "app")
        app_name = re.sub(r'[^a-zA-Z0-9_]', '_', app_name)
        
        files = []
        
        # Define project structure
        structure = [
            {
                "path": "main.py",
                "content": await self._generate_content("fastapi/main.py", description, {"app_name": app_name, **options}),
                "purpose": "Main application",
                "language": "python"
            },
            {
                "path": f"{app_name}/__init__.py",
                "content": "",
                "purpose": "Package initialization",
                "language": "python"
            },
            {
                "path": f"{app_name}/routes.py",
                "content": await self._generate_content("fastapi/routes.py", description, options),
                "purpose": "API routes",
                "language": "python"
            },
            {
                "path": f"{app_name}/models.py",
                "content": await self._generate_content("fastapi/models.py", description, options),
                "purpose": "Data models",
                "language": "python"
            },
            {
                "path": f"{app_name}/schemas.py",
                "content": await self._generate_content("fastapi/schemas.py", description, options),
                "purpose": "Pydantic schemas",
                "language": "python"
            },
            {
                "path": f"{app_name}/database.py",
                "content": await self._generate_content("fastapi/database.py", description, options),
                "purpose": "Database connection",
                "language": "python"
            },
            {
                "path": "requirements.txt",
                "content": await self._generate_content("fastapi/requirements.txt", description, options),
                "purpose": "Python dependencies",
                "language": "text"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("fastapi/README.md", description, {"app_name": app_name, **options}),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # Add dependencies directory for better organization
        structure.append({
            "path": f"{app_name}/dependencies.py",
            "content": await self._generate_content("fastapi/dependencies.py", description, options),
            "purpose": "Dependency injection functions",
            "language": "python"
        })
        
        # Add config module
        structure.append({
            "path": f"{app_name}/config.py",
            "content": await self._generate_content("fastapi/config.py", description, options),
            "purpose": "Configuration settings",
            "language": "python"
        })
        
        # Add Docker support if requested
        if options.get("docker", True):
            structure.extend([
                {
                    "path": "Dockerfile",
                    "content": await self._generate_content("fastapi/Dockerfile", description, {"app_name": app_name, **options}),
                    "purpose": "Docker configuration",
                    "language": "dockerfile"
                },
                {
                    "path": ".dockerignore",
                    "content": await self._generate_content("fastapi/.dockerignore", description, options),
                    "purpose": "Docker ignore file",
                    "language": "text"
                }
            ])
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "fastapi",
            "files": files,
            "project_type": "python",
            "app_name": app_name
        }
    
    async def _generate_spring(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a Spring Boot project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating Spring Boot project: {description}")
        
        # Get package name
        package_name = options.get("package_name", "com.example.demo")
        package_path = package_name.replace(".", "/")
        
        files = []
        
        # Define project structure
        structure = [
            {
                "path": f"src/main/java/{package_path}/Application.java",
                "content": await self._generate_content("spring/Application.java", description, {"package_name": package_name, **options}),
                "purpose": "Main application class",
                "language": "java"
            },
            {
                "path": f"src/main/java/{package_path}/controller/MainController.java",
                "content": await self._generate_content("spring/MainController.java", description, {"package_name": package_name, **options}),
                "purpose": "Main controller",
                "language": "java"
            },
            {
                "path": f"src/main/java/{package_path}/model/User.java",
                "content": await self._generate_content("spring/User.java", description, {"package_name": package_name, **options}),
                "purpose": "User model",
                "language": "java"
            },
            {
                "path": f"src/main/resources/application.properties",
                "content": await self._generate_content("spring/application.properties", description, options),
                "purpose": "Application properties",
                "language": "properties"
            },
            {
                "path": f"src/main/resources/templates/index.html",
                "content": await self._generate_content("spring/index.html", description, options),
                "purpose": "Main template",
                "language": "html"
            },
            {
                "path": "build.gradle",
                "content": await self._generate_content("spring/build.gradle", description, {"package_name": package_name, **options}),
                "purpose": "Gradle build configuration",
                "language": "gradle"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("spring/README.md", description, {"package_name": package_name, **options}),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # Add repository and service layers for better organization
        structure.extend([
            {
                "path": f"src/main/java/{package_path}/repository/UserRepository.java",
                "content": await self._generate_content("spring/UserRepository.java", description, {"package_name": package_name, **options}),
                "purpose": "User repository interface",
                "language": "java"
            },
            {
                "path": f"src/main/java/{package_path}/service/UserService.java",
                "content": await self._generate_content("spring/UserService.java", description, {"package_name": package_name, **options}),
                "purpose": "User service interface",
                "language": "java"
            },
            {
                "path": f"src/main/java/{package_path}/service/impl/UserServiceImpl.java",
                "content": await self._generate_content("spring/UserServiceImpl.java", description, {"package_name": package_name, **options}),
                "purpose": "User service implementation",
                "language": "java"
            }
        ])
        
        # Add Maven support
        if options.get("maven", False) or options.get("build_tool", "gradle") == "maven":
            structure.append({
                "path": "pom.xml",
                "content": await self._generate_content("spring/pom.xml", description, {"package_name": package_name, **options}),
                "purpose": "Maven build configuration",
                "language": "xml"
            })
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "spring",
            "files": files,
            "project_type": "java",
            "package_name": package_name
        }
    
    async def _generate_vue(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a Vue.js project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating Vue.js project: {description}")
        
        files = []
        
        # Define project structure
        structure = [
            {
                "path": "src/main.js",
                "content": await self._generate_content("vue/main.js", description, options),
                "purpose": "Application entry point",
                "language": "javascript"
            },
            {
                "path": "src/App.vue",
                "content": await self._generate_content("vue/App.vue", description, options),
                "purpose": "Main application component",
                "language": "vue"
            },
            {
                "path": "src/components/HelloWorld.vue",
                "content": await self._generate_content("vue/HelloWorld.vue", description, options),
                "purpose": "Example component",
                "language": "vue"
            },
            {
                "path": "src/router/index.js",
                "content": await self._generate_content("vue/router.js", description, options),
                "purpose": "Vue Router configuration",
                "language": "javascript"
            },
            {
                "path": "src/views/Home.vue",
                "content": await self._generate_content("vue/Home.vue", description, options),
                "purpose": "Home page component",
                "language": "vue"
            },
            {
                "path": "src/views/About.vue",
                "content": await self._generate_content("vue/About.vue", description, options),
                "purpose": "About page component",
                "language": "vue"
            },
            {
                "path": "public/index.html",
                "content": await self._generate_content("vue/index.html", description, options),
                "purpose": "Main HTML file",
                "language": "html"
            },
            {
                "path": "package.json",
                "content": await self._generate_content("vue/package.json", description, options),
                "purpose": "NPM package configuration",
                "language": "json"
            },
            {
                "path": "vue.config.js",
                "content": await self._generate_content("vue/vue.config.js", description, options),
                "purpose": "Vue CLI configuration",
                "language": "javascript"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("vue/README.md", description, options),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # Add Vuex store if requested
        if options.get("store", True):
            structure.extend([
                {
                    "path": "src/store/index.js",
                    "content": await self._generate_content("vue/store/index.js", description, options),
                    "purpose": "Vuex store configuration",
                    "language": "javascript"
                },
                {
                    "path": "src/store/modules/auth.js",
                    "content": await self._generate_content("vue/store/modules/auth.js", description, options),
                    "purpose": "Auth store module",
                    "language": "javascript"
                }
            ])
        
        # TypeScript support
        if options.get("typescript", False):
            # Replace .js files with .ts
            structure = [
                {
                    "path": f.get("path").replace(".js", ".ts") if f.get("path").endswith(".js") else f.get("path"),
                    "content": await self._generate_content(f.get("path").replace(".js", ".ts") if f.get("path").endswith(".js") else f.get("path"), description, options),
                    "purpose": f.get("purpose"),
                    "language": "typescript" if f.get("language") == "javascript" else f.get("language")
                }
                for f in structure
            ]
            
            # Add TypeScript config
            structure.append({
                "path": "tsconfig.json",
                "content": await self._generate_content("vue/tsconfig.json", description, options),
                "purpose": "TypeScript configuration",
                "language": "json"
            })
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "vue",
            "files": files,
            "project_type": "node"
        }
    
    async def _generate_angular(
        self,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate an Angular project structure.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating Angular project: {description}")
        
        files = []
        
        # Define project structure
        structure = [
            {
                "path": "src/main.ts",
                "content": await self._generate_content("angular/main.ts", description, options),
                "purpose": "Application entry point",
                "language": "typescript"
            },
            {
                "path": "src/app/app.module.ts",
                "content": await self._generate_content("angular/app.module.ts", description, options),
                "purpose": "Main application module",
                "language": "typescript"
            },
            {
                "path": "src/app/app.component.ts",
                "content": await self._generate_content("angular/app.component.ts", description, options),
                "purpose": "Main application component",
                "language": "typescript"
            },
            {
                "path": "src/app/app.component.html",
                "content": await self._generate_content("angular/app.component.html", description, options),
                "purpose": "Main component template",
                "language": "html"
            },
            {
                "path": "src/app/app.component.css",
                "content": await self._generate_content("angular/app.component.css", description, options),
                "purpose": "Main component styles",
                "language": "css"
            },
            {
                "path": "src/app/app-routing.module.ts",
                "content": await self._generate_content("angular/app-routing.module.ts", description, options),
                "purpose": "Routing configuration",
                "language": "typescript"
            },
            {
                "path": "src/index.html",
                "content": await self._generate_content("angular/index.html", description, options),
                "purpose": "Main HTML file",
                "language": "html"
            },
            {
                "path": "src/styles.css",
                "content": await self._generate_content("angular/styles.css", description, options),
                "purpose": "Global styles",
                "language": "css"
            },
            {
                "path": "angular.json",
                "content": await self._generate_content("angular/angular.json", description, options),
                "purpose": "Angular CLI configuration",
                "language": "json"
            },
            {
                "path": "package.json",
                "content": await self._generate_content("angular/package.json", description, options),
                "purpose": "NPM package configuration",
                "language": "json"
            },
            {
                "path": "tsconfig.json",
                "content": await self._generate_content("angular/tsconfig.json", description, options),
                "purpose": "TypeScript configuration",
                "language": "json"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("angular/README.md", description, options),
                "purpose": "Project documentation",
                "language": "markdown"
            }
        ]
        
        # Add feature module for better organization
        structure.extend([
            {
                "path": "src/app/features/home/home.component.ts",
                "content": await self._generate_content("angular/features/home/home.component.ts", description, options),
                "purpose": "Home feature component",
                "language": "typescript"
            },
            {
                "path": "src/app/features/home/home.component.html",
                "content": await self._generate_content("angular/features/home/home.component.html", description, options),
                "purpose": "Home feature template",
                "language": "html"
            },
            {
                "path": "src/app/features/home/home.module.ts",
                "content": await self._generate_content("angular/features/home/home.module.ts", description, options),
                "purpose": "Home feature module",
                "language": "typescript"
            }
        ])
        
        # Add shared module
        structure.extend([
            {
                "path": "src/app/shared/shared.module.ts",
                "content": await self._generate_content("angular/shared/shared.module.ts", description, options),
                "purpose": "Shared module",
                "language": "typescript"
            },
            {
                "path": "src/app/shared/components/header/header.component.ts",
                "content": await self._generate_content("angular/shared/components/header/header.component.ts", description, options),
                "purpose": "Header component",
                "language": "typescript"
            },
            {
                "path": "src/app/shared/components/header/header.component.html",
                "content": await self._generate_content("angular/shared/components/header/header.component.html", description, options),
                "purpose": "Header template",
                "language": "html"
            }
        ])
        
        # Generate files
        for file_info in structure:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "angular",
            "files": files,
            "project_type": "node"
        }
    
    async def _generate_generic(
        self,
        framework: str,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a generic framework structure using AI.
        
        Args:
            framework: Framework name
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating generic {framework} project: {description}")
        
        # Use AI to generate a project structure
        prompt = f"""
Generate a typical file structure for a {framework} project that matches this description:
"{description}"

Your response should be a JSON object with this structure:
```json
{{
  "files": [
    {{
      "path": "relative/path/to/file.ext",
      "purpose": "brief description of the file's purpose",
      "language": "programming language/file type"
    }}
  ],
  "project_type": "main programming language (e.g., python, node, java)",
  "description": "brief description of the project structure"
}}
Include all essential files for a working {framework} project, including:

Main entry point file(s)
Configuration files
View/template files
Model definitions
Routing or controller files
Package management files (e.g., package.json, requirements.txt)
Documentation

Keep the structure focused on the core framework files, don't include optional or very specific files.
Ensure the structure follows best practices for {framework} projects.
"""
    try:
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )   response = await gemini_client.generate_text(api_request)
        
        # Extract JSON from the response
        structure_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
        if structure_match:
            structure_json = structure_match.group(1)
        else:
            structure_json = response.text
        
        structure_data = json.loads(structure_json)
        
        # Generate content for each file
        files = []
        
        for file_info in structure_data.get("files", []):
            # Generate content for the file
            content = await self._generate_file_content(
                framework,
                file_info["path"],
                file_info["purpose"],
                description,
                options
            )
            
            files.append(CodeFile(
                path=file_info["path"],
                content=content,
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info.get("language")
            ))
        
        return {
            "success": True,
            "framework": framework,
            "files": files,
            "project_type": structure_data.get("project_type", self._infer_project_type(framework))
        }
    
    except json.JSONDecodeError as e:
        self._logger.error(f"Error parsing AI response for {framework} project structure: {e}")
        return {
            "success": False,
            "error": f"Could not generate {framework} project structure: Invalid JSON response",
            "framework": framework
        }
    except Exception as e:
        self._logger.error(f"Error generating {framework} project: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Could not generate {framework} project structure: {str(e)}",
            "framework": framework
        }

    def _infer_project_type(self, framework: str) -> str:
        """
        Infer project type from framework name.
        
        Args:
            framework: Framework name
            
        Returns:
            Inferred project type
        """
        return self._framework_project_types.get(framework.lower(), "unknown")

    async def _generate_content(
        self, 
        template_path: str,
        description: str,
        options: Dict[str, Any]
    ) -> str:
        """
        Generate content for a file based on a template path.
        
        Args:
            template_path: Path to template relative to framework
            description: Project description
            options: Additional options
            
        Returns:
            Generated file content
        """
        self._logger.debug(f"Generating content for template: {template_path}")
        
        # Extract framework and file path
        parts = template_path.split("/", 1)
        if len(parts) < 2:
            # Invalid template path
            framework = "generic"
            file_path = template_path
        else:
            framework = parts[0]
            file_path = parts[1]
        
        return await self._generate_file_content(
            framework,
            file_path,
            "Framework-specific file",
            description,
            options
        )

    async def generate_standard_project_structure(
        self, 
        framework: str,
        description: str,
        output_dir: Union[str, Path],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a standardized project structure for a framework.
        
        This method creates a more complete, production-ready project structure
        compared to the basic structure from generate_framework_structure.
        
        Args:
            framework: Framework to generate for (e.g., "react", "django")
            description: Description of the project
            output_dir: Directory where the project should be generated
            options: Additional options for the framework
            
        Returns:
            Dictionary with generation results
        """
        options = options or {}
        framework = framework.lower()
        self._logger.info(f"Generating standard project for {framework}: {description}")
        
        try:
            # Determine project type based on framework
            project_type = self._framework_project_types.get(framework, "unknown")
            
            # Get enhanced project structure if available
            result = await self._generate_enhanced_framework_structure(
                framework=framework,
                description=description,
                output_dir=output_dir,
                options=options
            )
            
            # If no specialized enhanced structure, fall back to basic
            if not result:
                result = await self.generate_framework_structure(
                    framework=framework,
                    description=description,
                    output_dir=output_dir,
                    options=options
                )
                
            return result
        except Exception as e:
            self._logger.error(f"Error generating standard project for {framework}: {str(e)}")
            return {
                "success": False,
                "framework": framework,
                "error": f"Failed to generate standard project for {framework}: {str(e)}",
                "files": []
            }
    
    async def _generate_enhanced_framework_structure(
        self,
        framework: str,
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an enhanced framework-specific project structure with best practices.
        
        Args:
            framework: Framework to generate for
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results or None if not supported
        """
        # Check for enhanced framework handlers
        handler_method = f"_generate_enhanced_{framework.replace('-', '_')}"
        if hasattr(self, handler_method):
            return await getattr(self, handler_method)(description, output_dir, options)
        
        # No enhanced handler available
        return None
    
    async def _generate_enhanced_react(
        self, 
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate an enhanced React project structure following best practices.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating enhanced React project: {description}")
        
        # Determine React variant
        variant = options.get("variant", "cra").lower()
        
        # Use TypeScript by default for enhanced projects
        use_typescript = options.get("typescript", True)
        
        # Define common file extensions based on TypeScript usage
        ext = ".tsx" if use_typescript else ".jsx"
        style_ext = options.get("style_ext", ".css")
        
        # Common options
        routing = options.get("routing", True)
        state_management = options.get("state_management", "context")  # context, redux, mobx
        styling = options.get("styling", "css")  # css, sass, styled-components, tailwind
        testing = options.get("testing", True)
        
        # Initialize files list
        files = []
        
        # Define project structure based on variant
        if variant == "nextjs":
            # NextJS project structure
            
            # Core configuration files
            files.extend([
                {
                    "path": "next.config.js",
                    "content": await self._generate_content("nextjs/enhanced/next.config.js", description, options),
                    "purpose": "Next.js configuration",
                    "language": "javascript"
                },
                {
                    "path": "package.json",
                    "content": await self._generate_content("nextjs/enhanced/package.json", description, options),
                    "purpose": "Package configuration",
                    "language": "json"
                },
                {
                    "path": ".env.local.example",
                    "content": await self._generate_content("nextjs/enhanced/.env.local.example", description, options),
                    "purpose": "Environment variables example",
                    "language": "env"
                },
                {
                    "path": ".gitignore",
                    "content": await self._generate_content("nextjs/enhanced/.gitignore", description, options),
                    "purpose": "Git ignore configuration",
                    "language": "gitignore"
                },
                {
                    "path": "README.md",
                    "content": await self._generate_content("nextjs/enhanced/README.md", description, options),
                    "purpose": "Project documentation",
                    "language": "markdown"
                }
            ])
            
            # TypeScript configuration
            if use_typescript:
                files.extend([
                    {
                        "path": "tsconfig.json",
                        "content": await self._generate_content("nextjs/enhanced/tsconfig.json", description, options),
                        "purpose": "TypeScript configuration",
                        "language": "json"
                    }
                ])
            
            # Pages or App directory structure
            if options.get("app_router", True):
                # Modern App Router structure
                files.extend([
                    {
                        "path": "app/layout" + ext,
                        "content": await self._generate_content("nextjs/enhanced/app/layout" + ext, description, options),
                        "purpose": "Root layout component",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "app/page" + ext,
                        "content": await self._generate_content("nextjs/enhanced/app/page" + ext, description, options),
                        "purpose": "Home page component",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "app/globals.css",
                        "content": await self._generate_content("nextjs/enhanced/app/globals.css", description, options),
                        "purpose": "Global styles",
                        "language": "css"
                    }
                ])
                
                # Add API route
                files.extend([
                    {
                        "path": f"app/api/example/route{'.ts' if use_typescript else '.js'}",
                        "content": await self._generate_content("nextjs/enhanced/app/api/example/route.ts", description, options),
                        "purpose": "Example API route",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
                
                # Add components directory
                files.extend([
                    {
                        "path": "components/ui/Button" + ext,
                        "content": await self._generate_content("nextjs/enhanced/components/ui/Button" + ext, description, options),
                        "purpose": "Reusable button component",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "components/layout/Header" + ext,
                        "content": await self._generate_content("nextjs/enhanced/components/layout/Header" + ext, description, options),
                        "purpose": "Header component",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
            else:
                # Legacy Pages Router structure
                files.extend([
                    {
                        "path": "pages/index" + ext,
                        "content": await self._generate_content("nextjs/enhanced/pages/index" + ext, description, options),
                        "purpose": "Home page",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "pages/_app" + ext,
                        "content": await self._generate_content("nextjs/enhanced/pages/_app" + ext, description, options),
                        "purpose": "App component",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "pages/_document" + ext,
                        "content": await self._generate_content("nextjs/enhanced/pages/_document" + ext, description, options),
                        "purpose": "Document component",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
                
                # Add API route
                files.extend([
                    {
                        "path": "pages/api/example" + (use_typescript ? ".ts" : ".js"),
                        "content": await self._generate_content("nextjs/enhanced/pages/api/example.ts", description, options),
                        "purpose": "Example API endpoint",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
                
                # Add components directory
                files.extend([
                    {
                        "path": "components/ui/Button" + ext,
                        "content": await self._generate_content("nextjs/enhanced/components/ui/Button" + ext, description, options),
                        "purpose": "Reusable button component",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "components/layout/Header" + ext,
                        "content": await self._generate_content("nextjs/enhanced/components/layout/Header" + ext, description, options),
                        "purpose": "Header component",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
            
            # Add utilities
            files.extend([
                {
                    "path": "lib/utils" + (use_typescript ? ".ts" : ".js"),
                    "content": await self._generate_content("nextjs/enhanced/lib/utils.ts", description, options),
                    "purpose": "Utility functions",
                    "language": "typescript" if use_typescript else "javascript"
                }
            ])
            
            # Add public directory
            files.extend([
                {
                    "path": "public/favicon.ico",
                    "content": "",  # Binary content would be handled differently
                    "purpose": "Favicon",
                    "language": "binary"
                }
            ])
            
            # Add testing if requested
            if testing:
                files.extend([
                    {
                        "path": "__tests__/Home.test" + ext,
                        "content": await self._generate_content("nextjs/enhanced/__tests__/Home.test" + ext, description, options),
                        "purpose": "Home page tests",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "jest.config" + (use_typescript ? ".ts" : ".js"),
                        "content": await self._generate_content("nextjs/enhanced/jest.config.ts", description, options),
                        "purpose": "Jest configuration",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
        else:
            # Create React App or similar structure
            
            # Core configuration files
            files.extend([
                {
                    "path": "package.json",
                    "content": await self._generate_content("react/enhanced/package.json", description, options),
                    "purpose": "Package configuration",
                    "language": "json"
                },
                {
                    "path": ".env.example",
                    "content": await self._generate_content("react/enhanced/.env.example", description, options),
                    "purpose": "Environment variables example",
                    "language": "env"
                },
                {
                    "path": ".gitignore",
                    "content": await self._generate_content("react/enhanced/.gitignore", description, options),
                    "purpose": "Git ignore configuration",
                    "language": "gitignore"
                },
                {
                    "path": "README.md",
                    "content": await self._generate_content("react/enhanced/README.md", description, options),
                    "purpose": "Project documentation",
                    "language": "markdown"
                },
                {
                    "path": "public/index.html",
                    "content": await self._generate_content("react/enhanced/public/index.html", description, options),
                    "purpose": "HTML entry point",
                    "language": "html"
                }
            ])
            
            # TypeScript configuration
            if use_typescript:
                files.extend([
                    {
                        "path": "tsconfig.json",
                        "content": await self._generate_content("react/enhanced/tsconfig.json", description, options),
                        "purpose": "TypeScript configuration",
                        "language": "json"
                    }
                ])
            
            # Core application files
            files.extend([
                {
                    "path": "src/index" + (use_typescript ? ".tsx" : ".jsx"),
                    "content": await self._generate_content("react/enhanced/src/index" + ext, description, options),
                    "purpose": "Application entry point",
                    "language": "typescript" if use_typescript else "javascript"
                },
                {
                    "path": "src/App" + ext,
                    "content": await self._generate_content("react/enhanced/src/App" + ext, description, options),
                    "purpose": "Main App component",
                    "language": "typescript" if use_typescript else "javascript"
                },
                {
                    "path": "src/index.css",
                    "content": await self._generate_content("react/enhanced/src/index.css", description, options),
                    "purpose": "Global styles",
                    "language": "css"
                }
            ])
            
            # Add TypeScript types if needed
            if use_typescript:
                files.extend([
                    {
                        "path": "src/types/index.ts",
                        "content": await self._generate_content("react/enhanced/src/types/index.ts", description, options),
                        "purpose": "TypeScript type definitions",
                        "language": "typescript"
                    }
                ])
            
            # Add routing if requested
            if routing:
                files.extend([
                    {
                        "path": "src/pages/Home" + ext,
                        "content": await self._generate_content("react/enhanced/src/pages/Home" + ext, description, options),
                        "purpose": "Home page component",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "src/pages/About" + ext,
                        "content": await self._generate_content("react/enhanced/src/pages/About" + ext, description, options),
                        "purpose": "About page component",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "src/routes" + (use_typescript ? ".tsx" : ".jsx"),
                        "content": await self._generate_content("react/enhanced/src/routes" + ext, description, options),
                        "purpose": "Route definitions",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
            
            # Add state management
            if state_management == "redux":
                files.extend([
                    {
                        "path": "src/store/index" + (use_typescript ? ".ts" : ".js"),
                        "content": await self._generate_content("react/enhanced/src/store/index.ts", description, options),
                        "purpose": "Redux store configuration",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "src/store/slices/counterSlice" + (use_typescript ? ".ts" : ".js"),
                        "content": await self._generate_content("react/enhanced/src/store/slices/counterSlice.ts", description, options),
                        "purpose": "Example Redux slice",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
            elif state_management == "mobx":
                files.extend([
                    {
                        "path": "src/stores/RootStore" + (use_typescript ? ".ts" : ".js"),
                        "content": await self._generate_content("react/enhanced/src/stores/RootStore.ts", description, options),
                        "purpose": "MobX root store",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "src/stores/CounterStore" + (use_typescript ? ".ts" : ".js"),
                        "content": await self._generate_content("react/enhanced/src/stores/CounterStore.ts", description, options),
                        "purpose": "Example MobX store",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
            else:  # context
                files.extend([
                    {
                        "path": "src/context/AppContext" + ext,
                        "content": await self._generate_content("react/enhanced/src/context/AppContext" + ext, description, options),
                        "purpose": "Application context",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
            
            # Add components directory
            files.extend([
                {
                    "path": "src/components/common/Button" + ext,
                    "content": await self._generate_content("react/enhanced/src/components/common/Button" + ext, description, options),
                    "purpose": "Reusable button component",
                    "language": "typescript" if use_typescript else "javascript"
                },
                {
                    "path": "src/components/layout/Header" + ext,
                    "content": await self._generate_content("react/enhanced/src/components/layout/Header" + ext, description, options),
                    "purpose": "Header component",
                    "language": "typescript" if use_typescript else "javascript"
                },
                {
                    "path": "src/components/layout/Footer" + ext,
                    "content": await self._generate_content("react/enhanced/src/components/layout/Footer" + ext, description, options),
                    "purpose": "Footer component",
                    "language": "typescript" if use_typescript else "javascript"
                }
            ])
            
            # Add utilities
            files.extend([
                {
                    "path": "src/utils/helpers" + (use_typescript ? ".ts" : ".js"),
                    "content": await self._generate_content("react/enhanced/src/utils/helpers.ts", description, options),
                    "purpose": "Helper functions",
                    "language": "typescript" if use_typescript else "javascript"
                },
                {
                    "path": "src/utils/api" + (use_typescript ? ".ts" : ".js"),
                    "content": await self._generate_content("react/enhanced/src/utils/api.ts", description, options),
                    "purpose": "API utilities",
                    "language": "typescript" if use_typescript else "javascript"
                }
            ])
            
            # Add testing if requested
            if testing:
                files.extend([
                    {
                        "path": "src/App.test" + ext,
                        "content": await self._generate_content("react/enhanced/src/App.test" + ext, description, options),
                        "purpose": "App component tests",
                        "language": "typescript" if use_typescript else "javascript"
                    },
                    {
                        "path": "src/components/common/Button.test" + ext,
                        "content": await self._generate_content("react/enhanced/src/components/common/Button.test" + ext, description, options),
                        "purpose": "Button component tests",
                        "language": "typescript" if use_typescript else "javascript"
                    }
                ])
        }
        
        # Generate files
        for file_info in files:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "react",
            "variant": variant,
            "files": files,
            "project_type": "node",
            "typescript": use_typescript,
            "routing": routing,
            "state_management": state_management,
            "styling": styling,
            "testing": testing
        }
    
    async def _generate_enhanced_django(
        self, 
        description: str,
        output_dir: Union[str, Path],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate an enhanced Django project structure following best practices.
        
        Args:
            description: Description of the project
            output_dir: Output directory
            options: Additional options
            
        Returns:
            Dictionary with generation results
        """
        self._logger.info(f"Generating enhanced Django project: {description}")
        
        # Get project name and app name
        project_name = options.get("project_name", "django_project")
        project_name = re.sub(r'[^a-zA-Z0-9_]', '_', project_name)
        
        app_name = options.get("app_name", "main")
        app_name = re.sub(r'[^a-zA-Z0-9_]', '_', app_name)
        
        # Common options
        include_rest_framework = options.get("rest_framework", True)
        include_authentication = options.get("authentication", True)
        include_admin = options.get("admin", True)
        include_static = options.get("static", True)
        include_templates = options.get("templates", True)
        
        # Initialize files list
        files = []
        
        # Core Django files
        files.extend([
            {
                "path": "manage.py",
                "content": await self._generate_content("django/enhanced/manage.py", description, {"project_name": project_name, **options}),
                "purpose": "Django management script",
                "language": "python"
            },
            {
                "path": "requirements.txt",
                "content": await self._generate_content("django/enhanced/requirements.txt", description, {"rest_framework": include_rest_framework, **options}),
                "purpose": "Python dependencies",
                "language": "text"
            },
            {
                "path": "README.md",
                "content": await self._generate_content("django/enhanced/README.md", description, {"project_name": project_name, "app_name": app_name, **options}),
                "purpose": "Project documentation",
                "language": "markdown"
            },
            {
                "path": ".gitignore",
                "content": await self._generate_content("django/enhanced/.gitignore", description, options),
                "purpose": "Git ignore configuration",
                "language": "gitignore"
            }
        ])
        
        # Add Docker support
        if options.get("docker", True):
            files.extend([
                {
                    "path": "Dockerfile",
                    "content": await self._generate_content("django/enhanced/Dockerfile", description, {"app_name": app_name, **options}),
                    "purpose": "Docker configuration",
                    "language": "dockerfile"
                },
                {
                    "path": "docker-compose.yml",
                    "content": await self._generate_content("django/enhanced/docker-compose.yml", description, {"project_name": project_name, **options}),
                    "purpose": "Docker Compose configuration",
                    "language": "yaml"
                },
                {
                    "path": ".dockerignore",
                    "content": await self._generate_content("django/enhanced/.dockerignore", description, options),
                    "purpose": "Docker ignore configuration",
                    "language": "text"
                }
            ])
        }
        
        # Project configuration
        files.extend([
            {
                "path": f"{project_name}/__init__.py",
                "content": "",
                "purpose": "Package initialization",
                "language": "python"
            },
            {
                "path": f"{project_name}/settings.py",
                "content": await self._generate_content("django/enhanced/settings.py", description, {
                    "project_name": project_name, 
                    "app_name": app_name,
                    "rest_framework": include_rest_framework,
                    **options
                }),
                "purpose": "Django settings",
                "language": "python"
            },
            {
                "path": f"{project_name}/urls.py",
                "content": await self._generate_content("django/enhanced/urls.py", description, {
                    "project_name": project_name, 
                    "app_name": app_name,
                    "admin": include_admin,
                    "rest_framework": include_rest_framework,
                    **options
                }),
                "purpose": "URL configuration",
                "language": "python"
            },
            {
                "path": f"{project_name}/wsgi.py",
                "content": await self._generate_content("django/enhanced/wsgi.py", description, {"project_name": project_name, **options}),
                "purpose": "WSGI configuration",
                "language": "python"
            },
            {
                "path": f"{project_name}/asgi.py",
                "content": await self._generate_content("django/enhanced/asgi.py", description, {"project_name": project_name, **options}),
                "purpose": "ASGI configuration",
                "language": "python"
            }
        ])
        
        # Main app structure
        files.extend([
            {
                "path": f"{app_name}/__init__.py",
                "content": "",
                "purpose": "App initialization",
                "language": "python"
            },
            {
                "path": f"{app_name}/admin.py",
                "content": await self._generate_content("django/enhanced/admin.py", description, {"app_name": app_name, **options}),
                "purpose": "Admin configuration",
                "language": "python"
            },
            {
                "path": f"{app_name}/apps.py",
                "content": await self._generate_content("django/enhanced/apps.py", description, {"app_name": app_name, **options}),
                "purpose": "App configuration",
                "language": "python"
            },
            {
                "path": f"{app_name}/models.py",
                "content": await self._generate_content("django/enhanced/models.py", description, {"app_name": app_name, **options}),
                "purpose": "Data models",
                "language": "python"
            },
            {
                "path": f"{app_name}/views.py",
                "content": await self._generate_content("django/enhanced/views.py", description, {
                    "app_name": app_name,
                    "rest_framework": include_rest_framework,
                    **options
                }),
                "purpose": "View functions",
                "language": "python"
            },
            {
                "path": f"{app_name}/urls.py",
                "content": await self._generate_content("django/enhanced/app_urls.py", description, {
                    "app_name": app_name,
                    "rest_framework": include_rest_framework,
                    **options
                }),
                "purpose": "App URL configuration",
                "language": "python"
            },
            {
                "path": f"{app_name}/tests.py",
                "content": await self._generate_content("django/enhanced/tests.py", description, {"app_name": app_name, **options}),
                "purpose": "Test cases",
                "language": "python"
            }
        ])
        
        # Add REST framework files if requested
        if include_rest_framework:
            files.extend([
                {
                    "path": f"{app_name}/serializers.py",
                    "content": await self._generate_content("django/enhanced/serializers.py", description, {"app_name": app_name, **options}),
                    "purpose": "API serializers",
                    "language": "python"
                },
                {
                    "path": f"{app_name}/api.py",
                    "content": await self._generate_content("django/enhanced/api.py", description, {"app_name": app_name, **options}),
                    "purpose": "API views",
                    "language": "python"
                }
            ])
        
        # Add authentication files if requested
        if include_authentication:
            files.extend([
                {
                    "path": f"{app_name}/auth.py",
                    "content": await self._generate_content("django/enhanced/auth.py", description, {"app_name": app_name, **options}),
                    "purpose": "Authentication utilities",
                    "language": "python"
                }
            ])
        
        # Add templates if requested
        if include_templates:
            files.extend([
                {
                    "path": f"{app_name}/templates/{app_name}/base.html",
                    "content": await self._generate_content("django/enhanced/templates/base.html", description, {"app_name": app_name, **options}),
                    "purpose": "Base template",
                    "language": "html"
                },
                {
                    "path": f"{app_name}/templates/{app_name}/index.html",
                    "content": await self._generate_content("django/enhanced/templates/index.html", description, {"app_name": app_name, **options}),
                    "purpose": "Index template",
                    "language": "html"
                }
            ])
        
        # Add static files if requested
        if include_static:
            files.extend([
                {
                    "path": f"{app_name}/static/{app_name}/css/style.css",
                    "content": await self._generate_content("django/enhanced/static/style.css", description, options),
                    "purpose": "Main stylesheet",
                    "language": "css"
                },
                {
                    "path": f"{app_name}/static/{app_name}/js/main.js",
                    "content": await self._generate_content("django/enhanced/static/main.js", description, options),
                    "purpose": "Main JavaScript file",
                    "language": "javascript"
                }
            ])
        
        # Generate files
        for file_info in files:
            files.append(CodeFile(
                path=file_info["path"],
                content=file_info["content"],
                purpose=file_info["purpose"],
                dependencies=[],
                language=file_info["language"]
            ))
        
        return {
            "success": True,
            "framework": "django",
            "files": files,
            "project_type": "python",
            "project_name": project_name,
            "app_name": app_name,
            "rest_framework": include_rest_framework,
            "authentication": include_authentication,
            "admin": include_admin,
            "templates": include_templates,
            "static": include_static
        }
















async def _generate_file_content(
    self, 
    framework: str,
    file_path: str,
    purpose: str,
    description: str,
    options: Dict[str, Any]
) -> str:
    """
    Generate content for a file using AI.
    
    Args:
        framework: Framework name
        file_path: Path to the file
        purpose: Purpose of the file
        description: Project description
        options: Additional options
        
    Returns:
        Generated file content
    """
    # Determine the programming language from the file extension
    ext = Path(file_path).suffix.lower()
    language_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript (React)",
        ".ts": "TypeScript",
        ".tsx": "TypeScript (React)",
        ".java": "Java",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".json": "JSON",
        ".xml": "XML",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".md": "Markdown",
        ".sql": "SQL",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++ Header",
        ".cs": "C#",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".vue": "Vue"
    }
    language = language_map.get(ext, "Unknown")
    
    # Build the prompt
    prompt = f"""
Generate content for a {language} file in a {framework} project.
File path: {file_path}
File purpose: {purpose}
Project description: "{description}"
Requirements:

Generate complete, valid code for a {language} file
Ensure the code follows best practices for {framework} projects
Make the code clean, well-structured, and well-commented
Only include code relevant to the file's purpose and path
Match the style and idioms typically used in {framework} projects

Only respond with the file content, nothing else.
"""
    # Add language-specific instructions
    if language == "Python":
        prompt += "\nInclude appropriate imports and docstrings. Follow PEP 8 guidelines."
    elif language in ["JavaScript", "TypeScript"]:
        prompt += "\nUse modern ES6+ syntax. Include appropriate imports/exports."
    elif language in ["JavaScript (React)", "TypeScript (React)"]:
        prompt += "\nUse functional components with hooks. Include appropriate imports."
    elif language == "Java":
        prompt += "\nInclude appropriate package declaration, imports, and JavaDoc comments."
    # Add framework-specific information
    if framework == "react":
        if "variant" in options and options["variant"] == "nextjs":
            prompt += "\nThis is a Next.js project. Use Next.js-specific patterns and API."
        else:
            prompt += "\nThis is a Create React App project. Use appropriate React patterns."
    elif framework == "django":
        prompt += f"\nProject name: {options.get('project_name', 'django_project')}"
        prompt += f"\nApp name: {options.get('app_name', 'main')}"
    
    try:
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Extract code from the response
        code_match = re.search(r'```(?:\w+)?\s*(.*?)\s*```', response.text, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        # No code block found, use the entire response
        return response.text.strip()
    except Exception as e:
        self._logger.error(f"Error generating content for {file_path}: {str(e)}", exc_info=True)
        return f"# Error generating content: {str(e)}\n# Please regenerate this file"
Global framework generator instance
framework_generator = FrameworkGenerator()
