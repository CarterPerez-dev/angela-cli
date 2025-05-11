# angela/components/ai/__init__.py
"""
AI components for Angela CLI.

This package provides AI-powered functionalities including content analysis,
command generation, intent understanding, and semantic code comprehension.
"""

# Core AI infrastructure
from .client import gemini_client, GeminiRequest
from .parser import parse_ai_response, CommandSuggestion
from .prompts import build_prompt

# Analysis modules
from .analyzer import error_analyzer
from .confidence import confidence_scorer
from .content_analyzer import content_analyzer
from .intent_analyzer import intent_analyzer
from .semantic_analyzer import semantic_analyzer


__all__ = [
    # Core AI
    'gemini_client', 'GeminiRequest', 'parse_ai_response', 
    'CommandSuggestion', 'build_prompt',
    
    # Analysis components
    'error_analyzer', 'confidence_scorer', 'content_analyzer',
    'intent_analyzer', 'semantic_analyzer'
]
