"""
Public API for the AI components.

This module provides functions to access AI components with lazy initialization.
"""
from typing import Optional, Type, Any, Callable

from angela.core.registry import registry
from angela.components.ai.client import gemini_client, GeminiRequest
from angela.components.ai.parser import parse_ai_response, CommandSuggestion
from angela.components.ai.prompts import build_prompt
from angela.components.ai.analyzer import error_analyzer
from angela.components.ai.confidence import confidence_scorer
from angela.components.ai.content_analyzer import content_analyzer
from angela.components.ai.intent_analyzer import intent_analyzer
from angela.components.ai.semantic_analyzer import semantic_analyzer

# Gemini Client API
def get_gemini_client():
    """Get the Gemini API client instance."""
    return registry.get_or_create("gemini_client", lambda: gemini_client)

def get_gemini_request_class() -> Type[GeminiRequest]:
    """Get the GeminiRequest class."""
    return GeminiRequest

# Parser API
def get_command_suggestion_class() -> Type[CommandSuggestion]:
    """Get the CommandSuggestion class."""
    return CommandSuggestion

def get_parse_ai_response_func() -> Callable:
    """Get the parse_ai_response function."""
    return parse_ai_response

# Prompt API
def get_build_prompt_func() -> Callable:
    """Get the build_prompt function."""
    return build_prompt

# Analyzer API
def get_error_analyzer():
    """Get the error analyzer instance."""
    return registry.get_or_create("error_analyzer", lambda: error_analyzer)

# Confidence API
def get_confidence_scorer():
    """Get the confidence scorer instance."""
    return registry.get_or_create("confidence_scorer", lambda: confidence_scorer)

# Content Analyzer API
def get_content_analyzer():
    """Get the content analyzer instance."""
    return registry.get_or_create("content_analyzer", lambda: content_analyzer)

# Intent Analyzer API
def get_intent_analyzer():
    """Get the intent analyzer instance."""
    return registry.get_or_create("intent_analyzer", lambda: intent_analyzer)

# Semantic Analyzer API
def get_semantic_analyzer():
    """Get the semantic analyzer instance."""
    return registry.get_or_create("semantic_analyzer", lambda: semantic_analyzer)
