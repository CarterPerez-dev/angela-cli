# docs/source/ext/usage_examples.py

from docutils import nodes
from docutils.parsers.rst import Directive
import os
import re
import glob

class UsageExamplesDirective(Directive):
    """Directive for extracting usage examples from test files."""
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    
    def run(self):
        examples = []
        
        # Find all test files with specific usage examples
        test_files = glob.glob('tests/usage_examples/*.py')
        
        for test_file in test_files:
            with open(test_file, 'r') as f:
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
                
                # Create the example node
                example_section = nodes.section()
                example_section += nodes.title(text=title)
                
                # Add description
                desc_para = nodes.paragraph()
                desc_para += nodes.Text(description)
                example_section += desc_para
                
                # Add command
                cmd_para = nodes.paragraph()
                cmd_literal = nodes.literal_block(text=f"angela \"{command}\"")
                cmd_para += cmd_literal
                example_section += cmd_para
                
                # Add result
                result_para = nodes.paragraph()
                result_para += nodes.Text("Output:")
                result_literal = nodes.literal_block(text=result)
                result_para += result_literal
                example_section += result_para
                
                examples.append(example_section)
        
        return examples

def setup(app):
    app.add_directive('usage_examples', UsageExamplesDirective)
    
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
