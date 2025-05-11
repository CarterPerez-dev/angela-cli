# angela/ai/client.py
import asyncio
from typing import Dict, Any, Optional

import google.generativeai as genai
from pydantic import BaseModel

from angela.api.utils import get_config_manager
from angela.constants import GEMINI_MODEL, GEMINI_MAX_TOKENS, GEMINI_TEMPERATURE
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class GeminiRequest(BaseModel):
    """Model for a request to the Gemini API."""
    prompt: str
    temperature: float = GEMINI_TEMPERATURE
    max_output_tokens: int = GEMINI_MAX_TOKENS
    
class GeminiResponse(BaseModel):
    """Model for a response from the Gemini API."""
    text: str
    generated_text: str
    raw_response: Dict[str, Any]

class GeminiClient:
    """Client for interacting with the Google Gemini API."""
    
    def __init__(self):
        """Initialize the Gemini API client."""
        self._setup_client()
        
    def _setup_client(self):
        """Set up the Gemini API client."""
        config_manager = get_config_manager()
        api_key = config_manager.config.api.gemini_api_key
        if not api_key:
            logger.error("Gemini API key is not configured.")
            raise ValueError("Gemini API key is not configured. Run 'angela init' to set it up.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        logger.debug(f"Gemini API client initialized with model: {GEMINI_MODEL}")
        
    # Update angela/ai/client.py
    async def generate_text(self, request: GeminiRequest) -> GeminiResponse:
        """Generate text using the Gemini API."""
        try:
            # Configure the generation configuration
            generation_config = genai.types.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_output_tokens,
            )
            
            # Call the Gemini API
            response = await asyncio.to_thread(
                self.model.generate_content,
                request.prompt,
                generation_config=generation_config,
            )
            
            # Process the response
            if not response.text:
                # Don't wrap this in a try/except - let it propagate directly
                raise ValueError("Empty response from Gemini API.")
            
            # Create a structured response - handle different response structures
            try:
                # Try to adapt to different response formats
                if hasattr(response, 'candidates') and response.candidates:
                    # Convert candidate to dict if possible
                    if hasattr(response.candidates[0], '__dict__'):
                        raw_response = response.candidates[0].__dict__
                    elif hasattr(response.candidates[0], 'to_dict'):
                        raw_response = response.candidates[0].to_dict()
                    else:
                        # Fallback - create a simple dict with text
                        raw_response = {"text": response.text}
                else:
                    # Fallback to a simpler format if candidates not available
                    raw_response = {"text": response.text}
                    
                result = GeminiResponse(
                    text=response.text,
                    generated_text=response.text,
                    raw_response=raw_response,
                )
            except Exception as format_error:
                logger.exception(f"Error formatting Gemini response: {str(format_error)}")
                # Even if formatting fails, still provide a valid response
                result = GeminiResponse(
                    text=response.text,
                    generated_text=response.text,
                    raw_response={"text": response.text},
                )
            
            logger.debug(f"Gemini API response received. Length: {len(result.text)}")
            return result
        
        except ValueError as ve:
            # Let ValueError propagate directly
            logger.exception(f"Gemini API returned empty response: {str(ve)}")
            raise
        except Exception as e:
            # Wrap other exceptions
            logger.exception(f"Error calling Gemini API: {str(e)}")
            raise RuntimeError(f"Failed to generate text with Gemini API: {str(e)}")

# Global client instance
gemini_client = GeminiClient()
