# docs/source/ext/usage_examples.py

"""
Sphinx extension for extracting Angela CLI usage examples from test files.

This extension scans test files in the tests/usage_examples directory and
extracts structured docstrings to generate usage examples in the documentation.
"""

import os
import re
import glob
from typing import List, Dict, Any, Optional, Tuple

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import ViewList

from sphinx.locale import _
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles


class UsageExample:
    """Represents a parsed usage example."""
    
    def __init__(self, title: str, description: str, command: str, result: str, source_file: str):
        self.title = title.strip()
        self.description = description.strip()
        self.command = command.strip()
        self.result = result.strip()
        self.source_file = source_file
        self.category = self._extract_category(source_file)
    
    def _extract_category(self, source_file: str) -> str:
        """Extract category from filename."""
        basename = os.path.basename(source_file)
        name, _ = os.path.splitext(basename)
        return name.replace('_', ' ').title()


class UsageExamplesDirective(SphinxDirective):
    """
    Directive for extracting and displaying usage examples from test files.
    
    Usage:
        .. usage_examples::
           :category: optional_category_filter
    """
    has_content = True
    option_spec = {
        'category': directives.unchanged,
    }
    
    def run(self) -> List[nodes.Node]:
        """Process the directive and generate documentation nodes."""
        # Parse all examples from test files
        examples = self._get_all_examples()
        
        # Filter by category if specified
        category_filter = self.options.get('category', None)
        if category_filter:
            examples = [ex for ex in examples if category_filter.lower() in ex.category.lower()]
        
        # Group examples by category
        categories = self._group_by_category(examples)
        
        # Create the resulting document structure
        result = []
        
        for category, category_examples in categories.items():
            # Create a section for each category
            section = nodes.section()
            section['ids'].append(nodes.make_id(category))
            
            # Add category title
            title = nodes.title(text=category)
            section += title
            
            # Add introductory text for the category
            intro_text = self._get_category_intro(category)
            if intro_text:
                intro_para = nodes.paragraph()
                intro_para += nodes.Text(intro_text)
                section += intro_para
            
            # Add each example in this category
            for example in category_examples:
                example_section = self._create_example_node(example)
                section += example_section
            
            result.append(section)
        
        return result
    
    def _get_all_examples(self) -> List[UsageExample]:
        """Find and parse all usage examples from test files."""
        examples = []
        
        # Find all test files with specific usage examples
        test_files = glob.glob('tests/usage_examples/*.py')
        
        for test_file in test_files:
            # Skip empty or non-existent files
            if not os.path.exists(test_file) or os.path.getsize(test_file) == 0:
                continue
                
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract examples using regex
            example_matches = re.finditer(
                r'"""EXAMPLE:(.*?)DESCRIPTION:(.*?)COMMAND:(.*?)RESULT:(.*?)"""',
                content, re.DOTALL
            )
            
            for match in example_matches:
                title = match.group(1).strip()
                description = match.group(2).strip()
                command = match.group(3).strip()
                result = match.group(4).strip()
                
                example = UsageExample(title, description, command, result, test_file)
                examples.append(example)
        
        return examples
    
    def _group_by_category(self, examples: List[UsageExample]) -> Dict[str, List[UsageExample]]:
        """Group examples by their category."""
        categories = {}
        
        for example in examples:
            if example.category not in categories:
                categories[example.category] = []
            
            categories[example.category].append(example)
        
        # Sort categories alphabetically
        return {k: categories[k] for k in sorted(categories.keys())}
    
    def _get_category_intro(self, category: str) -> Optional[str]:
        """Get introductory text for a category."""
        # Map of category introductions
        intros = {
            "Command Execution": "These examples demonstrate how to execute commands with Angela CLI.",
            "Context Awareness": "These examples show how Angela CLI understands your project context.",
            "File Operations": "Examples of file and directory operations using Angela CLI.",
            "Git Operations": "Examples of Git version control operations using Angela CLI.",
            "Workflows": "Examples of defining and running workflows with Angela CLI.",
            "Safety Features": "These examples demonstrate Angela CLI's safety and rollback features.",
            "Error Recovery": "Examples showing how Angela CLI handles and recovers from errors.",
            "Advanced Features": "These examples showcase Angela CLI's more advanced capabilities.",
            "Tools Integration": "Examples of Angela CLI integrating with developer tools.",
            "Testing Debugging": "Examples of using Angela CLI for testing and debugging."
        }
        
        return intros.get(category, None)
    
    def _create_example_node(self, example: UsageExample) -> nodes.Node:
        """Create a docutils node for a single example."""
        # Create the example section
        section = nodes.section()
        section['ids'].append(nodes.make_id(f"{example.category}-{example.title}"))
        
        # Add example title
        title = nodes.title(text=example.title)
        section += title
        
        # Add description
        desc_para = nodes.paragraph()
        desc_para += nodes.Text(example.description)
        section += desc_para
        
        # Add command
        cmd_header = nodes.paragraph()
        cmd_header += nodes.strong(text="Command:")
        section += cmd_header
        
        cmd_block = nodes.literal_block(text=f"angela \"{example.command}\"")
        cmd_block['language'] = 'bash'
        section += cmd_block
        
        # Add result
        result_header = nodes.paragraph()
        result_header += nodes.strong(text="Output:")
        section += result_header
        
        result_block = nodes.literal_block(text=example.result)
        section += result_block
        
        return section


def setup(app):
    """Set up the Sphinx extension."""
    app.add_directive('usage_examples', UsageExamplesDirective)
    
    return {
        'version': '0.2',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
