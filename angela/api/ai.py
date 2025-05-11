"""
Public API for the AI components.

This module provides functions to access AI components with lazy initialization.
"""
from typing import Optional, Type, Any, Callable

from angela.core.registry import registry
from angela.components.ai.client import gemini_client, GeminiRequest
from angela.components.ai.parser import parse_ai_response, CommandSuggestion
from angela.components.ai.prompts import build_prompt


# Gemini Client API
def get_gemini_client():
    """Get the Gemini API client instance."""
    from angela.components.ai.client import GeminiClient, gemini_client 
    return registry.get_or_create("gemini_client", GeminiClient, factory=lambda: gemini_client)

def get_gemini_request_class() -> Type[Any]: 
    """Get the GeminiRequest class."""
    from angela.components.ai.client import GeminiRequest 
    return GeminiRequest

# Parser API
def get_command_suggestion_class() -> Type[Any]: 
    """Get the CommandSuggestion class."""
    from angela.components.ai.parser import CommandSuggestion 
    return CommandSuggestion

def get_parse_ai_response_func() -> Callable:
    """Get the parse_ai_response function."""
    from angela.components.ai.parser import parse_ai_response 
    return parse_ai_response

# Prompt API
def get_build_prompt_func() -> Callable:
    """Get the build_prompt function."""
    from angela.components.ai.prompts import build_prompt 
    return build_prompt

# Analyzer API
def get_error_analyzer():
    """Get the error analyzer instance."""
    from angela.components.ai.analyzer import ErrorAnalyzer, error_analyzer 
    return registry.get_or_create("error_analyzer", ErrorAnalyzer, factory=lambda: error_analyzer)

# Confidence API
def get_confidence_scorer():
    """Get the confidence scorer instance."""
    from angela.components.ai.confidence import ConfidenceScorer, confidence_scorer 
    return registry.get_or_create("confidence_scorer", ConfidenceScorer, factory=lambda: confidence_scorer)

# Content Analyzer API
def get_content_analyzer():
    """Get the content analyzer instance."""
    from angela.components.ai.content_analyzer import ContentAnalyzer, content_analyzer 
    return registry.get_or_create("content_analyzer", ContentAnalyzer, factory=lambda: content_analyzer)

# Intent Analyzer API
def get_intent_analyzer():
    """Get the intent analyzer instance."""
    from angela.components.ai.intent_analyzer import IntentAnalyzer, intent_analyzer 
    return registry.get_or_create("intent_analyzer", IntentAnalyzer, factory=lambda: intent_analyzer)

# Semantic Analyzer API
def get_semantic_analyzer():
    """Get the semantic analyzer instance."""
    from angela.components.ai.semantic_analyzer import SemanticAnalyzer, semantic_analyzer 
    return registry.get_or_create("semantic_analyzer", SemanticAnalyzer, factory=lambda: semantic_analyzer)
