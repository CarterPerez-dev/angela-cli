# angela/ai/intent_analyzer.py

import re
import difflib
from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel

from angela.utils.logging import get_logger
from angela.api.ai import get_confidence_scorer
from angela.api.context import get_history_manager

logger = get_logger(__name__)

class IntentAnalysisResult(BaseModel):
    """Model for intent analysis results."""
    original_request: str
    normalized_request: str
    intent_type: str
    confidence: float
    entities: Dict[str, Any] = {}
    disambiguation_needed: bool = False
    possible_intents: List[Tuple[str, float]] = []

class IntentAnalyzer:
    """
    Enhanced intent analyzer with fuzzy matching and tolerance for
    misspellings and ambiguity.
    """
    
    # Define known intent patterns with examples
    INTENT_PATTERNS = {
        "file_search": [
            "find files", "search for files", "locate files", 
            "show me files", "list files matching"
        ],
        "directory_operation": [
            "create directory", "make folder", "create folder", 
            "remove directory", "delete folder"
        ],
        "file_operation": [
            "create file", "edit file", "delete file", "write to file",
            "read file", "show file contents", "copy file", "move file"
        ],
        "system_info": [
            "show system info", "check disk space", "memory usage",
            "cpu usage", "system status", "show processes"
        ],
        "git_operation": [
            "git status", "git commit", "git push", "git pull",
            "create branch", "switch branch", "merge branch"
        ],
        # Add more intent patterns as needed
    }
    
    # Common misspellings and variations
    SPELLING_VARIATIONS = {
        "directory": ["dir", "folder", "direcotry", "directroy"],
        "file": ["flie", "fil", "document"],
        "create": ["make", "creat", "crate", "new"],
        "delete": ["remove", "del", "rm", "erase"],
        "search": ["find", "look for", "locate", "seek"],
        # Add more variations
    }
    
    def __init__(self):
        """Initialize the intent analyzer."""
        self._logger = logger
    
    def normalize_request(self, request: str) -> str:
        """
        Normalize the request by fixing common misspellings and variations.
        
        Args:
            request: The original request string
            
        Returns:
            Normalized request string
        """
        normalized = request.lower()
        
        # Replace common variations with standard terms
        for standard, variations in self.SPELLING_VARIATIONS.items():
            for variation in variations:
                # Use word boundary regex to avoid partial replacements
                pattern = r'\b' + re.escape(variation) + r'\b'
                normalized = re.sub(pattern, standard, normalized)
        
        self._logger.debug(f"Normalized request: '{request}' -> '{normalized}'")
        return normalized
    
    def analyze_intent(self, request: str) -> IntentAnalysisResult:
        """
        Analyze the intent of a request with enhanced tolerance for
        variations and ambiguity.
        
        Args:
            request: The original request string
            
        Returns:
            IntentAnalysisResult with the analysis
        """
        # Normalize the request
        normalized = self.normalize_request(request)
        
        # Find closest matching intents
        matches = []
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            # Calculate best match score for this intent type
            best_score = 0
            for pattern in patterns:
                similarity = difflib.SequenceMatcher(None, normalized, pattern).ratio()
                if similarity > best_score:
                    best_score = similarity
            
            # Add to matches if score is above threshold
            if best_score > 0.6:  # Adjust threshold as needed
                matches.append((intent_type, best_score))
        
        # Sort matches by confidence score
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Check if we have a clear winner or need disambiguation
        if not matches:
            # No clear intent - low confidence fallback to generic
            return IntentAnalysisResult(
                original_request=request,
                normalized_request=normalized,
                intent_type="unknown",
                confidence=0.3,
                disambiguation_needed=True
            )
        
        top_intent, top_score = matches[0]
        
        # Extract entities based on the intent type
        entities = self._extract_entities(normalized, top_intent)
        
        # Check if disambiguation is needed
        disambiguation_needed = False
        if len(matches) > 1:
            second_intent, second_score = matches[1]
            # If top two scores are close, disambiguation might be needed
            if top_score - second_score < 0.15:
                disambiguation_needed = True
                self._logger.debug(f"Ambiguous intent: {top_intent} ({top_score:.2f}) vs {second_intent} ({second_score:.2f})")
        
        # Create the result
        result = IntentAnalysisResult(
            original_request=request,
            normalized_request=normalized,
            intent_type=top_intent,
            confidence=top_score,
            entities=entities,
            disambiguation_needed=disambiguation_needed,
            possible_intents=matches[:3]  # Keep top 3 for disambiguation
        )
        
        self._logger.info(f"Intent analysis: {top_intent} (confidence: {top_score:.2f})")
        return result
    
    def _extract_entities(self, normalized: str, intent_type: str) -> Dict[str, Any]:
        """
        Extract entities from the request based on intent type.
        
        Args:
            normalized: The normalized request string
            intent_type: The type of intent
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # Extract entities based on intent type
        if intent_type == "file_search":
            # Extract file patterns
            pattern_match = re.search(r'matching (.+?)(?: in | with | containing |$)', normalized)
            if pattern_match:
                entities["pattern"] = pattern_match.group(1)
            
            # Extract directory to search in
            dir_match = re.search(r'in (?:directory |folder |)([\w\./]+)', normalized)
            if dir_match:
                entities["directory"] = dir_match.group(1)
                
        elif intent_type == "file_operation" or intent_type == "directory_operation":
            # Extract file/directory names
            path_match = re.search(r'(?:file|directory|folder) (?:called |named |)["\'"]?([\w\./]+)["\'"]?', normalized)
            if path_match:
                entities["path"] = path_match.group(1)
                
            # Extract content if applicable
            content_match = re.search(r'with (?:content |text |)["\'](.*?)["\']', normalized)
            if content_match:
                entities["content"] = content_match.group(1)
        
        # Add more entity extraction rules for other intent types
        
        return entities
    
    async def get_interactive_disambiguation(self, result: IntentAnalysisResult) -> IntentAnalysisResult:
        """
        Get user clarification for ambiguous intent.
        
        Args:
            result: The initial analysis result
            
        Returns:
            Updated analysis result after disambiguation
        """
        # Only disambiguate if confidence is low or explicitly needed
        if result.confidence > 0.7 and not result.disambiguation_needed:
            return result
        
        self._logger.info(f"Getting disambiguation for intent: {result.intent_type}")
        
        # Import here to avoid circular imports
        from prompt_toolkit.shortcuts import radiolist_dialog
        from prompt_toolkit.styles import Style
        
        # Create options for disambiguation
        options = []
        for intent_type, score in result.possible_intents:
            # Create a human-readable description for each intent
            description = self._get_intent_description(intent_type, result.entities)
            options.append((intent_type, description))
        
        # Add a "none of these" option
        options.append(("none", "None of these - let me rephrase"))
        
        # Create dialog style
        dialog_style = Style.from_dict({
            'dialog': 'bg:#222222',
            'dialog.body': 'bg:#222222 #ffffff',
            'dialog.border': '#888888',
            'button': 'bg:#222222 #ffffff',
            'button.focused': 'bg:#0969DA #ffffff',
        })
        
        # Show the dialog
        selected_intent = radiolist_dialog(
            title="Clarification Needed",
            text=f"I'm not sure what you meant by: '{result.original_request}'\nPlease select what you intended:",
            values=options,
            style=dialog_style
        ).run()
        
        # If user selected a specific intent, update the result
        if selected_intent and selected_intent != "none":
            # Find the score for the selected intent
            selected_score = 0.85  # Default to high confidence since user confirmed
            for intent, score in result.possible_intents:
                if intent == selected_intent:
                    selected_score = max(0.85, score)  # At least 0.85 confidence
                    break
                    
            # Update the result
            result.intent_type = selected_intent
            result.confidence = selected_score
            result.disambiguation_needed = False
            
            # Re-extract entities based on the new intent
            result.entities = self._extract_entities(result.normalized_request, selected_intent)
            
            self._logger.info(f"Intent clarified: {selected_intent} (confidence: {selected_score:.2f})")
        
        return result
    
    def _get_intent_description(self, intent_type: str, entities: Dict[str, Any]) -> str:
        """
        Create a human-readable description for an intent.
        
        Args:
            intent_type: The type of intent
            entities: Extracted entities
            
        Returns:
            Human-readable description
        """
        if intent_type == "file_search":
            pattern = entities.get("pattern", "files")
            directory = entities.get("directory", "current directory")
            return f"Search for {pattern} in {directory}"
            
        elif intent_type == "file_operation":
            path = entities.get("path", "a file")
            if "create" in path or "make" in path:
                return f"Create a new file: {path}"
            elif "delete" in path or "remove" in path:
                return f"Delete file: {path}"
            else:
                return f"Perform operation on file: {path}"
                
        elif intent_type == "directory_operation":
            path = entities.get("path", "a directory")
            if "create" in path or "make" in path:
                return f"Create a new directory: {path}"
            elif "delete" in path or "remove" in path:
                return f"Delete directory: {path}"
            else:
                return f"Perform operation on directory: {path}"
                
        elif intent_type == "system_info":
            return "Show system information"
            
        elif intent_type == "git_operation":
            return "Perform Git operation"
            
        # Fallback for unknown intent types
        return f"Intent: {intent_type}"

# Global intent analyzer instance
intent_analyzer = IntentAnalyzer()
