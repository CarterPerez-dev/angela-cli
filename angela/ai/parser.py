# angela/ai/parser.py
import json
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field, ValidationError

from angela.utils.logging import get_logger

logger = get_logger(__name__)

class CommandSuggestion(BaseModel):
    """Model for a command suggestion from the AI."""
    intent: str = Field(..., description="The classified intent of the user's request")
    command: str = Field(..., description="The suggested shell command")
    explanation: str = Field(..., description="Explanation of what the command does")
    additional_info: Optional[str] = Field(None, description="Any additional information")

# Update in angela/ai/parser.py
def parse_ai_response(response_text: str) -> CommandSuggestion:
    """Parse the AI response into a structured format."""
    try:
        # Try to extract JSON from the response
        json_str = None
        
        # Check for JSON in markdown code block with language specifier
        if "```json" in response_text and "```" in response_text.split("```json")[1]:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        # Check for JSON in regular markdown code block
        elif "```" in response_text and "```" in response_text.split("```")[1]:
            # Try without language specifier
            json_str = response_text.split("```")[1].strip()
        else:
            # Assume the entire response is JSON
            json_str = response_text.strip()
        
        # Parse the JSON
        data = json.loads(json_str)
        
        # Validate with Pydantic model
        suggestion = CommandSuggestion(**data)
        
        logger.debug(f"Successfully parsed AI response: {suggestion}")
        return suggestion
    
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse AI response: {str(e)}")
        logger.debug(f"Raw response: {response_text}")
        
        # Fallback: Try to extract just the command if JSON parsing fails
        try:
            import re
            # Improve the regex pattern to better match different formats
            command_match = re.search(r'command["\']?\s*:\s*["\']?(.*?)["\']?[,}]', response_text)
            if command_match:
                # Extract just the command value, not the whole match
                command = command_match.group(1).strip()
                # Remove any trailing quotes
                if command.endswith('"') or command.endswith("'"):
                    command = command[:-1]
                logger.debug(f"Extracted command using regex: {command}")
                return CommandSuggestion(
                    intent="unknown",
                    command=command,
                    explanation="Command extracted from incomplete response."
                )
        except Exception as regex_error:
            logger.error(f"Regex extraction also failed: {str(regex_error)}")
        
        raise ValueError(f"Could not parse AI response: {str(e)}")
