# angela/ai/prompts.py
from typing import Dict, Any

from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Base system instructions
SYSTEM_INSTRUCTIONS = """
You are Angela, an AI-powered command-line assistant integrated into the user's terminal shell.
Your goal is to help users by interpreting their natural language requests and translating them into appropriate shell commands.

Follow these guidelines:
1. Only suggest commands that are safe and appropriate.
2. Prioritize standard Linux shell commands.
3. Focus on practical solutions that work in a terminal environment.
4. For this phase, focus on READ-ONLY commands that don't modify the system.
5. Format your responses in a structured JSON format.
"""

# Examples for few-shot learning
EXAMPLES = [
    {
        "request": "Find all Python files in this project",
        "context": {"project_root": "/home/user/project", "project_type": "python"},
        "response": {
            "intent": "search_files",
            "command": "find . -name '*.py'",
            "explanation": "This command searches for files with the .py extension in the current directory and all subdirectories."
        }
    },
    {
        "request": "Show me disk usage for the current directory",
        "context": {"cwd": "/home/user/project"},
        "response": {
            "intent": "disk_usage",
            "command": "du -sh .",
            "explanation": "This command shows the disk usage (-s) in a human-readable format (-h) for the current directory."
        }
    }
]

def build_prompt(request: str, context: Dict[str, Any]) -> str:
    """Build a prompt for the Gemini API with context information."""
    # Create a context description
    context_str = "Current context:\n"
    if context.get("cwd"):
        context_str += f"- Current working directory: {context['cwd']}\n"
    if context.get("project_root"):
        context_str += f"- Project root: {context['project_root']}\n"
    if context.get("project_type"):
        context_str += f"- Project type: {context['project_type']}\n"
    if context.get("relative_path"):
        context_str += f"- Path relative to project root: {context['relative_path']}\n"
    
    # Add examples for few-shot learning
    examples_str = "Examples:\n"
    for example in EXAMPLES:
        examples_str += f"\nUser request: {example['request']}\n"
        examples_str += f"Context: {example['context']}\n"
        examples_str += f"Response: {example['response']}\n"
    
    # Define the expected response format
    response_format = """
Expected response format (valid JSON):
{
    "intent": "the_classified_intent",
    "command": "the_suggested_command",
    "explanation": "explanation of what the command does",
    "additional_info": "any additional information (optional)"
}
"""
    
    # Build the complete prompt
    prompt = f"{SYSTEM_INSTRUCTIONS}\n\n{context_str}\n\n{examples_str}\n\n{response_format}\n\nUser request: {request}\n\nResponse:"
    
    logger.debug(f"Built prompt with length: {len(prompt)}")
    return prompt
