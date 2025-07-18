from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any
from onchain.data_registry import GrantFile

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
    started_at: str
    finished_at: str
    result: str

class BaseCompute(ABC):
    """Base interface for all compute providers."""
    
    @abstractmethod
    def execute(self, grant_file: GrantFile, files_content: list[str]) -> ExecuteResponse:
        """Create a new prediction/computation job based on the grant file and files content."""
        pass
    
    @abstractmethod
    def get(self, prediction_id: str) -> GetResponse:
        """Get the status and result of a prediction."""
        pass
    
    @abstractmethod
    def cancel(self, prediction_id: str) -> bool:
        """Cancel a running prediction."""
        pass 