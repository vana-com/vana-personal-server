from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseProvider(ABC):
    """Base interface for all compute providers."""
    
    @abstractmethod
    def create_prediction(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new prediction/computation job."""
        pass
    
    @abstractmethod
    def get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Get the status and result of a prediction."""
        pass
    
    @abstractmethod
    def cancel_prediction(self, prediction_id: str) -> bool:
        """Cancel a running prediction."""
        pass 