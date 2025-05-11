# angela/components/intent/models.py
from enum import Enum
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field

class IntentType(str, Enum):
    """Enumeration of possible intent types."""
    UNKNOWN = "unknown"
    FILE_SEARCH = "file_search"
    DIRECTORY_LIST = "directory_list"
    FILE_VIEW = "file_view"
    SYSTEM_INFO = "system_info"
    NETWORK_INFO = "network_info"
    FILE_EDIT = "file_edit"  # For future phases
    FILE_CREATE = "file_create"  # For future phases
    GIT_OPERATION = "git_operation"  # For future phases
    DOCKER_OPERATION = "docker_operation"  # For future phases

class Intent(BaseModel):
    """Model for user intent."""
    type: IntentType = Field(..., description="The type of intent")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Entities extracted from the request")
    original_request: str = Field(..., description="The original user request")

class ActionPlan(BaseModel):
    """Model for an action plan derived from intent."""
    intent: Intent = Field(..., description="The intent that led to this plan")
    commands: List[str] = Field(..., description="List of commands to execute")
    explanations: List[str] = Field(..., description="Explanations for each command")
    risk_level: int = Field(0, description="Risk level of the plan (0-4)")
