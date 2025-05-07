# angela/generation/frameworks.py
"""
Specialized framework generators for Angela CLI.

This module provides framework-specific code generation capabilities
for popular frameworks like React, Django, Spring, etc.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import json
import re

from angela.ai.client import gemini_client, GeminiRequest
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class FrameworkGenerator:
    """
    Base class for framework-specific generators.
    """
    
    def __init__(self):
        """Initialize the framework generator."""
        self._logger = logger
    
    async def generate_feature(
        self, 
        description: str,
        project_path: Path,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a new feature for a framework project.
        
        Args:
            description: Description of the feature to add
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Dictionary with generated feature information
        """
        raise NotImplementedError("Subclasses must implement generate_feature")
    
    async def generate_component(
        self, 
        description: str,
        component_type: str,
        project_path: Path,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a component for a framework project.
        
        Args:
            description: Description of the component
            component_type: Type of component to generate
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Dictionary with generated component information
        """
        raise NotImplementedError("Subclasses must implement generate_component")
    
    async def _build_prompt(self, task_type: str, task_description: str, project_analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Build a prompt for the AI service.
        
        Args:
            task_type: Type of task (feature, component, etc.)
            task_description: Description of the task
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Prompt string for the AI service
        """
        raise NotImplementedError("Subclasses must implement _build_prompt")

class ReactGenerator(FrameworkGenerator):
    """
    Generator for React framework projects.
    """
    
    async def generate_feature(
        self, 
        description: str,
        project_path: Path,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a new feature for a React project.
        
        Args:
            description: Description of the feature to add
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Dictionary with generated feature information
        """
        self._logger.info(f"Generating React feature: {description}")
        
        # Build prompt for the AI
        prompt = await self._build_prompt("feature", description, project_analysis, context)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.2
        )
        
        self._logger.debug("Sending React feature generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        return await self._parse_response(response.text, project_path, project_analysis)
    
    async def generate_component(
        self, 
        description: str,
        component_type: str,
        project_path: Path,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a React component.
        
        Args:
            description: Description of the component
            component_type: Type of component (functional, class, etc.)
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Dictionary with generated component information
        """
        self._logger.info(f"Generating React {component_type} component: {description}")
        
        # Build prompt for the AI
        prompt = await self._build_prompt("component", description, project_analysis, context)
        
        # Add component type information
        prompt += f"\nThe component should be a {component_type} component."
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )
        
        self._logger.debug("Sending React component generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        return await self._parse_response(response.text, project_path, project_analysis)
    
    async def _build_prompt(self, task_type: str, task_description: str, project_analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Build a prompt for React code generation.
        
        Args:
            task_type: Type of task (feature, component, etc.)
            task_description: Description of the task
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Prompt string for the AI service
        """
        # Determine project structure type
        is_next_js = False
        is_create_react_app = False
        is_vite = False
        
        # Check for Next.js indicators
        for file_info in project_analysis.get("files", []):
            if "next.config.js" in file_info.get("path", ""):
                is_next_js = True
                break
        
        # Check for Create React App indicators
        if not is_next_js:
            for file_info in project_analysis.get("files", []):
                if "react-scripts" in file_info.get("content", ""):
                    is_create_react_app = True
                    break
        
        # Check for Vite indicators
        if not is_next_js and not is_create_react_app:
            for file_info in project_analysis.get("files", []):
                if "vite.config.js" in file_info.get("path", "") or "vite.config.ts" in file_info.get("path", ""):
                    is_vite = True
                    break
        
        # Determine project structure
        project_structure = "Generic React"
        if is_next_js:
            project_structure = "Next.js"
        elif is_create_react_app:
            project_structure = "Create React App"
        elif is_vite:
            project_structure = "Vite React"
        
        # Determine if TypeScript is used
        uses_typescript = False
        for file_info in project_analysis.get("files", []):
            if file_info.get("path", "").endswith((".ts", ".tsx")):
                uses_typescript = True
                break
        
        # Determine component style (functional vs class)
        uses_functional_components = True
        for file_info in project_analysis.get("files", []):
            if file_info.get("type") == "source_code" and file_info.get("language") in ["JavaScript", "TypeScript"]:
                content = file_info.get("content", "")
                if content and "class " in content and " extends React.Component" in content:
                    uses_functional_components = False
                    break
        
        # Determine styling method
        uses_css_modules = False
        uses_styled_components = False
        uses_emotion = False
        uses_tailwind = False
        
        for file_info in project_analysis.get("files", []):
            if file_info.get("path", "").endswith(".module.css") or file_info.get("path", "").endswith(".module.scss"):
                uses_css_modules = True
            
            content = file_info.get("content", "")
            if content:
                if "styled-components" in content:
                    uses_styled_components = True
                if "@emotion/styled" in content or "@emotion/react" in content:
                    uses_emotion = True
                if "tailwindcss" in content or "tailwind.config" in content:
                    uses_tailwind = True
        
        # Build prompt
        if task_type == "feature":
            prompt = f"""
You are an expert React developer tasked with adding a new feature to a {project_structure} project.

Feature description: "{task_description}"

Project information:
- Uses TypeScript: {uses_typescript}
- Component style: {'Functional components with hooks' if uses_functional_components else 'Class components'}
- Styling method: {', '.join(method for method, used in [('CSS Modules', uses_css_modules), ('Styled Components', uses_styled_components), ('Emotion', uses_emotion), ('Tailwind CSS', uses_tailwind)] if used) or 'Standard CSS'}

Analyze the feature request and provide:
1. New components needed
2. Modifications to existing components or files
3. Styling requirements
4. Any state management considerations

Your response should be a JSON object with this structure:
```json
{{
  "new_files": [
    {{
      "path": "relative/path/to/file.ext",
      "purpose": "description of the file's purpose",
      "content": "complete file content"
    }}
  ],
  "modified_files": [
    {{
      "path": "relative/path/to/existing/file.ext",
      "purpose": "description of the modifications",
      "original_content": "provide some context from the original file",
      "modified_content": "complete modified file content"
    }}
  ],
  "explanation": "explanation of how the feature works and integrates with the existing codebase"
}}
```

Follow these React best practices:
1. Use {'functional components and hooks' if uses_functional_components else 'class components'} to match the project style
2. Use {'TypeScript types/interfaces' if uses_typescript else 'PropTypes'} for component props
3. Follow the existing project structure and naming conventions
4. Use appropriate styling methods that match the project's approach
5. Consider performance optimizations (useMemo, useCallback, etc.) where appropriate
"""
        elif task_type == "component":
            prompt = f"""
You are an expert React developer tasked with creating a new component for a {project_structure} project.

Component description: "{task_description}"

Project information:
- Uses TypeScript: {uses_typescript}
- Component style: {'Functional components with hooks' if uses_functional_components else 'Class components'}
- Styling method: {', '.join(method for method, used in [('CSS Modules', uses_css_modules), ('Styled Components', uses_styled_components), ('Emotion', uses_emotion), ('Tailwind CSS', uses_tailwind)] if used) or 'Standard CSS'}

Analyze the component requirements and provide:
1. Component implementation
2. Any helper functions or sub-components
3. Styling
4. Tests (if appropriate)

Your response should be a JSON object with this structure:
```json
{{
  "files": [
    {{
      "path": "suggested/path/to/component.{'.tsx' if uses_typescript else '.jsx'}",
      "purpose": "The main component file",
      "content": "complete file content"
    }},
    {{
      "path": "suggested/path/to/component.{'.module.css' if uses_css_modules else '.css'}",
      "purpose": "Styles for the component",
      "content": "complete file content"
    }},
    {{
      "path": "suggested/path/to/component.test.{'.tsx' if uses_typescript else '.jsx'}",
      "purpose": "Tests for the component",
      "content": "complete file content"
    }}
  ],
  "explanation": "explanation of how the component works and how to use it"
}}
```

Follow these React best practices:
1. Use {'functional components and hooks' if uses_functional_components else 'class components'} to match the project style
2. Use {'TypeScript types/interfaces' if uses_typescript else 'PropTypes'} for component props
3. Follow the existing project structure and naming conventions
4. Use appropriate styling methods that match the project's approach
5. Consider performance optimizations (useMemo, useCallback, etc.) where appropriate
"""
        
        # Add project files for context
        prompt += "\n\nRelevant existing project files for context:"
        
        # Find and add some relevant React files
        relevant_files = []
        extensions = ['.jsx', '.tsx', '.js', '.ts'] if uses_typescript else ['.jsx', '.js']
        
        for file_info in project_analysis.get("files", []):
            file_path = file_info.get("path", "")
            if any(file_path.endswith(ext) for ext in extensions) and "component" in file_path.lower():
                relevant_files.append(file_info)
                if len(relevant_files) >= 3:  # Limit to 3 files
                    break
        
        for file_info in relevant_files:
            content = file_info.get("content", "")
            if content:
                if len(content) > 1000:  # Limit content size
                    content = content[:1000] + "\n... (truncated)"
                prompt += f"\n\nFile: {file_info.get('path')}\n```\n{content}\n```\n"
        
        return prompt
    
    async def _parse_response(self, response: str, project_path: Path, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the AI response for React code generation.
        
        Args:
            response: AI response text
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            
        Returns:
            Dictionary with parsed generation information
        """
        try:
            # Look for JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Assume the entire response is JSON
                    json_str = response
            
            # Parse the JSON
            data = json.loads(json_str)
            
            # Restructure the data
            result = {
                "new_files": data.get("new_files", data.get("files", [])),
                "modified_files": data.get("modified_files", []),
                "explanation": data.get("explanation", "No explanation provided")
            }
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error parsing React generation response: {str(e)}")
            
            # Return a minimal fallback
            return {
                "new_files": [],
                "modified_files": [],
                "explanation": "Failed to parse AI response. Please try again with a more specific description."
            }

class DjangoGenerator(FrameworkGenerator):
    """
    Generator for Django framework projects.
    """
    
    async def generate_feature(
        self, 
        description: str,
        project_path: Path,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a new feature for a Django project.
        
        Args:
            description: Description of the feature to add
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Dictionary with generated feature information
        """
        self._logger.info(f"Generating Django feature: {description}")
        
        # Build prompt for the AI
        prompt = await self._build_prompt("feature", description, project_analysis, context)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.2
        )
        
        self._logger.debug("Sending Django feature generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        return await self._parse_response(response.text, project_path, project_analysis)
    
    async def generate_component(
        self, 
        description: str,
        component_type: str,
        project_path: Path,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a Django component.
        
        Args:
            description: Description of the component
            component_type: Type of component (model, view, form, etc.)
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Dictionary with generated component information
        """
        self._logger.info(f"Generating Django {component_type}: {description}")
        
        # Build prompt for the AI
        prompt = await self._build_prompt("component", description, project_analysis, context)
        
        # Add component type information
        prompt += f"\nThe component should be a Django {component_type}."
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )
        
        self._logger.debug(f"Sending Django {component_type} generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        return await self._parse_response(response.text, project_path, project_analysis)
    
    async def _build_prompt(self, task_type: str, task_description: str, project_analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Build a prompt for Django code generation.
        
        Args:
            task_type: Type of task (feature, component, etc.)
            task_description: Description of the task
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Prompt string for the AI service
        """
        # Find Django settings file
        settings_file = None
        for file_info in project_analysis.get("files", []):
            if file_info.get("path", "").endswith("settings.py"):
                settings_file = file_info
                break
        
        # Find existing Django apps
        django_apps = []
        if settings_file and settings_file.get("content"):
            # Look for INSTALLED_APPS in settings.py
            match = re.search(r'INSTALLED_APPS\s*=\s*\[\s*(.*?)\s*\]', settings_file.get("content"), re.DOTALL)
            if match:
                apps_text = match.group(1)
                # Extract app names
                apps = re.findall(r'[\'"]([^\'";]+)[\'"]', apps_text)
                # Filter out Django's built-in apps
                django_apps = [app for app in apps if not app.startswith('django.')]
        
        # Find URL configuration
        urls_file = None
        for file_info in project_analysis.get("files", []):
            if file_info.get("path", "").endswith("urls.py"):
                urls_file = file_info
                break
        
        # Find models
        models = []
        for file_info in project_analysis.get("files", []):
            if file_info.get("path", "").endswith("models.py") and file_info.get("content"):
                # Extract model classes
                for match in re.finditer(r'class\s+(\w+)\s*\(\s*models\.Model\s*\)', file_info.get("content")):
                    models.append(match.group(1))
        
        # Build prompt
        if task_type == "feature":
            prompt = f"""
You are an expert Django developer tasked with adding a new feature to a Django project.

Feature description: "{task_description}"

Project information:
- Django apps: {django_apps if django_apps else 'Unknown'}
- Models: {models if models else 'Unknown'}

Analyze the feature request and provide:
1. Which Django app the feature should be added to (or if a new app is needed)
2. Models required/modified for the feature
3. Views, forms, templates, and URL patterns
4. Any migrations or settings changes

Your response should be a JSON object with this structure:
```json
{{
  "new_files": [
    {{
      "path": "relative/path/to/file.ext",
      "purpose": "description of the file's purpose",
      "content": "complete file content"
    }}
  ],
  "modified_files": [
    {{
      "path": "relative/path/to/existing/file.ext",
      "purpose": "description of the modifications",
      "original_content": "provide some context from the original file",
      "modified_content": "complete modified file content"
    }}
  ],
  "explanation": "explanation of how the feature works and integrates with the existing codebase",
  "migrations": [
    "Instructions for any migrations needed"
  ]
}}
```

Follow these Django best practices:
1. Use Django's MTV (Model-Template-View) pattern
2. Follow DRY (Don't Repeat Yourself) principles
3. Use Django's form handling for user input
4. Leverage Django's built-in features when appropriate
5. Follow proper URL namespace conventions
"""
        elif task_type == "component":
            prompt = f"""
You are an expert Django developer tasked with creating a new component for a Django project.

Component description: "{task_description}"

Project information:
- Django apps: {django_apps if django_apps else 'Unknown'}
- Models: {models if models else 'Unknown'}

Analyze the component requirements and provide:
1. Implementation details
2. Integration with existing project
3. Any required imports or dependencies

Your response should be a JSON object with this structure:
```json
{{
  "files": [
    {{
      "path": "suggested/path/to/component.py",
      "purpose": "The main component file",
      "content": "complete file content"
    }},
    {{
      "path": "suggested/path/to/template.html",
      "purpose": "Template for the component",
      "content": "complete file content"
    }}
  ],
  "explanation": "explanation of how the component works and how to use it"
}}
```

Follow these Django best practices:
1. Use Django's MTV (Model-Template-View) pattern
2. Follow DRY (Don't Repeat Yourself) principles
3. Use Django's form handling for user input
4. Leverage Django's built-in features when appropriate
5. Follow proper URL namespace conventions
"""
        
        # Add project files for context
        prompt += "\n\nRelevant existing project files for context:"
        
        # Find and add some relevant Django files
        relevant_files = []
        
        # Add models.py
        for file_info in project_analysis.get("files", []):
            if file_info.get("path", "").endswith("models.py"):
                relevant_files.append(file_info)
                break
        
        # Add views.py
        for file_info in project_analysis.get("files", []):
            if file_info.get("path", "").endswith("views.py"):
                relevant_files.append(file_info)
                break
        
        # Add urls.py
        if urls_file:
            relevant_files.append(urls_file)
        
        # Add settings.py
        if settings_file:
            relevant_files.append(settings_file)
        
        for file_info in relevant_files:
            content = file_info.get("content", "")
            if content:
                if len(content) > 1000:  # Limit content size
                    content = content[:1000] + "\n... (truncated)"
                prompt += f"\n\nFile: {file_info.get('path')}\n```\n{content}\n```\n"
        
        return prompt
    
    async def _parse_response(self, response: str, project_path: Path, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the AI response for Django code generation.
        
        Args:
            response: AI response text
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            
        Returns:
            Dictionary with parsed generation information
        """
        try:
            # Look for JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Assume the entire response is JSON
                    json_str = response
            
            # Parse the JSON
            data = json.loads(json_str)
            
            # Restructure the data
            result = {
                "new_files": data.get("new_files", data.get("files", [])),
                "modified_files": data.get("modified_files", []),
                "explanation": data.get("explanation", "No explanation provided"),
                "migrations": data.get("migrations", [])
            }
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error parsing Django generation response: {str(e)}")
            
            # Return a minimal fallback
            return {
                "new_files": [],
                "modified_files": [],
                "explanation": "Failed to parse AI response. Please try again with a more specific description.",
                "migrations": []
            }

class SpringGenerator(FrameworkGenerator):
    """
    Generator for Spring framework projects.
    """
    
    async def generate_feature(
        self, 
        description: str,
        project_path: Path,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a new feature for a Spring project.
        
        Args:
            description: Description of the feature to add
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Dictionary with generated feature information
        """
        self._logger.info(f"Generating Spring feature: {description}")
        
        # Build prompt for the AI
        prompt = await self._build_prompt("feature", description, project_analysis, context)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.2
        )
        
        self._logger.debug("Sending Spring feature generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        return await self._parse_response(response.text, project_path, project_analysis)
    
    async def generate_component(
        self, 
        description: str,
        component_type: str,
        project_path: Path,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a Spring component.
        
        Args:
            description: Description of the component
            component_type: Type of component (controller, service, repository, etc.)
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Dictionary with generated component information
        """
        self._logger.info(f"Generating Spring {component_type}: {description}")
        
        # Build prompt for the AI
        prompt = await self._build_prompt("component", description, project_analysis, context)
        
        # Add component type information
        prompt += f"\nThe component should be a Spring {component_type}."
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )
        
        self._logger.debug(f"Sending Spring {component_type} generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        return await self._parse_response(response.text, project_path, project_analysis)
    
    async def _build_prompt(self, task_type: str, task_description: str, project_analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Build a prompt for Spring code generation.
        
        Args:
            task_type: Type of task (feature, component, etc.)
            task_description: Description of the task
            project_analysis: Analysis of the existing project
            context: Additional context information
            
        Returns:
            Prompt string for the AI service
        """
        # Determine if it's Spring Boot or traditional Spring
        is_spring_boot = False
        for file_info in project_analysis.get("files", []):
            if "SpringBootApplication" in file_info.get("content", ""):
                is_spring_boot = True
                break
        
        # Find main application class
        main_class = None
        for file_info in project_analysis.get("files", []):
            content = file_info.get("content", "")
            if "public static void main" in content and ".run(" in content:
                # Extract class name
                class_match = re.search(r'class\s+(\w+)', content)
                if class_match:
                    main_class = class_match.group(1)
                break
        
        # Find existing entities/models
        entities = []
        for file_info in project_analysis.get("files", []):
            if file_info.get("content") and ("@Entity" in file_info.get("content") or "JpaRepository" in file_info.get("content")):
                # Extract entity class name
                class_match = re.search(r'class\s+(\w+)', file_info.get("content"))
                if class_match and not class_match.group(1).endswith("Repository"):
                    entities.append(class_match.group(1))
        
        # Find package structure
        package_structure = {}
        for file_info in project_analysis.get("files", []):
            if file_info.get("path", "").endswith(".java"):
                java_path = file_info.get("path", "")
                package_match = re.search(r'package\s+([\w.]+)', file_info.get("content", ""))
                if package_match:
                    package = package_match.group(1)
                    if package not in package_structure:
                        package_structure[package] = []
                    package_structure[package].append(java_path)
        
        # Build prompt
        if task_type == "feature":
            prompt = f"""
You are an expert Spring {'Boot' if is_spring_boot else 'Framework'} developer tasked with adding a new feature to a Spring project.

Feature description: "{task_description}"

Project information:
- Spring Boot: {is_spring_boot}
- Main class: {main_class if main_class else 'Unknown'}
- Entities: {entities if entities else 'Unknown'}
- Package structure: {list(package_structure.keys()) if package_structure else 'Unknown'}

Analyze the feature request and provide:
1. Controllers, services, and repositories needed
2. Entity/model classes required
3. Any configuration changes
4. Tests for the feature

Your response should be a JSON object with this structure:
```json
{{
  "new_files": [
    {{
      "path": "relative/path/to/file.ext",
      "purpose": "description of the file's purpose",
      "content": "complete file content"
    }}
  ],
  "modified_files": [
    {{
      "path": "relative/path/to/existing/file.ext",
      "purpose": "description of the modifications",
      "original_content": "provide some context from the original file",
      "modified_content": "complete modified file content"
    }}
  ],
  "explanation": "explanation of how the feature works and integrates with the existing codebase"
}}
```

Follow these Spring best practices:
1. Use Spring's dependency injection
2. Follow the layered architecture (Controller, Service, Repository)
3. Use appropriate annotations (@RestController, @Service, etc.)
4. Implement proper error handling
5. Write unit and integration tests
"""
        elif task_type == "component":
            prompt = f"""
You are an expert Spring {'Boot' if is_spring_boot else 'Framework'} developer tasked with creating a new component for a Spring project.

Component description: "{task_description}"

Project information:
- Spring Boot: {is_spring_boot}
- Main class: {main_class if main_class else 'Unknown'}
- Entities: {entities if entities else 'Unknown'}
- Package structure: {list(package_structure.keys()) if package_structure else 'Unknown'}

Analyze the component requirements and provide:
1. Implementation details
2. Integration with existing project
3. Any required dependencies or configuration

Your response should be a JSON object with this structure:
```json
{{
  "files": [
    {{
      "path": "suggested/path/to/component.java",
      "purpose": "The main component file",
      "content": "complete file content"
    }},
    {{
      "path": "suggested/path/to/test.java",
      "purpose": "Test for the component",
      "content": "complete file content"
    }}
  ],
  "explanation": "explanation of how the component works and how to use it"
}}
```

Follow these Spring best practices:
1. Use Spring's dependency injection
2. Follow the layered architecture (Controller, Service, Repository)
3. Use appropriate annotations (@RestController, @Service, etc.)
4. Implement proper error handling
5. Write unit and integration tests
"""
        
        # Add project files for context
        prompt += "\n\nRelevant existing project files for context:"
        
        # Find and add some relevant Spring files
        relevant_files = []
        
        # Add main application class
        for file_info in project_analysis.get("files", []):
            if file_info.get("content") and "public static void main" in file_info.get("content") and ".run(" in file_info.get("content"):
                relevant_files.append(file_info)
                break
        
        # Add an entity class
        for file_info in project_analysis.get("files", []):
            if file_info.get("content") and "@Entity" in file_info.get("content"):
                relevant_files.append(file_info)
                break
        
        # Add a controller class
        for file_info in project_analysis.get("files", []):
            if file_info.get("content") and ("@RestController" in file_info.get("content") or "@Controller" in file_info.get("content")):
                relevant_files.append(file_info)
                break
        
        # Add a service class
        for file_info in project_analysis.get("files", []):
            if file_info.get("content") and "@Service" in file_info.get("content"):
                relevant_files.append(file_info)
                break
        
        for file_info in relevant_files:
            content = file_info.get("content", "")
            if content:
                if len(content) > 1000:  # Limit content size
                    content = content[:1000] + "\n... (truncated)"
                prompt += f"\n\nFile: {file_info.get('path')}\n```\n{content}\n```\n"
        
        return prompt
    
    async def _parse_response(self, response: str, project_path: Path, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the AI response for Spring code generation.
        
        Args:
            response: AI response text
            project_path: Path to the project
            project_analysis: Analysis of the existing project
            
        Returns:
            Dictionary with parsed generation information
        """
        try:
            # Look for JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Assume the entire response is JSON
                    json_str = response
            
            # Parse the JSON
            data = json.loads(json_str)
            
            # Restructure the data
            result = {
                "new_files": data.get("new_files", data.get("files", [])),
                "modified_files": data.get("modified_files", []),
                "explanation": data.get("explanation", "No explanation provided")
            }
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error parsing Spring generation response: {str(e)}")
            
            # Return a minimal fallback
            return {
                "new_files": [],
                "modified_files": [],
                "explanation": "Failed to parse AI response. Please try again with a more specific description."
            }

# Map of supported frameworks to their generator classes
FRAMEWORK_GENERATORS = {
    "react": ReactGenerator(),
    "django": DjangoGenerator(),
    "spring": SpringGenerator()
}

async def get_generator_for_project(project_analysis: Dict[str, Any]) -> Optional[FrameworkGenerator]:
    """
    Get the appropriate framework generator for a project.
    
    Args:
        project_analysis: Analysis of the existing project
        
    Returns:
        FrameworkGenerator instance or None if no matching framework found
    """
    logger.info("Determining framework for project")
    
    # Check for React
    for file_info in project_analysis.get("files", []):
        if "react" in file_info.get("content", "").lower() or file_info.get("path", "").endswith((".jsx", ".tsx")):
            logger.info("Detected React framework")
            return FRAMEWORK_GENERATORS["react"]
    
    # Check for Django
    for file_info in project_analysis.get("files", []):
        if file_info.get("path", "").endswith("settings.py") and "DJANGO_SETTINGS_MODULE" in file_info.get("content", ""):
            logger.info("Detected Django framework")
            return FRAMEWORK_GENERATORS["django"]
    
    # Check for Spring
    for file_info in project_analysis.get("files", []):
        if "org.springframework" in file_info.get("content", ""):
            logger.info("Detected Spring framework")
            return FRAMEWORK_GENERATORS["spring"]
    
    logger.info("No specific framework detected")
    return None
