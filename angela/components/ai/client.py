# angela/components/ai/client.py
import asyncio
import random # For jitter in retries
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold

from pydantic import BaseModel, Field

from angela.config import config_manager
from angela.constants import GEMINI_MODEL, GEMINI_MAX_TOKENS, GEMINI_TEMPERATURE
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class GeminiRequest(BaseModel):
    prompt: str
    temperature: float = Field(default=GEMINI_TEMPERATURE)
    max_output_tokens: int = Field(default=GEMINI_MAX_TOKENS)
    # No safety_settings field needed here if we control it via a client method parameter

class GeminiResponse(BaseModel):
    text: str
    generated_text: str
    raw_response: Dict[str, Any]

class GeminiClient:
    def __init__(self):
        self._setup_client()
        # Define the default PERMISSIVE safety settings as an instance variable
        self._default_permissive_safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    def _setup_client(self):
        api_key = config_manager.config.api.gemini_api_key
        if not api_key:
            logger.error("Gemini API key is not configured.")
            raise ValueError("Gemini API key is not configured. Run 'angela init' to set it up.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        logger.debug(f"Gemini API client initialized with model: {GEMINI_MODEL}")

    async def generate_text(
        self,
        request: GeminiRequest,
        use_api_default_safety: bool = False # New parameter, DEFAULTS TO FALSE
    ) -> GeminiResponse:
        max_retries = 1
        base_delay = 2
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    f"GEMINI API REQUEST (Attempt {attempt + 1}/{max_retries + 1}) "
                    f"PROMPT ({len(request.prompt)} chars)"
                )
                logger.debug(
                    f"Temperature: {request.temperature}, Max Tokens: {request.max_output_tokens}"
                )
                
                generation_config = GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_output_tokens,
                )

                api_call_kwargs = {
                    "generation_config": generation_config,
                }

                if not use_api_default_safety: # If False (default), apply PERMISSIVE settings
                    api_call_kwargs["safety_settings"] = self._default_permissive_safety_settings
                    logger.info("Using custom PERMISSIVE safety settings (BLOCK_NONE for all categories).")
                else: # If True, use API's own default safety settings
                    logger.info("Using Google Gemini API's DEFAULT safety settings.")
                    # No 'safety_settings' key is added to api_call_kwargs, so API defaults apply

                response_obj = await asyncio.to_thread(
                    self.model.generate_content,
                    request.prompt,
                    **api_call_kwargs
                )
                
                if hasattr(response_obj, 'prompt_feedback') and response_obj.prompt_feedback:
                    logger.debug(f"Prompt Feedback: {response_obj.prompt_feedback}")
                    if response_obj.prompt_feedback.block_reason:
                        block_reason_detail = response_obj.prompt_feedback.block_reason_message or "No additional details"
                        error_message = (f"Prompt blocked by API safety filters: {response_obj.prompt_feedback.block_reason}. "
                                         f"Message: {block_reason_detail}")
                        logger.error(f"{error_message} Details: {response_obj.prompt_feedback.safety_ratings}")
                        raise ValueError(error_message)

                response_text_content = ""
                if hasattr(response_obj, 'text') and response_obj.text:
                    response_text_content = response_obj.text
                elif hasattr(response_obj, 'parts') and response_obj.parts:
                    response_text_content = "".join(part.text for part in response_obj.parts if hasattr(part, 'text'))
                
                if not response_text_content:
                    logger.error(f"Empty response content from Gemini API. Raw response object: {vars(response_obj) if hasattr(response_obj, '__dict__') else str(response_obj)}")
                    raise ValueError("Empty response from Gemini API (no text or parts with text).")

                raw_response_data = {"text_content_from_api": response_text_content}
                if hasattr(response_obj, 'candidates') and response_obj.candidates:
                    candidate_one = response_obj.candidates[0]
                    if hasattr(candidate_one, 'to_dict'):
                        raw_response_data = candidate_one.to_dict()
                    elif hasattr(candidate_one, '__dict__'):
                         raw_response_data = candidate_one.__dict__
                    if 'safety_ratings' in raw_response_data and isinstance(raw_response_data['safety_ratings'], list):
                        raw_response_data['safety_ratings'] = [
                            {"category": str(sr.category), "probability": str(sr.probability)}
                            if hasattr(sr, 'category') and hasattr(sr, 'probability') else str(sr)
                            for sr in raw_response_data['safety_ratings']
                        ]

                result = GeminiResponse(
                    text=response_text_content,
                    generated_text=response_text_content,
                    raw_response=raw_response_data,
                )
                
                logger.debug(f"Gemini API response received. Length: {len(result.text)}")
                return result

            except ValueError as ve:
                logger.warning(f"ValueError during Gemini API call (Attempt {attempt + 1}/{max_retries + 1}): {ve}")
                last_exception = ve
                if attempt == max_retries:
                    raise
            
            except Exception as e:
                logger.warning(f"Error calling Gemini API (Attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__} - {e}")
                last_exception = e
                if attempt == max_retries:
                    logger.exception(f"Final attempt failed calling Gemini API: {str(e)}")
                    raise RuntimeError(f"Failed to generate text with Gemini API after {max_retries + 1} attempts: {str(e)}")

            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                current_exception_type = type(last_exception).__name__ if last_exception else "Unknown Error"
                current_exception_msg = str(last_exception) if last_exception else ""
                logger.info(f"Retrying Gemini API call in {delay:.2f} seconds due to: {current_exception_type} - {current_exception_msg}")
                await asyncio.sleep(delay)
        
        logger.error(f"Exhausted all retries ({max_retries}) for Gemini API call. Last error: {last_exception}")
        if isinstance(last_exception, Exception):
            raise last_exception
        else:
            raise RuntimeError(f"Max retries ({max_retries}) exceeded for Gemini API call. Unknown final error.")

# Global client instance
gemini_client = GeminiClient()
