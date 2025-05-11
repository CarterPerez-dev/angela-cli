# angela/components/ai/__init__.py
"""
AI components for Angela CLI.

This package provides AI-powered functionalities including content analysis,
command generation, intent understanding, and semantic code comprehension.
"""

# Core AI infrastructure - these don't create circular imports
from .client import gemini_client, GeminiRequest
from .parser import parse_ai_response, CommandSuggestion
from .prompts import build_prompt

# Import confidence_scorer directly instead of through the API layer
from .confidence import confidence_scorer

# Define __all__ with the directly imported components
__all__ = [
    # Core AI
    'gemini_client', 'GeminiRequest', 'parse_ai_response', 
    'CommandSuggestion', 'build_prompt',
    'confidence_scorer',  # Add direct export
]

# Lazy loading functions - these prevent circular imports
def get_error_analyzer():
    from .analyzer import error_analyzer
    return error_analyzer

def get_intent_analyzer():
    from .intent_analyzer import intent_analyzer
    return intent_analyzer

def get_content_analyzer():
    from .content_analyzer import content_analyzer
    return content_analyzer

def get_semantic_analyzer():
    from .semantic_analyzer import semantic_analyzer
    return semantic_analyzer

# Update __all__ to include the getter functions
__all__ += [
    'get_error_analyzer', 'get_intent_analyzer', 'get_content_analyzer',
    'get_semantic_analyzer'
]
