from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from domain.entities import GrantFile

@dataclass
class ExecuteResponse:
    """Data class for compute response."""
    id: str
    created_at: str

@dataclass
class GetResponse:
    """Data class for get response."""
    id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    result: str | None = None

class BaseCompute(ABC):
    """Base interface for all compute providers."""
    
    @abstractmethod
    def execute(self, grant_file: GrantFile, files_content: list[str]) -> ExecuteResponse:
        """Create a new prediction/computation job based on the grant file and files content.
        
        Args:
            grant_file: The grant file containing operation parameters (including response_format if applicable)
            files_content: List of file contents to process
        """
        pass
    
    @abstractmethod
    def get(self, prediction_id: str) -> GetResponse:
        """Get the status and result of a prediction."""
        pass
    
    @abstractmethod
    def cancel(self, prediction_id: str) -> bool:
        """Cancel a running prediction."""
        pass 